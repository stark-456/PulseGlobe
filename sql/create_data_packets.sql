-- 数据包表：存储采集的海量数据
-- 每条记录是一个"文件袋"，便于后续报告生成时按需取用

CREATE TABLE IF NOT EXISTS data_packets ( id SERIAL PRIMARY KEY,

-- 会话标识
session_id VARCHAR(50) NOT NULL, -- 采集批次ID，如 'sess_20241226_mongolia'

-- 数据来源
source_type VARCHAR(20) NOT NULL, -- 'tavily' | 'social' | 'rag'
source_detail VARCHAR(50), -- 'twitter' | 'tiktok' | 'youtube' | 'news_db'

-- 关键词关联
keyword VARCHAR(500), -- 触发此数据的关键词
keyword_type VARCHAR(20), -- 'tavily' | 'social' | 'rag'

-- 内容
title TEXT,
content TEXT, -- 原始内容（可能是外文，可能含评论）
content_zh TEXT, -- 翻译后的中文内容
summary TEXT, -- LLM生成的摘要（100字以内）

-- 元数据
url TEXT,
author VARCHAR(200),
publish_date TIMESTAMP,
platform VARCHAR(50), -- 'twitter' | 'tiktok' | 'google' | 'rag'
engagement JSONB, -- {likes, retweets, views, comments_count}

-- 管理字段
created_at TIMESTAMP DEFAULT NOW(),
tags TEXT [], -- 自定义标签，用于报告章节匹配

-- 避免重复
content_hash VARCHAR(64)              -- 内容哈希，用于去重
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_packets_session ON data_packets (session_id);

CREATE INDEX IF NOT EXISTS idx_packets_source ON data_packets (source_type);

CREATE INDEX IF NOT EXISTS idx_packets_keyword ON data_packets (keyword);

CREATE INDEX IF NOT EXISTS idx_packets_tags ON data_packets USING GIN (tags);

CREATE INDEX IF NOT EXISTS idx_packets_hash ON data_packets (content_hash);

-- 唯一约束（同一session内，相同内容不重复存储）
-- 注意：如果已存在则跳过
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_packets_session_hash'
    ) THEN
        ALTER TABLE data_packets 
        ADD CONSTRAINT uq_packets_session_hash UNIQUE (session_id, content_hash);

END IF;

END $$;

COMMENT ON TABLE data_packets IS '数据包表：存储采集的海量数据，每条是一个"文件袋"';

COMMENT ON COLUMN data_packets.session_id IS '采集批次ID，一次完整采集对应一个session';

COMMENT ON COLUMN data_packets.source_type IS '数据来源类型：tavily/social/rag';

COMMENT ON COLUMN data_packets.summary IS 'LLM生成的摘要，100字以内';

COMMENT ON COLUMN data_packets.tags IS '标签数组，用于报告章节匹配';