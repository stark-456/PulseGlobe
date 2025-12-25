# PulseGlobe 跨境舆情分析智能体系统蓝图

## 概述

本文档是蒙古国跨境舆情分析多Agent系统的架构蓝图，基于您的设计方案进行了优化和细化。

```mermaid
graph TB
    subgraph "用户输入"
        U[用户查询/默认蒙古国舆情]
    end
    
    subgraph "Agent 1: 数据收集Agent"
        A1_1[关键词提取节点]
        A1_2[迭代细化节点]
        A1_3[海量数据采集节点]
    end
    
    subgraph "Agent 2: 主编Agent"
        A2_1[报告框架确定]
        A2_2[HTML模板生成]
    end
    
    subgraph "Agent 3: 写稿Agent"
        A3[章节内容生成]
    end
    
    subgraph "输出"
        O[完整HTML报告]
    end
    
    U --> A1_1 --> A1_2 --> A1_3 --> A2_1 --> A2_2 --> A3 --> O
```

---

## 前置条件：新闻数据库向量化

> [!IMPORTANT]
> 在启动Agent系统前，需要完成新闻数据的向量化处理

### 向量化方案建议

| 方案 | 优点 | 缺点 | 推荐场景 |
|------|------|------|----------|
| **Chroma** | 轻量、本地部署、Python原生 | 大规模性能有限 | 快速原型、中小规模 |
| **Milvus** | 高性能、分布式、成熟 | 部署复杂 | 生产环境、大规模 |
| **PostgreSQL + pgvector** | 与现有DB统一、事务支持 | 需要扩展 | 已有PostgreSQL环境 |

### 向量化流程
```mermaid
graph LR
    A[蒙古国新闻数据库] --> B[文本预处理]
    B --> C[Embedding模型]
    C --> D[向量数据库]
    D --> E[RAG检索就绪]
```

**推荐Embedding模型**: `text-embedding-3-small` 或 多语言模型如 `multilingual-e5-large`（支持蒙古语）

---

## 数据层架构设计

> [!IMPORTANT]
> **PulseGlobe系统边界**：只接收已翻译好的中文数据，只负责**向量化**和**RAG召回**

```mermaid
graph LR
    subgraph "用户职责"
        A[爬取数据] --> B[翻译成中文] --> C[按标准建表入库]
    end
    
    subgraph "PulseGlobe职责"
        D[向量化服务] --> E[RAG召回]
    end
    
    C --> D
```

