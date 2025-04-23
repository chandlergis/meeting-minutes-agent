import os
import logging
from markitdown import MarkItDown
from typing import Dict, Optional, List

# 获取logger
log = logging.getLogger(__name__)

class DocumentParser:
    """
    通用文档解析器，支持多种文档格式转换为Markdown。
    支持格式包括：PDF、Word、PowerPoint、Excel、图片、音频等。
    """

    # 支持的文件类型
    SUPPORTED_FORMATS = {
        'document': ['.pdf', '.doc', '.docx', '.rtf', '.txt'],
        'spreadsheet': ['.xls', '.xlsx', '.csv'],
        'presentation': ['.ppt', '.pptx'],
        'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp'],
        'audio': ['.mp3', '.wav', '.m4a', '.ogg'],
        'archive': ['.zip', '.rar'],
        'web': ['.html', '.htm'],
        'data': ['.json', '.xml']
    }

    def __init__(self):
        """初始化文档解析器"""
        try:
            self.converter = MarkItDown()
            log.info("Document parser initialized successfully")
        except Exception as e:
            log.error(f"Failed to initialize document parser: {e}")
            raise RuntimeError(f"Failed to initialize document parser: {e}")

    def get_file_type(self, file_path: str) -> str:
        """
        判断文件类型
        Returns: 文件类型分类（document, spreadsheet, presentation等）
        """
        ext = os.path.splitext(file_path)[1].lower()
        for file_type, extensions in self.SUPPORTED_FORMATS.items():
            if ext in extensions:
                return file_type
        return "unknown"

    def parse_document(self, file_path: str) -> Dict[str, str]:
        """
        将文档转换为Markdown格式

        Args:
            file_path: 文档文件路径

        Returns:
            Dict包含:
                - text_content: Markdown格式的文本内容
                - file_name: 原始文件名
                - file_type: 文件类型
                - metadata: 元数据信息
                - error: 如果有错误，返回错误信息
        """
        if not os.path.exists(file_path):
            error_msg = f"File not found: {file_path}"
            log.error(error_msg)
            return {"error": error_msg}

        file_type = self.get_file_type(file_path)
        if file_type == "unknown":
            error_msg = f"Unsupported file format: {os.path.splitext(file_path)[1]}"
            log.error(error_msg)
            return {"error": error_msg}

        try:
            log.info(f"Converting {file_type} file: {file_path}")
            result = self.converter.convert(file_path)
            
            return {
                "text_content": result.text_content,
                "file_name": os.path.basename(file_path),
                "file_type": file_type,
                "metadata": getattr(result, 'metadata', {}),
                "error": None
            }

        except Exception as e:
            error_msg = f"Failed to convert file: {str(e)}"
            log.error(error_msg)
            return {"error": error_msg}

    def get_supported_formats(self) -> Dict[str, List[str]]:
        """返回支持的文件格式列表"""
        return self.SUPPORTED_FORMATS

    def save_markdown(self, content: str, output_path: str) -> Optional[str]:
        """
        保存Markdown内容到文件

        Args:
            content: Markdown格式的文本内容
            output_path: 输出文件路径

        Returns:
            None如果成功，否则返回错误信息
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            log.info(f"Markdown content saved to: {output_path}")
            return None
        except Exception as e:
            error_msg = f"Failed to save Markdown file: {str(e)}"
            log.error(error_msg)
            return error_msg