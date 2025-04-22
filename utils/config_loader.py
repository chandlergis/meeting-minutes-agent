# utils/config_loader.py

import yaml
import os
import logging

# 获取logger
log = logging.getLogger(__name__)

# 配置文件默认路径
DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.yaml')

def load_config(config_path: str = DEFAULT_CONFIG_PATH) -> dict:
    """
    加载YAML配置文件，支持环境变量覆盖。

    Args:
        config_path: 配置文件路径，默认为项目根目录下的 config/config.yaml

    Returns:
        dict: 配置字典
    """
    try:
        # 检查配置文件是否存在
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"配置文件未找到: {config_path}")

        # 读取YAML文件
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            
        if not isinstance(config, dict):
            raise ValueError("配置文件格式错误，应为YAML字典格式")

        # 处理Groq配置
        if 'groq' not in config:
            raise ValueError("配置中缺少 'groq' 部分")

        # 环境变量优先于配置文件
        if os.environ.get("GROQ_API_KEY"):
            config['groq']['api_key'] = os.environ["GROQ_API_KEY"]
        elif 'api_key' not in config['groq']:
            raise ValueError("未找到Groq API密钥，请在配置文件中设置或通过GROQ_API_KEY环境变量提供")

        # 设置默认值
        config['groq'].setdefault('model', 'whisper-large-v3-turbo')
        config['groq'].setdefault('language', 'zh')
        config['groq'].setdefault('prompt', '')
        config['groq'].setdefault('temperature', 0.1)

        return config

    except Exception as e:
        log.error(f"加载配置时出错: {str(e)}")
        raise
        # 直接使用默认配置文件
