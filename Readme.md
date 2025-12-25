# PulseGlobe

跨境舆情分析 AI 系统

## 项目结构

```
PulseGlobe/
├── config/                 # 配置文件
│   └── models.yaml         # 统一模型配置
├── docs/                   # 设计文档
│   ├── a2a_architecture.md # A2A 多 Agent 架构
│   ├── data_preparation_guide.md # 数据准备指南
│   └── implementation_plan.md    # 实现计划
├── pulseglobe/             # 核心代码
│   └── config.py           # 配置加载器
├── scripts/                # 工具脚本
│   ├── translate_mn_news.py  # 蒙语翻译脚本
│   └── vectorize_news.py     # 向量化脚本
├── sql/                    # SQL 脚本
│   ├── migrate_simple.sql    # 数据迁移
│   └── create_vector_index.sql # 向量索引
└── MCP/                    # MCP 服务
```

## 快速开始

1. 复制环境变量配置
```bash
cp .env.example .env
# 编辑 .env 填入 API Key
```

2. 数据翻译（蒙语 → 中文）
```bash
cd scripts
uv run translate_mn_news.py --limit 100
```

3. 向量化
```bash
uv run vectorize_news.py
```