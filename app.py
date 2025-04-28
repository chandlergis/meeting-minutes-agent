import streamlit as st
import os
from pathlib import Path
from typing import Dict, List
import logging
import subprocess
from pydub import AudioSegment

# First Streamlit command must be set_page_config
st.set_page_config(
    page_title="Meeting Minutes Generator",
    page_icon="📝",
    layout="wide"
)

from core.pdf_parser import DocumentParser
from core.llm import LLMService, Message
from utils.config_loader import load_config

# 设置日志
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def init_services():
    """初始化所有服务"""
    try:
        config = load_config()
        doc_parser = DocumentParser()
        llm_service = LLMService(config)
        return config, doc_parser, llm_service
    except Exception as e:
        st.error(f"服务初始化失败: {str(e)}")
        return None, None, None

def save_uploaded_document(uploaded_file, directory: str) -> str:
    """保存上传的文档文件并返回保存路径"""
    if not os.path.exists(directory):
        os.makedirs(directory)
    file_path = os.path.join(directory, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path

def convert_to_wav(src_path, dst_path):
    subprocess.run([
        "ffmpeg", "-y", "-i", src_path, "-ar", "16000", "-ac", "1", dst_path
    ], check=True)

def split_wav_to_chunks(wav_path, max_size_mb=35, max_chunk_minutes=9):
    """将wav按时长分割成多个小于max_size_mb的文件，优先按时长分段"""
    audio = AudioSegment.from_wav(wav_path)
    chunk_length_ms = max_chunk_minutes * 60 * 1000  # 9分钟一段
    chunks = []
    for i, start in enumerate(range(0, len(audio), chunk_length_ms)):
        chunk = audio[start:start+chunk_length_ms]
        chunk_path = wav_path.rsplit('.', 1)[0] + f"_part{i+1}.wav"
        chunk.export(chunk_path, format="wav")
        # 再次确保分段后每段都小于max_size_mb
        if os.path.getsize(chunk_path) > max_size_mb * 1024 * 1024:
            raise ValueError(f"音频分段后单段仍超过{max_size_mb}MB，请上传更短音频")
        chunks.append(chunk_path)
    return chunks

def save_uploaded_file(uploaded_file, directory: str) -> list:
    """保存上传的文件并返回wav路径列表（如需分段则返回多个）"""
    if not os.path.exists(directory):
        os.makedirs(directory)
    file_path = os.path.join(directory, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    ext = os.path.splitext(file_path)[1].lower()
    if ext in ['.mp3', '.m4a', '.ogg']:
        wav_path = file_path.rsplit('.', 1)[0] + '.wav'
        convert_to_wav(file_path, wav_path)
    elif ext == '.wav':
        wav_path = file_path
    else:
        raise ValueError("不支持的音频格式")
    # 无论多大都分段，保证每段都小于API限制
    return split_wav_to_chunks(wav_path, max_size_mb=35, max_chunk_minutes=9)

def main():
    # Create left-right layout
    left_col, right_col = st.columns([1, 1])

    with left_col:
        st.title("📝 会议纪要生成器")
        
        # 初始化服务
        config, doc_parser, llm_service = init_services()
        if not all([config, doc_parser, llm_service]):
            return

        # 创建临时文件夹
        temp_dir = Path("temp")
        temp_dir.mkdir(exist_ok=True)

        # 会议内容输入区
        st.header("📋 会议内容")
        meeting_content = st.text_area("输入会议备注（可选）", height=150)

        # 文档上传区
        st.header("📁 上传文档")
        st.info("支持上传最多15个文档，每个最大50MB")
        
        # 展平支持的格式列表并创建唯一集合
        supported_formats = []
        for formats in doc_parser.SUPPORTED_FORMATS.values():
            supported_formats.extend(formats)
        supported_formats = list(set(supported_formats))
        
        uploaded_docs = st.file_uploader(
            "选择文档文件",
            accept_multiple_files=True,
            type=supported_formats
        )

    with right_col:
        st.header("📤 生成结果")
        
        # 处理按钮
        if st.button("生成会议纪要", use_container_width=True):
            if not uploaded_docs and not meeting_content:
                st.warning("请至少提供一种会议内容（文档或备注）")
                return

            # 验证文件数量和大小
            if len(uploaded_docs) > 15:
                st.error("文档数量超过限制（最多15个）")
                return
            
            for doc in uploaded_docs:
                if doc.size > 50 * 1024 * 1024:  # 50MB
                    st.error(f"文档 {doc.name} 超过大小限制（50MB）")
                    return

            with st.spinner("正在处理文件..."):
                # 处理文档
                meeting_file = []
                for doc in uploaded_docs:
                    file_path = save_uploaded_document(doc, str(temp_dir))
                    result = doc_parser.parse_document(file_path)
                    if not result.get("error"):
                        meeting_file.append(result["text_content"])

            # 生成会议纪要prompt
            prompt = f"""
## Context:
本次任务的目标是根据提供的多种来源（会议备注、相关文档）的原始信息，自动化生成一份结构清晰、内容准确、格式标准的正式会议纪要。
这份纪要将用于官方记录、信息同步和任务跟进。

## Role:
你是一位专业的 AI 会议纪要助手，擅长从非结构化文本中提取关键信息，并将其组织成专业、规范的会议纪要文档。

## Input Data:
你将接收到以下格式的文本信息：

--- BEGIN INPUT ---

**# 会议备注:**
{meeting_content if meeting_content else '无内容'}

**# 文档内容:**
{' '.join(meeting_file) if meeting_file else '无内容'}

## INSTRUCTIONS (PROCESSING STEPS):

请按照以下步骤分析和处理上述输入数据：
1.  提取基本信息 (Extraction): 识别并整合会议的基础要素：会议名称/主题、时间、地点、主持人、参会人员名单。
2.  归纳议题与讨论 (Summarization & Analysis): 识别会议讨论的核心议题。对每个议题，总结关键讨论点、主要观点（包括共识与分歧）以及最终结论或状态。
3.  整理会议决定 (Decision Collation): 筛选并清晰记录所有达成的明确决策。
4.  梳理行动计划 (Action Item Identification): 提取所有分配的具体任务，明确负责人、截止日期（若有）和关键要求。
## GOAL (OUTPUT REQUIREMENTS):
你的最终输出必须是一份符合以下格式和约束条件的会议纪要：

1. 输出格式 (Strict Template):
请严格遵循以下纯文本模板，不要添加任何 Markdown 标记或其他格式符号。

--- BEGIN OUTPUT TEMPLATE ---

[会议名称]会议纪要

一、会议基本信息
    时间：[提取或推断的会议日期和时间]
    地点：[提取的会议地点]
    主持人：[提取的主持人姓名及部门]
    参会人员：[提取的参会人员姓名及部门列表，用逗号分隔]

二、主要议题及讨论内容
    （一）[议题1标题]
        讨论概要：[简述议题1的关键讨论点、主要观点、共识与分歧]
        议题结论：[明确议题1的结论或当前状态]

    （二）[议题2标题]
        讨论概要：[简述议题2的关键讨论点、主要观点、共识与分歧]
        议题结论：[明确议题2的结论或当前状态]

    [...] <根据实际议题数量调整>

三、会议决定
    1. [决定1：清晰、可执行的描述]
    2. [决定2：清晰、可执行的描述]
    [...] <根据实际决定数量调整，如无则写“无”>

四、任务计划（行动项）
    1. [任务1描述]
    2. [任务2描述]
    [...] <根据实际任务数量调整，如无则写“无”>
--- END OUTPUT TEMPLATE ---

2. 内容与风格约束 (Content & Style Constraints):
*   准确性: 内容必须基于提供的输入信息，忠实反映会议情况。
*   信息缺失处理: 若输入信息不足以填充模板中的某个字段（如具体时间、负责人），请使用 `[待明确]` 作为占位符。不得臆测信息。
*   专业性: 使用客观、中立、正式的商业书面语言。
*   简洁性: 在保证信息完整的前提下，力求语言精练。
*   格式纯净: 严格输出纯文本，无任何额外格式符号。

"""

            with st.spinner("正在生成会议纪要..."):
                # 调用LLM生成会议纪要
                response = llm_service.chat_with_system(prompt)
                
                if not response.error:
                    st.success("会议纪要生成成功！")
                    st.text_area("生成的会议纪要", response.text, height=600)
                    
                    # 提供下载按钮
                    st.download_button(
                        label="💾 下载会议纪要",
                        data=response.text,
                        file_name="meeting_minutes.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                else:
                    st.error(f"生成会议纪要失败: {response.error}")

    # 清理临时文件
    for file in temp_dir.glob("*"):
        try:
            file.unlink()
        except Exception as e:
            log.warning(f"Failed to delete temporary file {file}: {e}")

if __name__ == "__main__":
    main()