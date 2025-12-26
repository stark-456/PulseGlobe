"""
数据包模型
表示采集的单条数据（一个"文件袋"）
"""
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class DataPacket:
    """数据包：存储采集的单条数据"""
    
    # 会话标识
    session_id: str
    
    # 数据来源
    source_type: str              # 'tavily' | 'social' | 'rag'
    source_detail: str = ""       # 'twitter' | 'tiktok' | 'youtube' | 'news_db'
    
    # 关键词关联
    keyword: str = ""
    keyword_type: str = ""        # 'tavily' | 'social' | 'rag'
    
    # 内容
    title: str = ""
    content: str = ""             # 原始内容（可能是外文，含评论）
    content_zh: str = ""          # 翻译后的中文内容
    summary: str = ""             # LLM生成的摘要（100字以内）
    
    # 元数据
    url: str = ""
    author: str = ""
    publish_date: Optional[datetime] = None
    platform: str = ""
    engagement: dict = field(default_factory=dict)  # {likes, retweets, views}
    
    # 管理字段
    created_at: datetime = field(default_factory=datetime.now)
    tags: list[str] = field(default_factory=list)
    
    # 数据库ID
    id: Optional[int] = None
    
    @property
    def content_hash(self) -> str:
        """生成内容哈希，用于去重"""
        text = f"{self.source_type}:{self.url}:{self.title}:{self.content[:500]}"
        return hashlib.sha256(text.encode()).hexdigest()
    
    def to_dict(self) -> dict:
        """转换为字典（用于数据库插入）"""
        return {
            "session_id": self.session_id,
            "source_type": self.source_type,
            "source_detail": self.source_detail,
            "keyword": self.keyword,
            "keyword_type": self.keyword_type,
            "title": self.title,
            "content": self.content,
            "content_zh": self.content_zh,
            "summary": self.summary,
            "url": self.url,
            "author": self.author,
            "publish_date": self.publish_date,
            "platform": self.platform,
            "engagement": self.engagement,
            "created_at": self.created_at,
            "tags": self.tags,
            "content_hash": self.content_hash,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "DataPacket":
        """从字典创建"""
        return cls(
            id=data.get("id"),
            session_id=data["session_id"],
            source_type=data["source_type"],
            source_detail=data.get("source_detail", ""),
            keyword=data.get("keyword", ""),
            keyword_type=data.get("keyword_type", ""),
            title=data.get("title", ""),
            content=data.get("content", ""),
            content_zh=data.get("content_zh", ""),
            summary=data.get("summary", ""),
            url=data.get("url", ""),
            author=data.get("author", ""),
            publish_date=data.get("publish_date"),
            platform=data.get("platform", ""),
            engagement=data.get("engagement", {}),
            created_at=data.get("created_at", datetime.now()),
            tags=data.get("tags", []),
        )
