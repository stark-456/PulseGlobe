"""
Tavily 数据采集器
采集网页搜索结果
"""
import logging

from tavily import AsyncTavilyClient

from pulseglobe.core.config import get_config
from .base import BaseCollector

logger = logging.getLogger(__name__)


class TavilyCollector(BaseCollector):
    """Tavily 网页搜索采集器"""
    
    def __init__(self, max_results: int = 20, **kwargs):
        """
        Args:
            max_results: 每个关键词的最大结果数（默认20）
        """
        super().__init__(**kwargs)
        
        config = get_config()
        api_key = config.tavily.get("api_key")
        if not api_key:
            raise ValueError("Tavily API key not configured")
        
        self.client = AsyncTavilyClient(api_key=api_key)
        self.max_results = max_results
        
        logger.info(f"[TavilyCollector] 初始化完成，max_results={max_results}")
    
    @property
    def source_type(self) -> str:
        return "tavily"
    
    @property
    def source_detail(self) -> str:
        return "web_search"
    
    async def search(self, keyword: str) -> list[dict]:
        """执行 Tavily 搜索"""
        try:
            response = await self.client.search(
                query=keyword,
                search_depth="advanced",  # 更深度的搜索
                max_results=self.max_results,
                include_answer=False,
            )
            
            results = []
            for item in response.get("results", []):
                results.append({
                    "title": item.get("title", ""),
                    "content": item.get("content", ""),
                    "url": item.get("url", ""),
                    "publish_date": item.get("published_date"),
                    "platform": "web",
                })
            
            return results
            
        except Exception as e:
            logger.error(f"[TavilyCollector] 搜索失败: {e}")
            raise
