"""
数据采集器基类
定义采集→翻译→摘要→存储的通用流程
"""
import logging
from abc import ABC, abstractmethod
from datetime import datetime

from pulseglobe.models.data_packet import DataPacket
from pulseglobe.services.translation import TranslationService
from pulseglobe.services.summarization import SummarizationService

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """
    数据采集器基类
    
    流程：搜索 → 翻译 → 摘要 → 返回 DataPacket 列表
    """
    
    def __init__(
        self,
        translator: TranslationService = None,
        summarizer: SummarizationService = None,
    ):
        self.translator = translator or TranslationService()
        self.summarizer = summarizer or SummarizationService()
    
    @property
    @abstractmethod
    def source_type(self) -> str:
        """数据源类型：'tavily' | 'social' | 'rag'"""
        pass
    
    @property
    @abstractmethod
    def source_detail(self) -> str:
        """数据源详情"""
        pass
    
    @abstractmethod
    async def search(self, keyword: str) -> list[dict]:
        """
        执行搜索
        
        Returns:
            原始搜索结果列表
        """
        pass
    
    async def collect(
        self,
        session_id: str,
        keyword: str,
        keyword_type: str,
    ) -> list[DataPacket]:
        """
        执行完整采集流程
        
        Args:
            session_id: 采集批次ID
            keyword: 搜索关键词
            keyword_type: 关键词类型
            
        Returns:
            DataPacket 列表
        """
        logger.info(f"[{self.__class__.__name__}] 🔍 采集关键词: '{keyword}'")
        
        # 1. 搜索
        try:
            raw_results = await self.search(keyword)
            logger.info(f"[{self.__class__.__name__}]   获取 {len(raw_results)} 条原始结果")
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}]   搜索失败: {e}")
            return []
        
        if not raw_results:
            return []
        
        # 2. 处理每条结果
        packets = []
        for i, item in enumerate(raw_results):
            try:
                packet = await self._process_item(
                    item=item,
                    session_id=session_id,
                    keyword=keyword,
                    keyword_type=keyword_type,
                )
                if packet:
                    packets.append(packet)
            except Exception as e:
                logger.warning(f"[{self.__class__.__name__}]   处理第{i+1}条失败: {e}")
                continue
        
        logger.info(f"[{self.__class__.__name__}]   ✓ 生成 {len(packets)} 个数据包")
        return packets
    
    async def _process_item(
        self,
        item: dict,
        session_id: str,
        keyword: str,
        keyword_type: str,
    ) -> DataPacket:
        """处理单条搜索结果"""
        
        # 提取内容
        title = item.get("title", "")
        content = item.get("content", "") or item.get("text", "") or item.get("description", "")
        
        # 拼接评论（如果有）
        comments = item.get("comments", [])
        if comments:
            comment_texts = [c.get("text", "") for c in comments if c.get("text")]
            if comment_texts:
                content += "\n\n【评论】\n" + "\n".join(comment_texts[:10])
        
        # 翻译（如果需要）
        content_zh = await self.translator.translate_if_needed(content)
        title_zh = await self.translator.translate_if_needed(title) if title else ""
        
        # 生成摘要
        summary = await self.summarizer.summarize(content_zh, title_zh)
        
        # 构建数据包
        return DataPacket(
            session_id=session_id,
            source_type=self.source_type,
            source_detail=self.source_detail,
            keyword=keyword,
            keyword_type=keyword_type,
            title=title_zh or title,
            content=content,
            content_zh=content_zh,
            summary=summary,
            url=item.get("url", ""),
            author=item.get("author", ""),
            publish_date=self._parse_date(item.get("publish_date") or item.get("created_at")),
            platform=item.get("platform", self.source_detail),
            engagement=item.get("engagement", {}),
            created_at=datetime.now(),
            tags=[],
        )
    
    def _parse_date(self, date_str) -> datetime:
        """解析日期"""
        if not date_str:
            return None
        if isinstance(date_str, datetime):
            return date_str
        try:
            # 尝试常见格式
            for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"]:
                try:
                    return datetime.strptime(str(date_str)[:19], fmt)
                except:
                    continue
        except:
            pass
        return None
