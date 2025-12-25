# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "httpx>=0.25.0",
#     "psycopg2-binary>=2.9.9",
# ]
# ///
"""
蒙语新闻批量翻译脚本（并发版）
使用讯蒙科技 Tengri API 将蒙语新闻翻译成中文

用法 (使用 uv):
    uv run translate_mn_news.py [options]

选项:
    --concurrency   并发数量 (默认: 5)
    --batch-size    批量处理大小，用于进度显示 (默认: 50)
    --limit         最大处理数量 (默认: 无限制)
    --dry-run       试运行，不实际写入数据库
"""

import asyncio
import argparse
import logging
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

import httpx
import psycopg2
from psycopg2.extras import RealDictCursor

# ============================================
# 配置区域 - 请修改以下配置
# ============================================

# 数据库配置
DB_CONFIG = {
    "host": "111.91.20.199",
    "port": 5432,
    "database": "news_db",
    "user": "postgres",
    "password": "admin123"
}

# 讯蒙 API 配置
XMOR_API_KEY = "sk-cLT4ndg70eZR0ZrgRlASfEa2bcCLaZecWylTKKOwh2MgS0xj"
XMOR_API_BASE = "https://api.xmor.cn"

# 源表和目标表
SOURCE_TABLE = "news_articles"
TARGET_TABLE = "news_articles_mn_zh"

# ============================================
# 日志配置
# ============================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('translate_mn_news.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


# ============================================
# 翻译结果数据类
# ============================================
@dataclass
class TranslationResult:
    """翻译结果"""
    article: dict
    title_zh: Optional[str]
    content_zh: Optional[str]
    success: bool
    error: Optional[str] = None


# ============================================
# 翻译服务
# ============================================
class XmorTranslator:
    """讯蒙科技 Tengri API 翻译客户端（支持并发）"""
    
    def __init__(self, api_key: str, base_url: str = XMOR_API_BASE, concurrency: int = 5):
        self.api_key = api_key
        self.base_url = base_url
        self.semaphore = asyncio.Semaphore(concurrency)  # 限制并发数
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            timeout=120.0,
            limits=httpx.Limits(max_connections=concurrency * 2)
        )
    
    async def translate(
        self, 
        text: str, 
        source_lang: str = "auto",
        target_lang: str = "zh"
    ) -> Optional[str]:
        """翻译文本（带并发限制）"""
        if not text or not text.strip():
            return ""
        
        async with self.semaphore:  # 获取信号量，限制并发
            try:
                response = await self.client.post(
                    f"{self.base_url}/v1/chat/translation",
                    json={
                        "model": "tengri-t1",
                        "messages": [
                            {"role": "user", "content": text}
                        ],
                        "from": source_lang,
                        "to": target_lang
                    }
                )
                response.raise_for_status()
                result = response.json()
                
                if "choices" in result:
                    return result["choices"][0]["message"]["content"]
                elif "translation" in result:
                    return result["translation"]
                elif "content" in result:
                    return result["content"]
                else:
                    return str(result)
                    
            except httpx.HTTPStatusError as e:
                logger.error(f"翻译 API 错误: {e.response.status_code}")
                return None
            except Exception as e:
                logger.error(f"翻译请求失败: {e}")
                return None
    
    async def translate_article(self, article: dict) -> TranslationResult:
        """
        翻译单篇文章（标题和正文并发翻译）
        """
        article_id = article["original_id"]
        title = article.get("title", "")
        content = article.get("content", "")
        
        try:
            # 并发翻译标题和正文
            title_zh, content_zh = await asyncio.gather(
                self.translate(title),
                self.translate(content)
            )
            
            if title_zh and content_zh:
                return TranslationResult(
                    article=article,
                    title_zh=title_zh,
                    content_zh=content_zh,
                    success=True
                )
            else:
                return TranslationResult(
                    article=article,
                    title_zh=title_zh,
                    content_zh=content_zh,
                    success=False,
                    error=f"标题={bool(title_zh)}, 正文={bool(content_zh)}"
                )
        except Exception as e:
            return TranslationResult(
                article=article,
                title_zh=None,
                content_zh=None,
                success=False,
                error=str(e)
            )
    
    async def close(self):
        await self.client.aclose()


