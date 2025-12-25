-- ============================================
-- 数据迁移脚本：news_articles_mn_zh → pulseglobe_news
-- 用途：将翻译后的中文新闻导入 RAG 向量库
-- ============================================

-- ========== 配置区域 ==========
-- 修改以下日期范围来控制迁移数据
-- 设置为 NULL 表示不限制

-- 开始日期（包含）
-- 示例: '2025-12-01' 或 NULL
\set start_date '''2025-12-01'''

-- 结束日期（包含）
-- 示例: '2025-12-31' 或 NULL
\set end_date '''2025-12-31'''

-- ========== 迁移脚本 ==========

-- 查看将要迁移的数据量（预览）
SELECT
    COUNT(*) as total_count,
    MIN(publish_date) as min_date,
    MAX(publish_date) as max_date
FROM news_articles_mn_zh
WHERE (
        publish_date >=:start_date
        OR:start_date IS NULL
    )
    AND (
        publish_date <=:end_date
        OR:end_date IS NULL
    );

-- 执行迁移（INSERT）
INSERT INTO
    pulseglobe_news (
        doc_id,
        title,
        content,
        publish_date,
        source_name,
        source_country,
        category,
        url,
        created_at
    )
SELECT
    original_id,
    title,
    content,
    publish_date,
    source_name,
    'MN', -- 蒙古国
    category,
    url,
    created_at
FROM news_articles_mn_zh
WHERE (
        publish_date >=:start_date
        OR:start_date IS NULL
    )
    AND (
        publish_date <=:end_date
        OR:end_date IS NULL
    )
ON CONFLICT (doc_id) DO
UPDATE
SET
    title = EXCLUDED.title,
    content = EXCLUDED.content;

-- 验证迁移结果
SELECT
    'pulseglobe_news' as table_name,
    COUNT(*) as total,
    COUNT(*) FILTER (
        WHERE
            embedding IS NULL
    ) as pending_embedding
FROM pulseglobe_news;