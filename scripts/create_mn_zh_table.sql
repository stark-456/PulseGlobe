-- ============================================
-- PulseGlobe 中文新闻表创建脚本
-- 表名: news_articles_mn_zh
-- 说明: 与 news_articles 表结构完全一致，存储翻译后的中文版本
-- ============================================

-- 删除旧表（如果需要重建）
DROP TABLE IF EXISTS news_articles_mn_zh;

-- 如果需要，先安装 pgvector 扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- 创建中文新闻表（与 news_articles 结构一致）
CREATE TABLE news_articles_mn_zh (
    id SERIAL PRIMARY KEY,
    original_id VARCHAR(50) UNIQUE,
    title TEXT,
    content TEXT,
    publish_date DATE,
    scraped_time TIMESTAMP,
    url TEXT,
    source_name VARCHAR(50),
    language VARCHAR(10) DEFAULT 'zh',
    category VARCHAR(100),
    file_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    embedding vector (1536)
);

-- 创建索引
CREATE INDEX idx_mn_zh_original_id ON news_articles_mn_zh (original_id);

CREATE INDEX idx_mn_zh_publish_date ON news_articles_mn_zh (publish_date);

CREATE INDEX idx_mn_zh_category ON news_articles_mn_zh (category);