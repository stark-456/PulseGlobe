"""
RAG 召回 Worker
使用 PostgreSQL + pgvector 进行向量检索
"""
import logging
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor
from langchain_openai import OpenAIEmbeddings

from pulseglobe.core.config import get_config
from pulseglobe.agents.prompts import RAG_KEYWORD_EXTRACTION_PROMPT
from .base import BaseWorker

logger = logging.getLogger(__name__)


class RAGWorker(BaseWorker):
    """RAG 向量检索 Worker"""
    
    def __init__(self):
        super().__init__()
        config = get_config()
        
        # 数据库配置
        self.db_config = config.database
        
        # Embedding 模型
        embedding_config = config.embedding
        self.embeddings = OpenAIEmbeddings(
            model=embedding_config.get("model", "Qwen/Qwen3-Embedding-4B"),
            api_key=embedding_config.get("api_key"),
            base_url=embedding_config.get("base_url"),
            dimensions=embedding_config.get("dimensions", 2560),
        )
        
        self.table_name = self.db_config.get("table", "pulseglobe_news")
        self._conn: Optional[psycopg2.extensions.connection] = None
    
    @property
    def name(self) -> str:
        return "RAGWorker"
    
    @property
    def source_type(self) -> str:
        return "RAG中文新闻库"
    
    @property
    def extraction_prompt(self) -> str:
        return RAG_KEYWORD_EXTRACTION_PROMPT
    
    def _get_connection(self):
        """获取数据库连接"""
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(
                host=self.db_config.get("host"),
                port=self.db_config.get("port"),
                dbname=self.db_config.get("name"),
                user=self.db_config.get("user"),
                password=self.db_config.get("password"),
            )
        return self._conn
    
    async def search(self, keyword: str) -> list[dict]:
        """
        执行向量相似度搜索
        
        Args:
            keyword: 搜索关键词（中文）
            
        Returns:
            检索结果列表，每个结果包含 title, content, url
        """
        try:
            # 生成查询向量
            query_embedding = self.embeddings.embed_query(keyword)
            
            # 执行向量搜索
            conn = self._get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 使用 pgvector 的 <=> 运算符进行余弦距离搜索
                cur.execute(
                    f"""
                    SELECT 
                        title,
                        content,
                        url,
                        1 - (embedding <=> %s::vector) as similarity
                    FROM {self.table_name}
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> %s::vector
                    LIMIT 5
                    """,
                    (query_embedding, query_embedding)
                )
                
                results = []
                for row in cur.fetchall():
                    results.append({
                        "title": row["title"] or "",
                        "content": row["content"] or "",
                        "url": row["url"] or "",
                        "similarity": float(row["similarity"]) if row["similarity"] else 0,
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"RAG 检索错误: {e}")
            raise
    
    def close(self):
        """关闭数据库连接"""
        if self._conn and not self._conn.closed:
            self._conn.close()
