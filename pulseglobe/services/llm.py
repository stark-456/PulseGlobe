"""
LLM 客户端服务
使用 langchain-openai 兼容各种 OpenAI 格式的 API
"""
from langchain_openai import ChatOpenAI
from pulseglobe.core.config import get_config


def get_llm_client() -> ChatOpenAI:
    """获取 LLM 客户端实例"""
    config = get_config()
    llm_config = config.llm
    
    return ChatOpenAI(
        model=llm_config.get("model", "deepseek-ai/DeepSeek-V3"),
        api_key=llm_config.get("api_key"),
        base_url=llm_config.get("base_url"),
        temperature=0.7,
    )


def get_json_llm_client() -> ChatOpenAI:
    """获取支持 JSON 输出的 LLM 客户端"""
    config = get_config()
    llm_config = config.llm
    
    return ChatOpenAI(
        model=llm_config.get("model", "deepseek-ai/DeepSeek-V3"),
        api_key=llm_config.get("api_key"),
        base_url=llm_config.get("base_url"),
        temperature=0.3,
        model_kwargs={"response_format": {"type": "json_object"}},
    )
