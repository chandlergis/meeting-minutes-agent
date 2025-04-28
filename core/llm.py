import os
import json
import logging
from typing import Dict, List, Optional, Union
import requests
from dataclasses import dataclass
from utils.config_loader import load_config

# 获取logger
log = logging.getLogger(__name__)

@dataclass
class Message:
    """聊天消息的数据类"""
    role: str
    content: str

@dataclass
class ChatResponse:
    """聊天响应的数据类"""
    text: str
    raw_response: dict
    error: Optional[str] = None

class LLMService:
    """
    大语言模型服务
    支持多个模型提供商的统一接口
    """
    
    def __init__(self, config: Dict = None):
        """
        初始化LLM服务
        Args:
            config: 配置字典，如果不提供则从配置文件加载
        """
        if config is None:
            config = load_config()
        
        xai_config = config.get('xai', {})
        self.api_key = xai_config.get('api_key') or os.getenv("XAI_API_KEY")
        if not self.api_key:
            raise ValueError("API key must be provided either in config or through XAI_API_KEY environment variable")
        
        # 修改为新的 API 配置
        self.model = xai_config.get('model', "rsv-c6x82efj")
        self.base_url = "http://25.214.170.46:80/xlm-gateway-gwfjet/sfm-api-gateway/gateway/compatible-mode/v1"
        
        # API调用的默认头信息
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        log.info(f"LLM Service initialized with model: {self.model}")

    def chat(self, 
            messages: List[Message],
            temperature: float = None,
            max_tokens: int = None,
            reasoning_effort: str = None
            ) -> ChatResponse:
        """
        发送聊天请求到AI模型
        
        Args:
            messages: 消息列表，每个消息包含role和content
            temperature: 温度参数，控制随机性
            max_tokens: 最大生成token数
            reasoning_effort: 推理努力程度 ["low", "medium", "high"]

        Returns:
            ChatResponse对象，包含生成的文本和原始响应
        """
        try:
            # 简化请求参数，适配新的 API
            payload = {
                "model": self.model,
                "messages": [msg.__dict__ for msg in messages],
                "stream": False
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload
            )
            
            response.raise_for_status()
            result = response.json()
            
            # 适配新的返回格式
            assistant_message = result["choices"][0]["message"]["content"]
            
            return ChatResponse(
                text=assistant_message,
                raw_response=result
            )
            
        except requests.exceptions.RequestException as e:
            error_msg = f"API request failed: {str(e)}"
            log.error(error_msg)
            return ChatResponse(
                text="",
                raw_response={},
                error=error_msg
            )
        
        except KeyError as e:
            error_msg = f"Unexpected API response format: {str(e)}"
            log.error(error_msg)
            return ChatResponse(
                text="",
                raw_response=response.json() if 'response' in locals() else {},
                error=error_msg
            )

    def simple_chat(self, prompt: str) -> str:
        """
        简单的聊天接口，只需要提供prompt即可
        
        Args:
            prompt: 用户输入的提示文本
            
        Returns:
            生成的回复文本
        """
        messages = [
            Message(role="system", content="You are a highly intelligent AI assistant."),
            Message(role="user", content=prompt)
        ]
        
        response = self.chat(messages)
        if response.error:
            return f"Error: {response.error}"
        return response.text

    def chat_with_system(self, 
            user_message: str,
            system_content: str = None
            ) -> ChatResponse:
        """
        使用自定义system prompt的聊天接口
        
        Args:
            user_message: 用户输入的消息
            system_content: 系统提示消息，如果不提供则使用配置文件中的默认值
            
        Returns:
            ChatResponse对象
        """
        messages = [
            Message(role="system", content=system_content or self.system_content),
            Message(role="user", content=user_message)
        ]
        
        return self.chat(messages)