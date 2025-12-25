"""
PulseGlobe 配置加载器
从 config/models.yaml 和环境变量加载配置
"""

import os
import re
from pathlib import Path
from typing import Any, Optional

import yaml


def _resolve_env_vars(value: Any) -> Any:
    """递归解析配置值中的环境变量 ${VAR_NAME}"""
    if isinstance(value, str):
        pattern = r'\$\{([^}]+)\}'
        matches = re.findall(pattern, value)
        for var_name in matches:
            env_value = os.getenv(var_name, "")
            value = value.replace(f"${{{var_name}}}", env_value)
        return value
    elif isinstance(value, dict):
        return {k: _resolve_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_resolve_env_vars(item) for item in value]
    return value


class Config:
    """配置管理器"""
    
    _instance: Optional['Config'] = None
    _config: dict = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._config:
            self.reload()
    
    def reload(self, config_path: Optional[Path] = None):
        """加载或重新加载配置"""
        if config_path is None:
            # 默认从项目根目录的 config/models.yaml 加载
            config_path = Path(__file__).parent.parent / "config" / "models.yaml"
        
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            raw_config = yaml.safe_load(f)
        
        # 解析环境变量
        self._config = _resolve_env_vars(raw_config)
    
    @property
    def embedding(self) -> dict:
        """获取 Embedding 配置"""
        return self._config.get("embedding", {})
    
    @property
    def llm(self) -> dict:
        """获取 LLM 配置"""
        return self._config.get("llm", {})
    
    @property
    def translation(self) -> dict:
        """获取翻译配置"""
        return self._config.get("translation", {})
    
    @property
    def rag(self) -> dict:
        """获取 RAG 参数"""
        return self._config.get("rag", {})
    
    @property
    def database(self) -> dict:
        """获取数据库配置"""
        return self._config.get("database", {})
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取任意配置项"""
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default


# 全局配置实例
config = Config()
