"""
配置管理模块
从环境变量加载 TikHub API 配置
"""
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""
    
    # TikHub API 配置
    tikhub_api_token: str
    tikhub_api_base_url: str = "https://api.tikhub.io"
    
    # 速率限制
    max_requests_per_minute: int = 60
    
    # 缓存配置
    cache_ttl_seconds: int = 300
    
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False
    )


# 全局配置实例
settings = Settings()
