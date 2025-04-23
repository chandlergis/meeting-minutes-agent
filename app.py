import streamlit as st
import os
from pathlib import Path
from typing import Dict, List
import logging

# First Streamlit command must be set_page_config
st.set_page_config(
    page_title="Meeting Minutes Generator",
    page_icon="📝",
    layout="wide"
)

from core.pdf_parser import DocumentParser
from core.audio_transcriber import SimpleAudioTranscriber
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
        audio_transcriber = SimpleAudioTranscriber(config)
        llm_service = LLMService(config)
        return config, doc_parser, audio_transcriber, llm_service
    except Exception as e:
        st.error(f"服务初始化失败: {str(e)}")
        return None, None, None, None

def save_uploaded_file(uploaded_file, directory: str) -> str:
    """保存上传的文件并返回保存路径"""
    if not os.path.exists(directory):
        os.makedirs(directory)
    file_path = os.path.join(directory, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path

def main():
    # Create left-right layout
    left_col, right_col = st.columns([1, 1])

    with left_col:
        st.title("📝 会议纪要生成器")
        
        # 初始化服务
        config, doc_parser, audio_transcriber, llm_service = init_services()
        if not all([config, doc_parser, audio_transcriber, llm_service]):
            return

        # 创建临时文件夹
        temp_dir = Path("temp")
        temp_dir.mkdir(exist_ok=True)

        # 会议内容输入区
        st.header("📋 会议内容")
        meeting_content = st.text_area("输入会议备注（可选）", height=150)

        # 文档上传区
        st.header("📁 上传文档")
        st.info("支持上传最多10个文档，每个最大50MB")
        uploaded_docs = st.file_uploader(
            "选择文档文件",
            accept_multiple_files=True,
            type=list(set([ext[1:] for exts in doc_parser.SUPPORTED_FORMATS.values() 
                          for ext in exts if ext not in ['.mp3', '.wav', '.m4a', '.ogg']]))
        )

        # 音频上传区
        st.header("🎵 上传音频")
        st.info("支持上传最多5个音频文件，每个最大40MB")
        uploaded_audios = st.file_uploader(
            "选择音频文件",
            accept_multiple_files=True,
            type=['mp3', 'wav', 'm4a', 'ogg']
        )

    with right_col:
        st.header("📤 生成结果")
        
        # 处理按钮
        if st.button("生成会议纪要", use_container_width=True):
            if not uploaded_docs and not uploaded_audios and not meeting_content:
                st.warning("请至少提供一种会议内容（文档、音频或备注）")
                return

            # 验证文件数量和大小
            if len(uploaded_docs) > 10:
                st.error("文档数量超过限制（最多10个）")
                return
            if len(uploaded_audios) > 5:
                st.error("音频文件数量超过限制（最多5个）")
                return
            
            for doc in uploaded_docs:
                if doc.size > 50 * 1024 * 1024:  # 50MB
                    st.error(f"文档 {doc.name} 超过大小限制（50MB）")
                    return
            for audio in uploaded_audios:
                if audio.size > 40 * 1024 * 1024:  # 40MB
                    st.error(f"音频文件 {audio.name} 超过大小限制（40MB）")
                    return

            with st.spinner("正在处理文件..."):
                # 处理文档
                meeting_file = []
                for doc in uploaded_docs:
                    file_path = save_uploaded_file(doc, str(temp_dir))
                    result = doc_parser.parse_document(file_path)
                    if not result.get("error"):
                        meeting_file.append(result["text_content"])
                
                # 处理音频
                meeting_audio = []
                for audio in uploaded_audios:
                    file_path = save_uploaded_file(audio, str(temp_dir))
                    result = audio_transcriber.transcribe_audio(file_path)
                    if isinstance(result, dict) and "text" in result:
                        meeting_audio.append(result["text"])

            # 生成会议纪要prompt
            prompt = f"""
请根据以下信息生成一份专业的会议纪要：

会议备注：
{meeting_content if meeting_content else '无'}

文档内容：
{' '.join(meeting_file) if meeting_file else '无'}

音频转录：
{' '.join(meeting_audio) if meeting_audio else '无'}

请生成一份结构化的会议纪要，包含：
1. 会议主要议题
2. 重要决策和结论
3. 待办事项和负责人
4. 后续跟进计划
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