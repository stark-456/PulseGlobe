"""
翻译服务
支持多种翻译提供商（讯蒙 Tengri API / LLM）
可通过配置切换
"""
import re
import logging
from abc import ABC, abstractmethod

import httpx
from langchain_core.messages import HumanMessage

from pulseglobe.core.config import get_config
from pulseglobe.services.llm import get_llm_client

logger = logging.getLogger(__name__)


class BaseTranslator(ABC):
    """翻译器基类"""
    
    @abstractmethod
    async def translate(self, text: str, target_lang: str = "zh") -> str:
        """翻译文本"""
        pass


class XmorTranslator(BaseTranslator):
    """讯蒙 Tengri API 翻译器"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.xmor.cn"):
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
        )
    
    async def translate(self, text: str, target_lang: str = "zh") -> str:
        """使用讯蒙 Tengri API 翻译"""
        if not text or not text.strip():
            return text
        
        try:
            response = await self.client.post(
                f"{self.base_url}/v1/translate",
                json={
                    "text": text,
                    "target_lang": target_lang,
                }
            )
            response.raise_for_status()
            result = response.json()
            return result.get("translation", text)
        except Exception as e:
            logger.error(f"讯蒙翻译失败: {e}")
            return text  # 失败时返回原文
    
    async def close(self):
        await self.client.aclose()


class LLMTranslator(BaseTranslator):
    """LLM 翻译器"""
    
    def __init__(self):
        self.llm = get_llm_client()
    
    async def translate(self, text: str, target_lang: str = "zh") -> str:
        """使用 LLM 翻译"""
        if not text or not text.strip():
            return text
        
        # 如果已经是中文为主，直接返回
        if self._is_mainly_chinese(text):
            return text
        
        lang_map = {"zh": "中文", "en": "英文", "mn": "蒙古语"}
        target = lang_map.get(target_lang, "中文")
        
        prompt = f"""请将以下内容翻译成{target}，只输出翻译结果，不要有任何解释：

{text}"""
        
        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            return response.content.strip()
        except Exception as e:
            logger.error(f"LLM翻译失败: {e}")
            return text
    
    def _is_mainly_chinese(self, text: str) -> bool:
        """检测文本是否主要是中文"""
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        total_chars = len(text.strip())
        if total_chars == 0:
            return True
        return chinese_chars / total_chars > 0.5


class TranslationService:
    """
    翻译服务（可切换提供商）
    
    配置方式（settings.yaml）:
    translation:
      provider: "xmor"  # 或 "llm"
      api_key: "${XMOR_API_KEY}"
      base_url: "https://api.xmor.cn"
    """
    
    def __init__(self, provider: str = None):
        config = get_config()
        trans_config = config.get("translation", {})
        
        self.provider = provider or trans_config.get("provider", "llm")
        
        if self.provider == "xmor":
            api_key = trans_config.get("api_key", "")
            base_url = trans_config.get("base_url", "https://api.xmor.cn")
            self.translator = XmorTranslator(api_key, base_url)
            logger.info("[TranslationService] 使用讯蒙 Tengri API")
        else:
            self.translator = LLMTranslator()
            logger.info("[TranslationService] 使用 LLM 翻译")
    
    async def translate(self, text: str, target_lang: str = "zh") -> str:
        """翻译文本"""
        return await self.translator.translate(text, target_lang)
    
    def is_chinese(self, text: str) -> bool:
        """检测文本是否主要是中文"""
        if not text:
            return True
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        total_chars = len(text.strip())
        if total_chars == 0:
            return True
        return chinese_chars / total_chars > 0.3
    
    async def translate_if_needed(self, text: str) -> str:
        """如果是外文则翻译"""
        if not text or self.is_chinese(text):
            return text
        return await self.translate(text, "zh")
    
    async def close(self):
        """关闭资源"""
        if hasattr(self.translator, 'close'):
            await self.translator.close()
