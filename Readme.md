# PulseGlobe

跨境舆情分析智能体系统

## 快速开始

1. 复制环境变量配置
```bash
cp .env.example .env
# 编辑 .env 填入 API Key
```

2. 安装依赖
```bash
uv sync
```

3. 测试 Worker Agents
```bash
uv run python tests/test_workers.py
```

## 项目结构

```
pulseglobe/
├── config/settings.yaml      # 配置文件
├── core/config.py            # 配置加载器
├── services/llm.py           # LLM 服务
└── agents/workers/           # Worker Agents
    ├── tavily_worker.py      # Tavily 搜索
    ├── rag_worker.py         # RAG 向量检索
    └── social_worker.py      # 社交媒体搜索
```
