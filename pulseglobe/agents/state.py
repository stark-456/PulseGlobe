"""
Agent 状态定义
用于 LangGraph 状态管理
"""
from typing import TypedDict, Optional
from dataclasses import dataclass, field


class KeywordState(TypedDict):
    """关键词感知阶段的状态"""
    
    # 输入
    country: str              # 目标国家（如"蒙古"）
    query: str                # 用户问题
    
    # 三类关键词列表
    tavily_keywords: list[str]    # Tavily搜索关键词（目标国语言/英语）
    social_keywords: list[str]    # 社交媒体关键词（目标国语言/英语）
    rag_keywords: list[str]       # RAG召回关键词（中文）
    
    # 迭代控制
    iteration: int                # 当前迭代次数
    max_iterations: int           # 最大迭代次数
    converged: bool               # 是否已收敛
    
    # 统计信息
    iteration_stats: list[dict]   # 每轮迭代的统计


class WorkerResult(TypedDict):
    """单个 Worker 的输出"""
    new_keywords: list[str]       # 发现的新关键词
    search_count: int             # 搜索次数
    result_count: int             # 结果数量


@dataclass
class OrchestratorConfig:
    """Orchestrator 配置"""
    max_iterations: int = 3                # 最大迭代次数
    convergence_threshold: float = 0.1     # 收敛阈值（新增关键词占比）
    max_keywords_per_list: int = 20        # 每个列表最大关键词数
    
    # Worker 配置
    tavily_enabled: bool = True
    rag_enabled: bool = True
    social_enabled: bool = True
    
    # 社交平台配置
    social_platforms: list[str] = field(default_factory=lambda: ["twitter", "tiktok"])
    social_post_count: int = 5
    social_comments_per_post: int = 0