# ============================================
# 数据库操作
# ============================================
class NewsDatabase:
    """新闻数据库操作类"""
    
    def __init__(self, config: dict):
        self.config = config
        self.conn = None
        self._lock = asyncio.Lock()  # 数据库写入锁
    
    def connect(self):
        """建立数据库连接"""
        self.conn = psycopg2.connect(**self.config)
        logger.info(f"已连接到数据库: {self.config['database']}@{self.config['host']}")
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            logger.info("数据库连接已关闭")
    
    def ensure_target_table_exists(self):
        """确保目标表存在"""
        with self.conn.cursor() as cur:
            cur.execute(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = '{TARGET_TABLE}'
                );
            """)
            exists = cur.fetchone()[0]
            
            if not exists:
                logger.warning(f"目标表 {TARGET_TABLE} 不存在")
                raise RuntimeError(f"目标表 {TARGET_TABLE} 不存在")
            
            logger.info(f"目标表 {TARGET_TABLE} 已存在")
    
    def get_untranslated_articles(self, limit: Optional[int] = None) -> list:
        """获取尚未翻译的文章"""
        query = f"""
            SELECT s.* 
            FROM {SOURCE_TABLE} s
            WHERE s.language = 'mn'
            AND NOT EXISTS (
                SELECT 1 FROM {TARGET_TABLE} t 
                WHERE t.original_id = s.original_id
            )
            ORDER BY s.id
        """
        if limit:
            query += f" LIMIT {limit}"
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query)
            return cur.fetchall()
    
    def insert_translated_article(self, result: TranslationResult, dry_run: bool = False):
        """插入翻译后的文章（线程安全）"""
        if not result.success:
            return False
        
        if dry_run:
            return True
        
        article = result.article
        with self.conn.cursor() as cur:
            cur.execute(f"""
                INSERT INTO {TARGET_TABLE} (
                    original_id, title, content, publish_date, scraped_time,
                    url, source_name, language, category, file_path, created_at
                ) VALUES (
                    %(original_id)s, %(title)s, %(content)s, %(publish_date)s, %(scraped_time)s,
                    %(url)s, %(source_name)s, %(language)s, %(category)s, %(file_path)s, %(created_at)s
                )
                ON CONFLICT (original_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    content = EXCLUDED.content
            """, {
                "original_id": article["original_id"],
                "title": result.title_zh,
                "content": result.content_zh,
                "publish_date": article.get("publish_date"),
                "scraped_time": article.get("scraped_time"),
                "url": article.get("url"),
                "source_name": article.get("source_name"),
                "language": "zh",
                "category": article.get("category"),
                "file_path": article.get("file_path"),
                "created_at": datetime.now()
            })
        self.conn.commit()
        return True
    
    def get_stats(self) -> dict:
        """获取翻译统计信息"""
        with self.conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {SOURCE_TABLE} WHERE language = 'mn'")
            total_source = cur.fetchone()[0]
            
            cur.execute(f"SELECT COUNT(*) FROM {TARGET_TABLE}")
            completed = cur.fetchone()[0]
            
            return {
                "total_source": total_source,
                "completed": completed,
                "pending": total_source - completed
            }


# ============================================
# 主逻辑（并发版本）
# ============================================
async def translate_batch_concurrent(
    db: NewsDatabase,
    translator: XmorTranslator,
    batch_size: int = 50,
    limit: Optional[int] = None,
    dry_run: bool = False
):
    """并发批量翻译文章"""
    
    # 获取待翻译文章
    logger.info("正在从数据库获取待翻译文章...")
    articles = db.get_untranslated_articles(limit=limit)
    total = len(articles)
    
    if total == 0:
        logger.info("没有需要翻译的文章")
        return
    
    logger.info(f"找到 {total} 篇待翻译文章，开始并发翻译...")
    
    success_count = 0
    fail_count = 0
    
    # 分批处理，每批 batch_size 篇
    for batch_start in range(0, total, batch_size):
        batch_end = min(batch_start + batch_size, total)
        batch = articles[batch_start:batch_end]
        batch_num = batch_start // batch_size + 1
        total_batches = (total + batch_size - 1) // batch_size
        
        logger.info(f"--- 批次 {batch_num}/{total_batches}: 翻译 {len(batch)} 篇 ({batch_start+1}-{batch_end}/{total}) ---")
        
        # 并发翻译这一批文章
        tasks = [translator.translate_article(article) for article in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果并写入数据库（顺序写入，避免并发问题）
        for result in results:
            if isinstance(result, Exception):
                fail_count += 1
                logger.error(f"  ✗ 异常: {result}")
                continue
            
            if result.success:
                db.insert_translated_article(result, dry_run=dry_run)
                success_count += 1
                title_preview = (result.title_zh or "")[:40]
                logger.info(f"  ✓ {result.article['original_id']}: {title_preview}...")
            else:
                fail_count += 1
                logger.warning(f"  ✗ {result.article['original_id']}: {result.error}")
        
        # 打印批次统计
        logger.info(f"--- 批次完成 | 累计成功: {success_count} | 累计失败: {fail_count} ---")
    
    logger.info(f"\n翻译完成! 成功: {success_count}, 失败: {fail_count}")


async def main():
    parser = argparse.ArgumentParser(description="蒙语新闻批量翻译工具（并发版）")
    parser.add_argument("--concurrency", type=int, default=5, help="并发数量 (默认: 5)")
    parser.add_argument("--batch-size", type=int, default=50, help="批量处理大小 (默认: 50)")
    parser.add_argument("--limit", type=int, default=None, help="最大处理数量")
    parser.add_argument("--dry-run", action="store_true", help="试运行模式")
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("蒙语新闻批量翻译工具（并发版）")
    logger.info(f"并发数: {args.concurrency}, 批次大小: {args.batch_size}")
    logger.info("=" * 60)
    
    if args.dry_run:
        logger.info(">>> 试运行模式: 不会实际写入数据库 <<<")
    
    # 初始化
    db = NewsDatabase(DB_CONFIG)
    translator = XmorTranslator(XMOR_API_KEY, concurrency=args.concurrency)
    
    try:
        db.connect()
        db.ensure_target_table_exists()
        
        stats = db.get_stats()
        logger.info(f"当前状态: 源表={stats['total_source']}, 已完成={stats['completed']}, 待处理={stats['pending']}")
        
        await translate_batch_concurrent(
            db=db,
            translator=translator,
            batch_size=args.batch_size,
            limit=args.limit,
            dry_run=args.dry_run
        )
        
        stats = db.get_stats()
        logger.info(f"最终状态: 源表={stats['total_source']}, 已完成={stats['completed']}, 待处理={stats['pending']}")
        
    finally:
        await translator.close()
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
