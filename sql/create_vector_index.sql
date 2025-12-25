-- ============================================
-- 向量索引创建脚本
-- 在数据量增大后执行以加速检索
-- ============================================

-- 修改向量维度为 1024（如果需要）
-- ALTER TABLE pulseglobe_news
-- ALTER COLUMN embedding TYPE vector(1024);

-- ========== HNSW 索引（推荐） ==========
-- 优点：召回质量高，查询速度快
-- 缺点：构建时间较长，占用更多内存
CREATE INDEX idx_news_embedding_hnsw ON pulseglobe_news USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- ========== 或者 IVFFlat 索引 ==========
-- 优点：构建速度快
-- 缺点：召回质量略低
-- 需要有数据后才能创建，lists 建议设置为 sqrt(行数)
-- CREATE INDEX idx_news_embedding_ivfflat
-- ON pulseglobe_news
-- USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ========== 查询示例 ==========
-- 相似度搜索（带日期过滤）
-- SELECT doc_id, title,
--        1 - (embedding <=> '[0.1, 0.2, ...]'::vector) AS similarity
-- FROM pulseglobe_news
-- WHERE source_country = 'MN'
--   AND publish_date BETWEEN '2025-12-01' AND '2025-12-31'
-- ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector
-- LIMIT 10;

-- ========== 查看索引状态 ==========
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE
    tablename = 'pulseglobe_news';