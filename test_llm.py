from core.llm import LLMService
from utils.config_loader import load_config

# 加载配置
config = load_config()
llm = LLMService(config=config)

# 使用默认的system content
response = llm.chat_with_system("hello")
print(response.text)

# 使用自定义的system content
custom_system = "你是一个专业的技术文档撰写专家，擅长将技术内容转化为通俗易懂的文档。"
response = llm.chat_with_system(
    "解释下什么是依赖注入？",
    system_content=custom_system
)
print(response.text)