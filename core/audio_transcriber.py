# core/audio_transcriber.py

import os
# import time # 示例中不再记录时间，所以移除
from groq import Groq, APIError
import logging

# 获取当前模块的 logger
log = logging.getLogger(__name__)
# 注意: 日志的基本配置 (handler, formatter, level) 应该在程序入口 (app.py 或 main 脚本) 进行统一设置。
# 这里只是获取 logger 实例。

def seconds_to_srt_time(seconds: float) -> str:
    """将浮点秒数转换为 SRT 时间格式"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def generate_transcript_with_timestamps(words: list, max_duration: int = 7, max_chars: int = 30) -> dict:
    """生成带时间戳的转录内容"""
    segments = []
    current_text = ""
    start_time = None
    subtitle_index = 1

    for i, word_info in enumerate(words):
        if start_time is None:
            start_time = word_info["start"]
        
        current_text += word_info["word"]
        end_time = word_info["end"]

        should_split = (
            (end_time - start_time > max_duration) or
            (len(current_text) > max_chars) or
            (i == len(words) - 1)
        )

        if should_split:
            segments.append({
                "index": subtitle_index,
                "start_time": seconds_to_srt_time(start_time),
                "end_time": seconds_to_srt_time(end_time),
                "text": current_text.strip()
            })
            
            subtitle_index += 1
            current_text = ""
            start_time = None if i == len(words) - 1 else words[i + 1]["start"]

    return segments

class SimpleAudioTranscriber:
    """
    使用 Groq API 将单个音频文件转录为文本。

    配置信息（API Key, model等）通过构造函数传入的字典获取。
    此类不处理文件大小限制或音频切分，调用者需确保
    传入的音频文件符合 Groq Whisper API 的要求。
    """
    def __init__(self, config: dict):
        groq_config = config.get('groq')
        if not groq_config or not isinstance(groq_config, dict):
            # 强制要求配置中有 'groq' 且是字典
            raise ValueError("Configuration dictionary must contain a valid 'groq' section.")

        # 从配置中提取参数，提供默认值
        self.api_key = groq_config.get('api_key')
        self.model = groq_config.get('model', 'whisper-large-v3-turbo')
        self.language = groq_config.get('language', 'zh')
        self.prompt = groq_config.get('prompt', '') # 读取 prompt 参数
        # 尝试将 temperature 转换为 float，如果失败则使用默认值
        try:
            self.temperature = float(groq_config.get('temperature', 0.1))
        except (ValueError, TypeError):
            log.warning(f"Invalid 'temperature' value in config for model '{self.model}'. Using default 0.1.")
            self.temperature = 0.1

        # 强制要求 api_key 必须存在
        if not self.api_key:
            raise ValueError("Groq API Key is missing in the provided configuration under 'groq'.")

        try:
            # 在初始化时创建 Groq 客户端，验证 API Key 的有效性（部分验证）
            self.client = Groq(api_key=self.api_key)
            log.info(f"SimpleAudioTranscriber initialized (model: {self.model}, lang: {self.language}, temp: {self.temperature}, prompt: '{self.prompt[:50]}...').")
        except Exception as e:
            # 客户端初始化失败通常是 API Key 问题或网络问题
            log.error(f"Failed to initialize Groq client with provided config: {e}")
            # 抛出 ConnectionError，表明服务不可用
            raise ConnectionError(f"Failed to initialize Groq client: {e}") from e


    def transcribe_audio(self, audio_file_path: str) -> dict | str:
        if not os.path.exists(audio_file_path):
            error_msg = f"Error: Audio file not found at '{audio_file_path}'."
            log.error(error_msg)
            return error_msg

        log.info(f"Transcribing audio file: '{os.path.basename(audio_file_path)}'...")

        try:
            with open(audio_file_path, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    file=(audio_file_path, audio_file.read()),
                    model="whisper-large-v3-turbo",
                    temperature=0.15,
                    language="zh",
                    response_format="verbose_json",
                    timestamp_granularities=["word"]
                )
                
                # 生成带时间戳的转录段落
                segments = generate_transcript_with_timestamps(transcription.words)
                
                # 返回完整的转录结果
                return {
                    'text': transcription.text,
                    'task': transcription.task,
                    'language': transcription.language,
                    'duration': transcription.duration,
                    'words': transcription.words,
                    'segments': segments,  # 添加分段信息
                    'x_groq': transcription.x_groq
                }

        except APIError as e:
            error_msg = f"Groq API Error during transcription: {str(e)}"
            log.error(error_msg)
            return error_msg


# --- 示例用法 (仅当直接运行此文件进行测试时执行) ---
if __name__ == "__main__":
    # 在这里简单配置日志，以便看到输出
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log = logging.getLogger(__name__) # 重新获取 logger

    # 为了运行这个示例，我们需要 config_loader 和 config.yaml
    # 假设 config_loader.py 在 ../utils/ 目录下
    try:
        # 尝试导入 config_loader
        from utils.config_loader import load_config
    except ImportError:
        log.error("Could not import config_loader. Make sure utils/config_loader.py exists and is in the Python path.")
        exit(1) # 如果无法加载配置，直接退出示例

    print("--- Testing SimpleAudioTranscriber ---")

    # 1. 加载配置
    try:
        print("\nLoading configuration...")
        app_config = load_config() # 使用默认路径: ../config/config.yaml
        # 从加载的配置中获取 Groq 部分
        groq_config_for_transcriber = app_config.get('groq')

        if not groq_config_for_transcriber:
             log.error("Configuration loaded successfully, but missing 'groq' section.")
             exit(1)

        # 2. 初始化转录器
        print("\nInitializing transcriber...")
        # 将 Groq 配置部分传递给构造函数
        transcriber = SimpleAudioTranscriber(config=app_config) # 传递整个 app_config，Transcriber 会自己找 'groq'


        # 3. 指定一个测试音频文件路径 (替换为你自己的文件)
        #    确保这个文件存在，并且大小小于 Groq 的限制（约 40MB）
        test_audio_path = "path/to/your/test_audio.mp3" # <--- !!! 修改这里为你实际的音频文件路径 !!!

        if os.path.exists(test_audio_path):
            print(f"\nStarting transcription for: '{test_audio_path}'")
            try:
                # 4. 调用转录方法
                result = transcriber.transcribe_audio(test_audio_path)

                # 5. 处理结果
                if isinstance(result, str):
                    # 转录失败，result 是错误信息字符串
                    print("\n--- Transcription Failed ---")
                    print(result)
                elif isinstance(result, dict) and "text" in result:
                    # 转录成功，result 是包含 'text' 的字典
                    print("\n--- Transcription Successful ---")
                    print("\nFull Text:")
                    print(result["text"])

                    # 可选：打印词级别时间戳（如果存在）
                    if "words" in result and result["words"]:
                        print("\nWord Timestamps (first 5):")
                        for i, word_info in enumerate(result["words"][:5]):
                             # word_info 结构类似 {'word': '你好', 'start': 0.5, 'end': 0.8, 'confidence': 0.99}
                             print(f"  - '{word_info.get('word', '')}': {word_info.get('start', '?'):.2f}s - {word_info.get('end', '?'):.2f}s (Confidence: {word_info.get('confidence', '?'):.2f})")
                    else:
                         print("\nWord timestamps not available in the result.")

                else:
                     # 结果既不是错误字符串也不是预期的字典格式
                     print("\n--- Unexpected Transcription Result Format ---")
                     print(result)

            except Exception as e:
                # 捕获 transcribe_audio 中未被处理的异常 (如 IOError, ConnectionError 等)
                log.exception(f"\nAn uncaught exception occurred during transcription of '{os.path.basename(test_audio_path)}':") # 记录详细堆栈信息
                print(f"\n--- Transcription Failed (Uncaught Exception) ---\nError Type: {type(e).__name__}\nMessage: {e}")


        else:
            print(f"\nError: Test audio file not found at '{test_audio_path}'. Please update the path in the script.")

    except (ValueError, ConnectionError) as e:
        # 捕获配置加载或初始化转录器时抛出的错误
        print(f"\n--- Initialization or Configuration Error ---")
        print(f"Error: {e}")
    except Exception as e:
        # 捕获加载配置或初始化之外的其他任何意外错误
        log.exception("\nAn unexpected error occurred during setup:")
        print(f"\n--- An Unexpected Error Occurred During Setup ---\nError Type: {type(e).__name__}\nMessage: {e}")

    print("\n--- Testing finished ---")