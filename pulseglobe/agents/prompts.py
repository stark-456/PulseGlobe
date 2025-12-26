"""
关键词提取 Prompt 模板
针对三种不同场景的关键词提取
支持交叉提取（从任意数据源提取三类关键词）
"""

# ============ 交叉关键词提取 ============
# 从搜索结果中同时提取三类关键词

CROSS_KEYWORD_EXTRACTION_PROMPT = """你是一个专业的舆情分析关键词提取专家。

## 任务
从搜索结果中提取三类关键词，用于后续的多渠道搜索。

## 背景
- 目标国家: {country}
- 用户问题: {query}
- 数据来源: {source_type}

## 现有关键词列表
- Tavily搜索关键词: {tavily_keywords}
- 社交媒体关键词: {social_keywords}
- RAG中文关键词: {rag_keywords}

## 搜索结果
{search_results}

## 重要约束
1. **不要离题**：所有新关键词必须与用户问题"{query}"直接相关
2. **语义去重**：不要提取与现有关键词语义相同的内容
3. **具体优先**：优先提取**具体的事件、人物、组织、政策名称**，而不是抽象的宏观词汇
   - ✓ 好: "蓝天电视台", "中蒙天然气管道", "蒙古国总理奥云额尔登"
   - ✗ 差: "中蒙合作", "新闻传播", "双边关系"

## 蒙古语言提示
- 蒙古人使用**西里尔字母蒙古语**，例如：Монголын мэдээ（蒙古新闻）
- 社交媒体上也常用英语

## 三类关键词要求

### 1. Tavily搜索关键词
- 使用{country}的官方语言（西里尔字母）或英语
- 适合Google/Bing搜索引擎
- 包含：具体的媒体名、记者名、新闻事件名、政策名称

### 2. 社交媒体关键词  
- 使用蒙古语（西里尔字母）或英语
- 适合Twitter/TikTok/YouTube搜索
- 包含：Hashtag(#xxx)、具体的KOL/博主名、特定事件标签

### 3. RAG中文关键词
- **必须使用中文**
- 适合向量相似度检索
- 包含：具体的事件中文描述、媒体或组织中文名称、人物中文名

## 输出格式
输出JSON格式:
{{
  "tavily_new": ["具体关键词1", "具体关键词2", ...],
  "social_new": ["#具体话题1", "具体KOL名", ...],
  "rag_new": ["具体事件中文名1", "具体组织中文名", ...],
  "reasoning": "简要说明发现了哪些具体的事件/人物/组织"
}}

如果某类没有发现新关键词，输出空数组。记住：具体优先，不要追求数量！
"""

# ============ 初始关键词生成（保持不变） ============

INITIAL_KEYWORD_PROMPT = """你是一个专业的舆情分析专家。

## 任务
根据用户问题，为{scenario}场景生成初始关键词列表。

## 背景
- 目标国家: {country}
- 用户问题: {query}

## 场景说明
{scenario_description}

## 输出格式
输出JSON格式:
{{
  "keywords": ["关键词1", "关键词2", ...],
  "reasoning": "简要说明关键词选择逻辑"
}}

生成5-10个关键词。
"""

# 场景描述
SCENARIO_DESCRIPTIONS = {
    "tavily": "搜索引擎搜索：使用目标国家语言或英语，适合Google/Bing搜索",
    "social": "社交媒体搜索：使用目标国家语言或英语，包含hashtag和热门话题词",
    "rag": "中文新闻库检索：必须使用中文，适合向量相似度检索",
}

# ============ 兼容旧接口（Worker内部使用） ============

TAVILY_KEYWORD_EXTRACTION_PROMPT = CROSS_KEYWORD_EXTRACTION_PROMPT
SOCIAL_KEYWORD_EXTRACTION_PROMPT = CROSS_KEYWORD_EXTRACTION_PROMPT
RAG_KEYWORD_EXTRACTION_PROMPT = CROSS_KEYWORD_EXTRACTION_PROMPT
