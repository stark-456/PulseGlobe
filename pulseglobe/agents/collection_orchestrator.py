"""
数据采集 Orchestrator
协调三个采集器进行海量数据采集并存储
"""
import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional

from pulseglobe.agents.collectors import TavilyCollector, SocialCollector, RAGCollector
from pulseglobe.services.storage import PacketStorage
from pulseglobe.services.translation import TranslationService
from pulseglobe.services.summarization import SummarizationService
from pulseglobe.models.data_packet import DataPacket

logger = logging.getLogger(__name__)


@dataclass
class CollectionConfig:
    """采集配置"""
    # Tavily 配置
    tavily_enabled: bool = True
    tavily_max_results: int = 20
    
    # Social 配置
    social_enabled: bool = True
    social_platforms: list[str] = field(default_factory=lambda: ["twitter", "tiktok", "youtube"])
    social_post_count: int = 10
    social_comments_per_post: int = 10
    
    # RAG 配置
    rag_enabled: bool = True
    rag_max_results: int = 15
    
    # 翻译配置
    translation_provider: str = "xmor"  # "xmor" 或 "llm"


@dataclass
class CollectionResult:
    """采集结果"""
    session_id: str
    stats: dict
    duration_seconds: float


class DataCollectionOrchestrator:
    """
    数据采集 Orchestrator
    
    协调三个采集器，执行完整的数据采集流程：
    1. 输入：关键词列表（来自阶段一）
    2. 并行采集：Tavily + Social + RAG
    3. 翻译 + 摘要
    4. 存储到 data_packets 表
    5. 返回 session_id
    """
    
    def __init__(self, config: CollectionConfig = None):
        self.config = config or CollectionConfig()
        
        # 共享服务
        self.translator = TranslationService(provider=self.config.translation_provider)
        self.summarizer = SummarizationService()
        self.storage = PacketStorage()
        
        # 初始化采集器
        self._init_collectors()
        
        logger.info(f"[DataCollectionOrchestrator] 初始化完成")
        logger.info(f"[DataCollectionOrchestrator]   Tavily: {self.config.tavily_enabled}, max={self.config.tavily_max_results}")
        logger.info(f"[DataCollectionOrchestrator]   Social: {self.config.social_enabled}, platforms={self.config.social_platforms}")
        logger.info(f"[DataCollectionOrchestrator]   RAG: {self.config.rag_enabled}, max={self.config.rag_max_results}")
    
    def _init_collectors(self):
        """初始化采集器"""
        self.tavily_collector = TavilyCollector(
            max_results=self.config.tavily_max_results,
            translator=self.translator,
            summarizer=self.summarizer,
        ) if self.config.tavily_enabled else None
        
        self.social_collector = SocialCollector(
            platforms=self.config.social_platforms,
            post_count=self.config.social_post_count,
            comments_per_post=self.config.social_comments_per_post,
            translator=self.translator,
            summarizer=self.summarizer,
        ) if self.config.social_enabled else None
        
        self.rag_collector = RAGCollector(
            max_results=self.config.rag_max_results,
            translator=self.translator,
            summarizer=self.summarizer,
        ) if self.config.rag_enabled else None
    
    async def collect(
        self,
        tavily_keywords: list[str],
        social_keywords: list[str],
        rag_keywords: list[str],
        session_id: str = None,
    ) -> CollectionResult:
        """
        执行数据采集
        
        Args:
            tavily_keywords: Tavily 搜索关键词
            social_keywords: 社交媒体关键词
            rag_keywords: RAG 召回关键词
            session_id: 可选的会话ID，默认自动生成
            
        Returns:
            CollectionResult 包含 session_id 和统计信息
        """
        start_time = datetime.now()
        
        # 生成 session_id
        if not session_id:
            session_id = f"sess_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"{'='*70}")
        logger.info(f"[DataCollectionOrchestrator] ▶ 开始数据采集")
        logger.info(f"[DataCollectionOrchestrator]   Session: {session_id}")
        logger.info(f"[DataCollectionOrchestrator]   Tavily关键词: {len(tavily_keywords)}")
        logger.info(f"[DataCollectionOrchestrator]   Social关键词: {len(social_keywords)}")
        logger.info(f"[DataCollectionOrchestrator]   RAG关键词: {len(rag_keywords)}")
        logger.info(f"{'='*70}")
        
        all_packets = []
        
        # 采集 Tavily 数据
        if self.tavily_collector and tavily_keywords:
            logger.info(f"\n[DataCollectionOrchestrator] 📰 采集 Tavily 数据...")
            tavily_packets = await self._collect_channel(
                collector=self.tavily_collector,
                keywords=tavily_keywords,
                keyword_type="tavily",
                session_id=session_id,
            )
            all_packets.extend(tavily_packets)
            logger.info(f"[DataCollectionOrchestrator]   Tavily 采集完成: {len(tavily_packets)} 条")
        
        # 采集 Social 数据
        if self.social_collector and social_keywords:
            logger.info(f"\n[DataCollectionOrchestrator] 📱 采集 Social 数据...")
            social_packets = await self._collect_channel(
                collector=self.social_collector,
                keywords=social_keywords,
                keyword_type="social",
                session_id=session_id,
            )
            all_packets.extend(social_packets)
            logger.info(f"[DataCollectionOrchestrator]   Social 采集完成: {len(social_packets)} 条")
        
        # 采集 RAG 数据
        if self.rag_collector and rag_keywords:
            logger.info(f"\n[DataCollectionOrchestrator] 📚 采集 RAG 数据...")
            rag_packets = await self._collect_channel(
                collector=self.rag_collector,
                keywords=rag_keywords,
                keyword_type="rag",
                session_id=session_id,
            )
            all_packets.extend(rag_packets)
            logger.info(f"[DataCollectionOrchestrator]   RAG 采集完成: {len(rag_packets)} 条")
        
        # 存储数据
        logger.info(f"\n[DataCollectionOrchestrator] 💾 存储数据包...")
        save_result = self.storage.save_packets(all_packets)
        
        # 获取统计
        stats = self.storage.get_session_stats(session_id)
        
        duration = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"\n{'='*70}")
        logger.info(f"[DataCollectionOrchestrator] ◀ 采集完成")
        logger.info(f"[DataCollectionOrchestrator]   Session: {session_id}")
        logger.info(f"[DataCollectionOrchestrator]   总计: {stats['total']} 条")
        logger.info(f"[DataCollectionOrchestrator]   - Tavily: {stats.get('tavily', 0)}")
        logger.info(f"[DataCollectionOrchestrator]   - Social: {stats.get('social', 0)}")
        logger.info(f"[DataCollectionOrchestrator]   - RAG: {stats.get('rag', 0)}")
        logger.info(f"[DataCollectionOrchestrator]   新增: {save_result['saved']}, 重复: {save_result['duplicates']}")
        logger.info(f"[DataCollectionOrchestrator]   耗时: {duration:.1f}s")
        logger.info(f"{'='*70}")
        
        return CollectionResult(
            session_id=session_id,
            stats=stats,
            duration_seconds=duration,
        )
    
    async def _collect_channel(
        self,
        collector,
        keywords: list[str],
        keyword_type: str,
        session_id: str,
    ) -> list[DataPacket]:
        """采集单个通道的所有关键词"""
        all_packets = []
        
        for i, keyword in enumerate(keywords, 1):
            logger.info(f"[DataCollectionOrchestrator]   [{i}/{len(keywords)}] '{keyword}'")
            try:
                packets = await collector.collect(
                    session_id=session_id,
                    keyword=keyword,
                    keyword_type=keyword_type,
                )
                all_packets.extend(packets)
            except Exception as e:
                logger.warning(f"[DataCollectionOrchestrator]   ✗ 采集失败: {e}")
                continue
        
        return all_packets
    
    def close(self):
        """关闭资源"""
        if self.rag_collector:
            self.rag_collector.close()
        if hasattr(self.social_collector, 'close'):
            asyncio.create_task(self.social_collector.close())
        self.storage.close()
