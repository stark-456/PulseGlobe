# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "httpx>=0.25.0",
#     "psycopg2-binary>=2.9.9",
#     "pyyaml>=6.0",
#     "python-dotenv>=1.0.0",
# ]
# ///
"""
向量化脚本：为 pulseglobe_news 表生成 embedding
使用硬基流动 Qwen/Qwen3-Embedding-4B 模型（2560 维）

用法 (使用 uv):
    uv run vectorize_news.py [options]

选项:
    --concurrency   并发数量 (默认: 5)
    --batch-size    批量处理大小 (默认: 50)
    --limit         最大处理数量 (默认: 无限制)
    --dry-run       试运行，不实际写入数据库
"""

import asyncio
import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

import httpx
import psycopg2
from psycopg2.extras import RealDictCursor
import yaml
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# ============================================
# 配置加载
# ============================================
def load_config():
    """加载配置文件"""
    config_path = Path(__file__).parent.parent / "config" / "settings.yaml"
    
    if not config_path.exists():
        logging.error(f"配置文件不存在: {config_path}")
        sys.exit(1)
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 解析环境变量
    def resolve_env(value):
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            env_name = value[2:-1]
            return os.getenv(env_name, "")
        return value
    
    def resolve_dict(d):
        return {k: resolve_dict(v) if isinstance(v, dict) else resolve_env(v) 
                for k, v in d.items()}
    
    return resolve_dict(config)


# ============================================
# 日志配置
# ============================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('vectorize_news.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


# ============================================
# Embedding 结果
# ============================================
@dataclass
class EmbeddingResult:
    doc_id: str
    embedding: Optional[list]
    success: bool
    error: Optional[str] = None


# ============================================
# Embedding 服务
# ============================================
class EmbeddingService:
    """通用 Embedding 服务（OpenAI 兼容接口）"""
    
    def __init__(self, config: dict, concurrency: int = 5):
        self.model = config.get("model", "Qwen/Qwen3-Embedding-4B")
        self.dimension = config.get("dimensions", 2560)
        self.base_url = config.get("base_url", "https://api.siliconflow.cn/v1")
        self.api_key = config.get("api_key", "")
        
        self.semaphore = asyncio.Semaphore(concurrency)
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=60.0,
            limits=httpx.Limits(max_connections=concurrency * 2)
        )
        
        logger.info(f"Embedding 服务初始化: model={self.model}, dim={self.dimension}")
    
    async def get_embedding(self, text: str) -> Optional[list]:
        """获取单个文本的 embedding"""
        if not text or not text.strip():
            return None
        
        # 截断过长文本（bge 模型限制 512 tokens，约 1500 中文字符）
        text = text[:3000]
        
        async with self.semaphore:
            try:
                response = await self.client.post(
                    f"{self.base_url}/embeddings",
                    json={
                        "model": self.model,
                        "input": text
                    }
                )
                response.raise_for_status()
                result = response.json()
                return result["data"][0]["embedding"]
            except httpx.HTTPStatusError as e:
                logger.error(f"Embedding API 错误: {e.response.status_code} - {e.response.text[:200]}")
                return None
            except Exception as e:
                logger.error(f"Embedding 请求失败: {e}")
                return None
    
    async def embed_document(self, doc: dict) -> EmbeddingResult:
        """为单个文档生成 embedding（标题 + 内容拼接）"""
        doc_id = doc["doc_id"]
        title = doc.get("title", "") or ""
        content = doc.get("content", "") or ""
        
        # 拼接标题和内容
        full_text = f"{title}\n\n{content}"
        
        try:
            embedding = await self.get_embedding(full_text)
            if embedding:
                return EmbeddingResult(doc_id=doc_id, embedding=embedding, success=True)
            else:
                return EmbeddingResult(doc_id=doc_id, embedding=None, success=False, error="空响应")
        except Exception as e:
            return EmbeddingResult(doc_id=doc_id, embedding=None, success=False, error=str(e))
    
    async def close(self):
        await self.client.aclose()


