-- ============================================
-- 简化版迁移脚本（手动修改日期）
-- 用法：直接在数据库客户端执行，修改下面的日期
-- ============================================

-- ========== 修改这里的日期 ==========
-- 开始日期
-- SET @start_date = '2025-12-01';
-- 结束日期
-- SET @end_date = '2025-12-31';

-- ========== 预览要迁移的数据 ==========
SELECT
    COUNT(*) as total_count,
    MIN(publish_date) as min_date,
    MAX(publish_date) as max_date
FROM news_articles_mn_zh
WHERE
    publish_date >= '2025-12-01' -- 修改开始日期
    AND publish_date <= '2025-12-31';
-- 修改结束日期

-- ========== 执行迁移 ==========
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
    'MN',
    category,
    url,
    created_at
FROM news_articles_mn_zh
WHERE
    publish_date >= '2025-12-01' -- 修改开始日期
    AND publish_date <= '2025-12-31' -- 修改结束日期
ON CONFLICT (doc_id) DO
UPDATE
SET
    title = EXCLUDED.title,
    content = EXCLUDED.content;

-- ========== 迁移全部数据（无日期限制）==========
-- 取消下面的注释即可迁移全部数据
/*
INSERT INTO pulseglobe_news (
doc_id, title, content, publish_date, source_name, 
source_country, category, url, created_at
)
SELECT 
original_id, title, content, publish_date, source_name,
'MN', category, url, created_at
FROM news_articles_mn_zh
ON CONFLICT (doc_id) DO UPDATE SET
title = EXCLUDED.title,
content = EXCLUDED.content;
*/

-- ========== 验证结果 ==========
SELECT COUNT(*) as total FROM pulseglobe_news;