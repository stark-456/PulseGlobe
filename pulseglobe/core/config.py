"""
PulseGlobe 配置加载器
支持YAML配置文件和环境变量替换
"""
import os
import re
from pathlib import Path
from typing import Any

import yaml


class Config:
    """配置管理器"""
    
    _instance = None
    _config: dict = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self):
        """加载配置文件"""
        # 查找配置文件
        config_paths = [
            Path(__file__).parent.parent.parent / "config" / "settings.yaml",
            Path.cwd() / "config" / "settings.yaml",
        ]
        
        config_path = None
        for path in config_paths:
            if path.exists():
                config_path = path
                break
        
        if config_path is None:
            raise FileNotFoundError("配置文件 settings.yaml 未找到")
        
        # 读取并解析YAML
        with open(config_path, 'r', encoding='utf-8') as f:
            raw_config = yaml.safe_load(f)
        
        # 替换环境变量
        self._config = self._resolve_env_vars(raw_config)
    
    def _resolve_env_vars(self, obj: Any) -> Any:
        """递归替换环境变量 ${VAR} 或 ${VAR:default}"""
        if isinstance(obj, str):
            pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'
            
            def replace(match):
                var_name = match.group(1)
                default = match.group(2)
                value = os.environ.get(var_name)
                if value is None:
                    if default is not None:
                        return default
                    raise ValueError(f"环境变量 {var_name} 未设置")
                return value
            
            return re.sub(pattern, replace, obj)
        elif isinstance(obj, dict):
            return {k: self._resolve_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._resolve_env_vars(item) for item in obj]
        else:
            return obj
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值，支持点号分隔的路径
        例: config.get("database.host")
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    @property
    def database(self) -> dict:
        return self._config.get("database", {})
    
    @property
    def llm(self) -> dict:
        return self._config.get("llm", {})
    
    @property
    def embedding(self) -> dict:
        return self._config.get("embedding", {})
    
    @property
    def tavily(self) -> dict:
        return self._config.get("tavily", {})
    
    @property
    def mcp(self) -> dict:
        return self._config.get("mcp", {})
    
    @property
    def agent(self) -> dict:
        return self._config.get("agent", {})


# 全局配置实例
def get_config() -> Config:
    """获取配置实例"""
    return Config()
