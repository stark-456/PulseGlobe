"""
RAG 数据采集器
从向量库检索新闻数据
"""
import logging

import psycopg2
from psycopg2.extras import RealDictCursor
from langchain_openai import OpenAIEmbeddings

from pulseglobe.core.config import get_config
from .base import BaseCollector

logger = logging.getLogger(__name__)


class RAGCollector(BaseCollector):
    """RAG 向量检索采集器"""
    
    def __init__(self, max_results: int = 15, **kwargs):
        """
        Args:
            max_results: 每个关键词的最大结果数（默认15）
        """
        super().__init__(**kwargs)
        
        config = get_config()
        
        # 数据库配置
        db_config = config.database
        self.db_config = {
            "host": db_config.get("host"),
            "port": db_config.get("port"),
            "dbname": db_config.get("name"),
            "user": db_config.get("user"),
            "password": db_config.get("password"),
        }
        self.table_name = db_config.get("table", "pulseglobe_news")
        
        # Embedding 模型
        embedding_config = config.embedding
        self.embeddings = OpenAIEmbeddings(
            model=embedding_config.get("model", "Qwen/Qwen3-Embedding-4B"),
            api_key=embedding_config.get("api_key"),
            base_url=embedding_config.get("base_url"),
            dimensions=embedding_config.get("dimensions", 2560),
        )
        
        self.max_results = max_results
        self._conn = None
        
        logger.info(f"[RAGCollector] 初始化完成，max_results={max_results}")
    
    @property
    def source_type(self) -> str:
        return "rag"
    
    @property
    def source_detail(self) -> str:
        return "news_db"
    
    def _get_connection(self):
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(**self.db_config)
        return self._conn
    
    async def search(self, keyword: str) -> list[dict]:
        """执行向量检索"""
        try:
            # 生成查询向量
            query_embedding = self.embeddings.embed_query(keyword)
            
            conn = self._get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"""
                    SELECT 
                        title,
                        content,
                        url,
                        source_name,
                        publish_date,
                        1 - (embedding <=> %s::vector) as similarity
                    FROM {self.table_name}
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (query_embedding, query_embedding, self.max_results)
                )
                
                results = []
                for row in cur.fetchall():
                    results.append({
                        "title": row["title"] or "",
                        "content": row["content"] or "",
                        "url": row["url"] or "",
                        "author": row.get("source_name", ""),
                        "publish_date": row.get("publish_date"),
                        "platform": "news_db",
                        "engagement": {"similarity": float(row["similarity"]) if row["similarity"] else 0},
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"[RAGCollector] 检索失败: {e}")
            raise
    
    def close(self):
        if self._conn and not self._conn.closed:
            self._conn.close()
