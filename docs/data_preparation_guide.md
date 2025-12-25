# PulseGlobe 数据准备指南

本文档指导用户如何准备数据，以便 PulseGlobe 系统进行向量化和 RAG 召回。

---

## 前置条件

- PostgreSQL 14+ 数据库
- pgvector 扩展（0.5.0+）
- 已翻译成**中文**的新闻数据

---

## 第一步：安装 pgvector 扩展

```sql
-- 需要数据库管理员权限
CREATE EXTENSION IF NOT EXISTS vector;
```

> **验证安装**：执行 `SELECT vector_version();` 应返回版本号

---

## 第二步：创建标准数据表

```sql
CREATE TABLE pulseglobe_news (
    -- 主键
    id SERIAL PRIMARY KEY,
    doc_id VARCHAR(50) UNIQUE NOT NULL,
    
    -- 【必填】已翻译的中文内容
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    
    -- 【必填】元数据
    publish_date DATE NOT NULL,
    source_name VARCHAR(100) NOT NULL,
    source_country CHAR(2) NOT NULL,
    category VARCHAR(50),
    url TEXT,
    
    -- 【系统填充】向量字段 - 留空即可
    embedding vector(2560),
    
    -- 审计字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建必要索引
CREATE INDEX idx_news_country ON pulseglobe_news(source_country);
CREATE INDEX idx_news_date ON pulseglobe_news(publish_date);
CREATE INDEX idx_news_category ON pulseglobe_news(category);
```

---

## 第三步：准备并导入数据

### 字段说明

| 字段 | 必填 | 说明 | 示例 |
|------|------|------|------|
| `doc_id` | ✅ | 唯一文档ID | `"TyfNy4jhDpT"` |
| `title` | ✅ | 中文标题 | `"三岁男孩获得国际象棋评级"` |
| `content` | ✅ | 中文正文 | `"印度男孩萨尔瓦吉亚..."` |
| `publish_date` | ✅ | 发布日期 | `2025-12-05` |
| `source_name` | ✅ | 来源网站 | `"Eagle"` |
| `source_country` | ✅ | ISO国家代码 | `"MN"` (蒙古国) |
| `category` | ❌ | 分类标签 | `"体育"` |
| `url` | ❌ | 原文链接 | `"https://eagle.mn/..."` |
| `embedding` | ❌ | **留空** | PulseGlobe 自动填充 |

### 常用国家代码

| 国家 | ISO代码 |
|------|---------|
| 蒙古国 | `MN` |
| 越南 | `VN` |
| 韩国 | `KR` |
| 日本 | `JP` |
| 泰国 | `TH` |

### 数据导入示例

```sql
INSERT INTO pulseglobe_news 
(doc_id, title, content, publish_date, source_name, source_country, category, url)
VALUES
(
  'TyfNy4jhDpT',
  '三岁男孩获得国际象棋联合会官方评级',
  '印度男孩萨尔瓦吉亚·辛格·库什瓦哈获得了国际象棋联合会(FIDE)的官方评级...',
  '2025-12-05',
  'Eagle',
  'MN',
  '体育',
  'https://eagle.mn/r/TyfNy4jhDpT'
);
```

---

## 第四步：验证数据

```sql
-- 检查数据量
SELECT source_country, COUNT(*) 
FROM pulseglobe_news 
GROUP BY source_country;

-- 检查待向量化数据
SELECT COUNT(*) 
FROM pulseglobe_news 
WHERE embedding IS NULL;
```

---

## 完成

数据准备完成后，启动 PulseGlobe 系统，将自动：

1. 扫描 `embedding IS NULL` 的记录
2. 调用 Embedding API 生成向量
3. 回填 `embedding` 字段
4. 创建向量索引，RAG 召回就绪

---

## 常见问题

### Q: 为什么必须是中文？
PulseGlobe 使用中文优化的 Embedding 模型，中文数据召回效果最佳。

### Q: 向量维度 1536 是固定的吗？
是的，基于 OpenAI `text-embedding-3-small` 模型。如需其他模型，请修改表结构。