**详细的数据准备指南请参考**：[data_preparation_guide.md](file:///d:/Work/DevelopPartTime/PulseGlobe/docs/data_preparation_guide.md)

---

## Agent 1: 数据收集Agent

### 1.1 节点一：关键词提取

```mermaid
graph TD
    Input[用户输入] --> Parse{是否有具体查询?}
    Parse -->|是| Extract[提取关键信息]
    Parse -->|否| Default[默认:蒙古国整体舆情]
    Extract --> Split[拆分为三类关键词列表]
    Default --> Split
    Split --> L1[Tavily搜索关键词]
    Split --> L2[社交媒体关键词]
    Split --> L3[RAG召回关键词]
```

**输出结构**:
```json
{
  "tavily_keywords": ["中蒙关系", "蒙古国经济", "稀土开采"],
  "social_keywords": ["Mongolia", "Монгол", "#Mongolia", "#УБ"],
  "rag_keywords": ["蒙古国政策", "乌兰巴托", "中蒙边境"]
}
```

> [!TIP]
> 社交媒体关键词需要包含英文、蒙古语、相关hashtag等多种形式

---

### 1.2 节点二：迭代细化（Reflection Loop）

这是您设计中非常精彩的部分——通过反思循环不断完善关键词列表。

> [!IMPORTANT]
> 采用 **主Agent + 子Agent + A2A协议** 架构实现
> 
> **详细设计文档**：[a2a_architecture.md](file:///d:/develop/PulseGlobe/docs/a2a_architecture.md)

#### A2A 多Agent架构概览

```mermaid
graph TB
    subgraph "主Agent (Orchestrator)"
        O[迭代细化主Agent]
        O -->|"A2A Task"| S1[Tavily搜索Agent]
        O -->|"A2A Task"| S2[RAG召回Agent]
        O -->|"A2A Task"| S3[社交媒体Agent]
        O --> R[反思节点]
    end
```

| 决策项 | 选择 |
|--------|------|
| 部署模式 | 进程内（单进程，内存通信） |
| A2A SDK | 官方 `a2a-sdk` |
| 翻译服务 | 讯蒙 Tengri API（可切换） |

#### 迭代流程

```mermaid
graph TD
    Start[初始关键词列表] --> Loop{迭代次数 < N 且未收敛?}
    Loop -->|是| Parallel[并行调用三个子Agent]
    Parallel --> S1[Tavily Agent: 搜索→翻译→摘要]
    Parallel --> S2[RAG Agent: 召回→摘要]
    Parallel --> S3[Social Agent: MCP→翻译→摘要]
    S1 & S2 & S3 --> Merge[合并结果]
    Merge --> Reflect[反思节点: 更新关键词]
    Reflect --> Converge{收敛判断}
    Converge -->|未收敛| Loop
    Converge -->|已收敛| Output[最终关键词列表 + 三类摘要]
    Loop -->|否| Output
```

**收敛判断**：当新增关键词占比 < 10% 时认为收敛

**反思Prompt模板示例**:
```
基于以下新获取的信息：
{new_information_summary}

请分析：
1. 是否发现了之前遗漏的重要主题/实体/事件？
2. 当前关键词列表是否需要补充或调整？
3. 输出更新后的关键词列表（保持JSON格式）
```

---

### 1.3 节点三：海量数据采集

```mermaid
graph TD
    Keywords[最终关键词列表] --> Parallel
    
    subgraph Parallel[并行数据采集]
        T[Tavily深度搜索]
        R[RAG多轮召回]
        M[MCP社交数据]
    end
    
    Parallel --> Monitor{监控Agent评估}
    Monitor -->|数据不全| Parallel
    Monitor -->|数据充分| Store[分类存储]
    
    Store --> D1[(搜索引擎数据)]
    Store --> D2[(新闻RAG数据)]
    Store --> D3[(社交媒体数据)]
    Store --> Summary[三类数据摘要]
```

**监控Agent的判断标准**:
- 每类数据是否达到最小数量阈值
- 关键词覆盖率是否达标
- 数据时间分布是否合理（避免只有旧数据）

---

## Agent 2: 主编Agent

### 2.1 报告框架确定

**输入**:
- 用户原始问题
- 三类数据摘要
- 关键词列表

**输出结构**:
```json
{
  "report_title": "2024年12月蒙古国舆情分析报告",
  "chapters": [
    {
      "id": 1,
      "title": "舆情概述与核心发现",
      "sections": [
        {"id": "1.1", "title": "本期舆情热度趋势", "data_source": ["tavily", "rag"]},
        {"id": "1.2", "title": "核心事件摘要", "data_source": ["tavily", "rag"]}
      ]
    },
    {
      "id": 2,
      "title": "政治与外交动态",
      "sections": [
        {"id": "2.1", "title": "中蒙关系最新进展", "data_source": ["tavily", "rag"]},
        {"id": "2.2", "title": "国际关系动态", "data_source": ["tavily"]}
      ]
    },
    {
      "id": 7,
      "title": "社交媒体舆情分析",
      "sections": [
        {"id": "7.1", "title": "各平台热门话题", "data_source": ["social"]},
        {"id": "7.2", "title": "舆情情感分析", "data_source": ["social"]}
      ]
    }
  ]
}
```

> [!IMPORTANT]
> 必须包含"社交媒体舆情分析"章节，这是您设计的硬性要求

---

### 2.2 HTML模板生成

**模板架构**:
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{{report_title}}</title>
    <script src="echarts.min.js"></script>
    <style>/* 主题样式 */</style>
</head>
<body>
    <header>
        <h1>{{report_title}}</h1>
        <p class="meta">生成时间: {{generated_at}}</p>
    </header>
    
    <nav id="toc"><!-- 自动生成目录 --></nav>
    
    <!-- 章节占位符 -->
    <section id="chapter-1">
        <h2>{{chapter_1_title}}</h2>
        <div class="content">{{chapter_1_content}}</div>
        <div class="chart" id="chart-1-1"></div>
    </section>
    
    <!-- 更多章节... -->
    
    <script>
        // ECharts 初始化脚本占位
        // {{echarts_init_scripts}}
    </script>
</body>
</html>
```

**风格确定逻辑**:
- 经济类报告 → 商务蓝色调
- 政治类报告 → 稳重灰色调
- 社会类报告 → 活力渐变色

---

## Agent 3: 写稿Agent

### 章节生成流程

```mermaid
graph TD
    Chapters[章节列表] --> Loop[遍历每个章节]
    Loop --> Fetch[根据data_source获取对应数据]
    Fetch --> LLM[调用LLM生成内容]
    LLM --> Parse[解析输出]
    Parse --> Text[HTML文字内容]
    Parse --> Chart[ECharts JSON数据]
    Text --> Store1[存储到章节内容池]
    Chart --> Store2[存储到图表数据池]
    Store1 --> Next{还有下一章?}
    Store2 --> Next
    Next -->|是| Loop
    Next -->|否| Done[所有章节完成]
```

### Few-shot Prompt 模板

```
你是一位专业的舆情分析报告撰写者。

## 任务
根据提供的数据，撰写报告章节内容。

## 输入
- 章节标题: {{section_title}}
- 相关数据: {{section_data}}

## 输出格式要求
请严格按照以下JSON格式输出：

{
  "content_html": "<div class='section-content'>..你的分析内容..</div>",
  "charts": [
    {
      "chart_id": "chart-{{section_id}}-1",
      "chart_type": "line|bar|pie|radar",
      "echarts_option": {
        // 完整的ECharts option配置
      }
    }
  ]
}

## 示例
【输入】
章节标题: 舆情热度趋势
相关数据: [{"date": "2024-12-15", "count": 120}, {"date": "2024-12-16", "count": 145}...]

【输出】
{
  "content_html": "<div class='section-content'><p>本周蒙古国相关舆情热度呈现<strong>上升趋势</strong>...</p></div>",
  "charts": [
    {
      "chart_id": "chart-1-1",
      "chart_type": "line",
      "echarts_option": {
        "title": {"text": "舆情热度趋势"},
        "xAxis": {"type": "category", "data": ["12-15", "12-16", ...]},
        "yAxis": {"type": "value"},
        "series": [{"data": [120, 145, ...], "type": "line", "smooth": true}]
      }
    }
  ]
}
```

---

## 最终组装

```python
# 伪代码: HTML报告组装脚本
def assemble_report(template_html, chapters_content, charts_data):
    soup = BeautifulSoup(template_html, 'html.parser')
    
    for chapter_id, content in chapters_content.items():
        # 填充文字内容
        placeholder = soup.find(id=f"chapter-{chapter_id}")
        placeholder.find(class_='content').append(BeautifulSoup(content, 'html.parser'))
    
    # 生成ECharts初始化脚本
    echarts_scripts = generate_echarts_init(charts_data)
    soup.find(id='echarts-scripts').string = echarts_scripts
    
    return str(soup)
```

---

## 设计评审与优化建议

### ✅ 设计优点

1. **迭代反思机制** - 通过多轮反思不断完善关键词，这是非常专业的做法
2. **数据源分类明确** - Tavily/RAG/社交三类数据各有侧重，覆盖全面
3. **模块化程度高** - Agent职责划分清晰，便于独立开发测试
4. **输出格式规范** - HTML+ECharts的组合提供了丰富的可视化能力

### ⚠️ 需要考虑的问题

| 问题 | 建议方案 |
|------|----------|
| 蒙古语支持 | Embedding和LLM需选择多语言模型 |
| 成本控制 | 设置迭代次数上限，添加Token预算监控 |
| 错误恢复 | 添加checkpoint机制，支持断点续跑 |
| 数据时效 | 社交数据设置时间窗口过滤 |
| MCP调用并发 | 社交平台API可能有速率限制 |

### 🚀 进阶优化建议

1. **添加质量评估Agent** - 在写稿后检查内容质量、事实一致性
2. **缓存机制** - 相同关键词的搜索结果可缓存复用
3. **增量更新** - 支持在现有报告基础上更新而非全部重生成
4. **多语言报告** - 一次生成中文+英文双语版本

---

## 技术栈（已确定）

| 组件 | 选型 | 备注 |
|------|------|------|
| **Agent框架** | LangGraph | 状态图驱动，适合复杂流程 |
| **A2A 协议** | `a2a-sdk` | 官方Python SDK，进程内模式 |
| **向量数据库** | PostgreSQL + pgvector | 与现有数据库统一 |
| **LLM** | 多平台兼容 | 见下方兼容层设计 |
| **Embedding** | 多平台兼容 | 见下方兼容层设计 |
| **翻译服务** | 讯蒙 Tengri | 可切换，见下方翻译服务 |
| **搜索引擎** | Tavily API | 已有 |
| **社交数据** | TikHub MCP | 已有 |

---

## 模型兼容层设计

> [!IMPORTANT]
> 用户可灵活配置不同平台的模型，系统通过统一接口调用

### 配置文件结构

```yaml
# config/models.yaml

llm:
  provider: "siliconflow"  # openai / azure / siliconflow / newapi / ollama
  model: "deepseek-v3"
  api_key: "${SILICONFLOW_API_KEY}"
  base_url: "https://api.siliconflow.cn/v1"
  
embedding:
  provider: "siliconflow"
  model: "qwen3-embedding"
  api_key: "${SILICONFLOW_API_KEY}"
  base_url: "https://api.siliconflow.cn/v1"

translation:  # 运行时翻译配置（可灵活切换提供商）
  provider: "xmor"  # xmor / llm / baidu / google
  api_key: "${XMOR_API_KEY}"
  base_url: "https://api.xmor.cn"
  # 备选：使用LLM翻译
  # provider: "llm"
  # model: "deepseek-v3"
```

### 支持的模型平台

| 平台 | provider值 | 说明 |
|------|-----------|------|
| OpenAI官方 | `openai` | GPT-4o, text-embedding-3-small |
| Azure OpenAI | `azure` | 企业部署 |
| 硅基流动 | `siliconflow` | DeepSeek, Qwen等国产模型 |
| New API中转 | `newapi` | 自建中转站，兼容OpenAI格式 |
| Ollama本地 | `ollama` | 本地部署的开源模型 |
| 智谱AI | `zhipu` | GLM-4系列 |
| 百度千帆 | `qianfan` | 文心一言 |

### 支持的翻译服务

| 平台 | provider值 | 说明 |
|------|-----------|------|
| **讯蒙科技** | `xmor` | Tengri API，支持蒙古语 |
| LLM翻译 | `llm` | 使用配置的LLM进行翻译 |
| 百度翻译 | `baidu` | 百度翻译API |
| 谷歌翻译 | `google` | Google Translate API |

### 模型客户端抽象层

```python
# pulseglobe/models/client.py

from abc import ABC, abstractmethod
from typing import List

class BaseLLMClient(ABC):
    """LLM统一接口"""
    
    @abstractmethod
    def chat(self, messages: List[dict], **kwargs) -> str:
        pass
    
    @abstractmethod
    def stream_chat(self, messages: List[dict], **kwargs):
        pass

class BaseEmbeddingClient(ABC):
    """Embedding统一接口"""
    
    @abstractmethod
    def embed(self, text: str) -> List[float]:
        pass
    
    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        pass

# 工厂函数
def create_llm_client(config: dict) -> BaseLLMClient:
    provider = config["provider"]
    
    if provider == "openai":
        return OpenAIClient(config)
    elif provider == "siliconflow":
        return SiliconFlowClient(config)
    elif provider == "newapi":
        return NewAPIClient(config)  # OpenAI兼容格式
    elif provider == "ollama":
        return OllamaClient(config)
    else:
        raise ValueError(f"Unsupported provider: {provider}")
```

### OpenAI兼容适配器

大多数平台都兼容OpenAI格式，可复用同一个适配器：

```python
# pulseglobe/models/openai_compatible.py

from openai import OpenAI

class OpenAICompatibleClient(BaseLLMClient):
    """适用于所有OpenAI兼容API的客户端"""
    
    def __init__(self, config: dict):
        self.client = OpenAI(
            api_key=config["api_key"],
            base_url=config.get("base_url", "https://api.openai.com/v1")
        )
        self.model = config["model"]
    
    def chat(self, messages: List[dict], **kwargs) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            **kwargs
        )
        return response.choices[0].message.content

# 硅基流动、New API中转站都可以用这个
SiliconFlowClient = OpenAICompatibleClient
NewAPIClient = OpenAICompatibleClient
```

---

## 运行时外文翻译方案

> [!WARNING]
> Tavily搜索和MCP社交数据可能返回外文内容，需要运行时翻译

### 翻译时机

```mermaid
graph LR
    A[Tavily搜索结果] --> B{语言检测}
    C[MCP社交数据] --> B
    B -->|中文| D[直接使用]
    B -->|外文| E[翻译服务]
    E --> D
    D --> F[存入数据池]
```

### 翻译服务抽象

```python
# pulseglobe/translation/service.py

class TranslationService:
    """运行时翻译服务"""
    
    def __init__(self, config: dict):
        self.provider = config.get("provider", "llm")
        
        if self.provider == "llm":
            # 使用LLM做翻译
            self.llm = create_llm_client(config)
        elif self.provider == "baidu":
            self.client = BaiduTranslateClient(config)
        elif self.provider == "google":
            self.client = GoogleTranslateClient(config)
    
    def translate(self, text: str, target_lang: str = "zh") -> str:
        if self.provider == "llm":
            return self._translate_with_llm(text, target_lang)
        else:
            return self.client.translate(text, target_lang)
    
    def _translate_with_llm(self, text: str, target_lang: str) -> str:
        prompt = f"""请将以下内容翻译成{target_lang}，只输出翻译结果：

{text}"""
        return self.llm.chat([{"role": "user", "content": prompt}])
    
    def detect_language(self, text: str) -> str:
        """检测文本语言"""
        # 简单实现：检测是否包含中文字符
        import re
        if re.search(r'[\u4e00-\u9fff]', text):
            return "zh"
        return "foreign"
```

### 数据处理流程

```python
# pulseglobe/agents/data_collection/processor.py

class DataProcessor:
    """数据预处理器 - 处理外文翻译"""
    
    def __init__(self, translator: TranslationService):
        self.translator = translator
    
    def process_tavily_results(self, results: List[dict]) -> List[dict]:
        """处理Tavily搜索结果"""
        processed = []
        for item in results:
            if self.translator.detect_language(item["content"]) != "zh":
                item["content_original"] = item["content"]
                item["content"] = self.translator.translate(item["content"])
                item["title_original"] = item.get("title", "")
                item["title"] = self.translator.translate(item.get("title", ""))
            processed.append(item)
        return processed
    
    def process_social_data(self, data: List[dict]) -> List[dict]:
        """处理MCP社交数据"""
        # 社交数据通常是短文本，批量翻译
        processed = []
        for item in data:
            text = item.get("text", "") or item.get("content", "")
            if text and self.translator.detect_language(text) != "zh":
                item["text_original"] = text
                item["text"] = self.translator.translate(text)
            processed.append(item)
        return processed
```

---

## 环境变量配置

```bash
# .env 示例

# 硅基流动
SILICONFLOW_API_KEY=sk-xxx

# New API中转站
NEWAPI_BASE_URL=https://your-newapi-server.com/v1
NEWAPI_API_KEY=sk-xxx

# Tavily搜索
TAVILY_API_KEY=tvly-xxx

# TikHub MCP (已配置)
TIKHUB_API_TOKEN=xxx

# 讯蒙 Tengri 翻译API
XMOR_API_KEY=sk-xxxxx

# 数据库
DATABASE_URL=postgresql://user:pass@localhost:5432/pulseglobe
```

---

## 下一步行动

- [x] 确认Agent框架：LangGraph
- [x] 确认模型兼容层设计
- [x] 确认运行时翻译方案
- [x] 确认A2A多Agent架构（见 [a2a_architecture.md](file:///d:/develop/PulseGlobe/docs/a2a_architecture.md)）
- [x] 确认A2A SDK：官方 `a2a-sdk`
- [x] 确认翻译服务：讯蒙 Tengri API
- [ ] 开始编码实现

