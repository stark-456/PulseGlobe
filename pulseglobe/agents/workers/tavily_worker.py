"""
Tavily 搜索 Worker
使用 Tavily API 进行网页搜索
"""
import logging
from tavily import AsyncTavilyClient

from pulseglobe.core.config import get_config
from pulseglobe.agents.prompts import TAVILY_KEYWORD_EXTRACTION_PROMPT
from .base import BaseWorker

logger = logging.getLogger(__name__)


class TavilyWorker(BaseWorker):
    """Tavily 搜索引擎 Worker"""
    
    def __init__(self):
        super().__init__()
        config = get_config()
        api_key = config.tavily.get("api_key")
        if not api_key:
            raise ValueError("Tavily API key not configured")
        self.client = AsyncTavilyClient(api_key=api_key)
    
    @property
    def name(self) -> str:
        return "TavilyWorker"
    
    @property
    def source_type(self) -> str:
        return "Tavily网页搜索"
    
    @property
    def extraction_prompt(self) -> str:
        return TAVILY_KEYWORD_EXTRACTION_PROMPT
    
    async def search(self, keyword: str) -> list[dict]:
        """
        执行 Tavily 搜索
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            搜索结果列表，每个结果包含 title, content, url
        """
        try:
            response = await self.client.search(
                query=keyword,
                search_depth="basic",
                max_results=5,
            )
            
            results = []
            for item in response.get("results", []):
                results.append({
                    "title": item.get("title", ""),
                    "content": item.get("content", ""),
                    "url": item.get("url", ""),
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Tavily 搜索错误: {e}")
            raise
