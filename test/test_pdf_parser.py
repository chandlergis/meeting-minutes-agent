import os
import sys
import unittest
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from core.pdf_parser import DocumentParser

class TestDocumentParser(unittest.TestCase):
    def setUp(self):
        """测试前的设置"""
        self.parser = DocumentParser()
        self.test_files = {
            'pdf': os.path.join(project_root, "test", "test.pdf"),
            'docx': os.path.join(project_root, "test", "test.docx"),
            'jpg': os.path.join(project_root, "test", "test.jpg"),
        }

    def test_get_file_type(self):
        """测试文件类型识别"""
        self.assertEqual(self.parser.get_file_type("test.pdf"), "document")
        self.assertEqual(self.parser.get_file_type("test.docx"), "document")
        self.assertEqual(self.parser.get_file_type("test.jpg"), "image")
        self.assertEqual(self.parser.get_file_type("test.xyz"), "unknown")

    def test_parse_document(self):
        """测试文档解析功能"""
        # 测试PDF文件
        if os.path.exists(self.test_files['pdf']):
            result = self.parser.parse_document(self.test_files['pdf'])
            self.assertIsInstance(result, dict)
            self.assertIn('text_content', result)
            self.assertEqual(result.get('file_type'), 'document')

    def test_supported_formats(self):
        """测试支持的文件格式列表"""
        formats = self.parser.get_supported_formats()
        self.assertIsInstance(formats, dict)
        self.assertIn('document', formats)
        self.assertIn('image', formats)
        self.assertIn('.pdf', formats['document'])

if __name__ == '__main__':
    unittest.main(verbosity=2)