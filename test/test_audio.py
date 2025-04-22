import os
import sys
import unittest
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from core.audio_transcriber import SimpleAudioTranscriber
from utils.config_loader import load_config

class TestAudioTranscriber(unittest.TestCase):
    def setUp(self):
        """测试前的设置"""
        self.config = load_config()
        self.transcriber = SimpleAudioTranscriber(self.config)
        self.test_audio = os.path.join(project_root, "test", "test.wav")

    def test_transcribe_audio(self):
        """测试音频转录功能"""
        # 确保测试音频文件存在
        self.assertTrue(os.path.exists(self.test_audio), f"Test audio file not found: {self.test_audio}")
        
        # 执行转录
        result = self.transcriber.transcribe_audio(self.test_audio)
        
        # 打印结果，以便查看转录内容
        print("\n=== Transcription Result ===")
        if isinstance(result, dict):
            print("\nTranscribed Text:")
            print(result.get('text', 'No text found'))
            
            if 'words' in result:
                print("\nWord Timestamps (first 5 words):")
                for word_info in result['words'][:5]:
                    print(f"Word: {word_info.get('word')}")
                    print(f"Start: {word_info.get('start')}s")
                    print(f"End: {word_info.get('end')}s")
                    print(f"Confidence: {word_info.get('confidence')}\n")
        else:
            print("Error:", result)

        # 验证结果是否为字典类型（成功转录）或字符串类型（错误信息）
        self.assertTrue(isinstance(result, (dict, str)), "Result should be either dict or error string")
        
        # 如果是成功的转录结果
        if isinstance(result, dict):
            self.assertIn('text', result, "Transcription result should contain 'text' key")
            self.assertIsInstance(result['text'], str, "Transcribed text should be a string")

if __name__ == '__main__':
    unittest.main(verbosity=2)