# ============================================
# 数据库操作
# ============================================
class VectorDatabase:
    """向量数据库操作"""
    
    def __init__(self, config: dict):
        self.config = {
            "host": config.get("host", "localhost"),
            "port": config.get("port", 5432),
            "database": config.get("name", "news_db"),
            "user": config.get("user", "postgres"),
            "password": config.get("password", "")
        }
        self.conn = None
        self.table = "pulseglobe_news"
    
    def connect(self):
        self.conn = psycopg2.connect(**self.config)
        logger.info(f"已连接到数据库: {self.config['database']}@{self.config['host']}")
    
    def close(self):
        if self.conn:
            self.conn.close()
            logger.info("数据库连接已关闭")
    
    def get_pending_documents(self, limit: Optional[int] = None) -> list:
        """获取待向量化的文档"""
        query = f"""
            SELECT doc_id, title, content 
            FROM {self.table}
            WHERE embedding IS NULL
            ORDER BY id
        """
        if limit:
            query += f" LIMIT {limit}"
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query)
            return cur.fetchall()
    
    def update_embedding(self, doc_id: str, embedding: list, dry_run: bool = False):
        """更新文档的 embedding"""
        if dry_run:
            return True
        
        embedding_str = "[" + ",".join(map(str, embedding)) + "]"
        
        with self.conn.cursor() as cur:
            cur.execute(f"""
                UPDATE {self.table}
                SET embedding = %s::vector
                WHERE doc_id = %s
            """, (embedding_str, doc_id))
        self.conn.commit()
        return True
    
    def get_stats(self) -> dict:
        """获取向量化统计"""
        with self.conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {self.table}")
            total = cur.fetchone()[0]
            
            cur.execute(f"SELECT COUNT(*) FROM {self.table} WHERE embedding IS NOT NULL")
            vectorized = cur.fetchone()[0]
            
            return {
                "total": total,
                "vectorized": vectorized,
                "pending": total - vectorized
            }


# ============================================
# 主逻辑
# ============================================
async def vectorize_batch(
    db: VectorDatabase,
    embedder: EmbeddingService,
    batch_size: int = 50,
    limit: Optional[int] = None,
    dry_run: bool = False
):
    """批量向量化"""
    
    logger.info("正在获取待向量化文档...")
    docs = db.get_pending_documents(limit=limit)
    total = len(docs)
    
    if total == 0:
        logger.info("没有待向量化的文档")
        return
    
    logger.info(f"找到 {total} 个待向量化文档，开始处理...")
    
    success_count = 0
    fail_count = 0
    
    for batch_start in range(0, total, batch_size):
        batch_end = min(batch_start + batch_size, total)
        batch = docs[batch_start:batch_end]
        batch_num = batch_start // batch_size + 1
        total_batches = (total + batch_size - 1) // batch_size
        
        logger.info(f"--- 批次 {batch_num}/{total_batches}: 处理 {len(batch)} 个 ({batch_start+1}-{batch_end}/{total}) ---")
        
        # 并发处理
        tasks = [embedder.embed_document(doc) for doc in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 写入数据库
        for result in results:
            if isinstance(result, Exception):
                fail_count += 1
                logger.error(f"  ✗ 异常: {result}")
                continue
            
            if result.success and result.embedding:
                db.update_embedding(result.doc_id, result.embedding, dry_run=dry_run)
                success_count += 1
            else:
                fail_count += 1
                logger.warning(f"  ✗ {result.doc_id}: {result.error}")
        
        logger.info(f"--- 批次完成 | 累计成功: {success_count} | 累计失败: {fail_count} ---")
    
    logger.info(f"\n向量化完成! 成功: {success_count}, 失败: {fail_count}")


async def main():
    parser = argparse.ArgumentParser(description="新闻向量化工具")
    parser.add_argument("--concurrency", type=int, default=5, help="并发数量")
    parser.add_argument("--batch-size", type=int, default=50, help="批量处理大小")
    parser.add_argument("--limit", type=int, default=None, help="最大处理数量")
    parser.add_argument("--dry-run", action="store_true", help="试运行模式")
    args = parser.parse_args()
    
    # 加载配置
    config = load_config()
    
    logger.info("=" * 60)
    logger.info("新闻向量化工具")
    logger.info(f"模型: {config['embedding']['model']}")
    logger.info(f"维度: {config['embedding']['dimension']}")
    logger.info(f"并发数: {args.concurrency}, 批次大小: {args.batch_size}")
    logger.info("=" * 60)
    
    if args.dry_run:
        logger.info(">>> 试运行模式 <<<")
    
    db = VectorDatabase(config["database"])
    embedder = EmbeddingService(config["embedding"], concurrency=args.concurrency)
    
    try:
        db.connect()
        
        stats = db.get_stats()
        logger.info(f"当前状态: 总数={stats['total']}, 已向量化={stats['vectorized']}, 待处理={stats['pending']}")
        
        await vectorize_batch(
            db=db,
            embedder=embedder,
            batch_size=args.batch_size,
            limit=args.limit,
            dry_run=args.dry_run
        )
        
        stats = db.get_stats()
        logger.info(f"最终状态: 总数={stats['total']}, 已向量化={stats['vectorized']}, 待处理={stats['pending']}")
        
    finally:
        await embedder.close()
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
