"""
Orchestrator Agent
协调三个 Worker 进行迭代关键词感知（交叉更新版本）
使用 LangGraph 实现状态图
"""
import asyncio
import json
import logging
from typing import Literal

from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END

from pulseglobe.agents.state import KeywordState, OrchestratorConfig
from pulseglobe.agents.prompts import INITIAL_KEYWORD_PROMPT, SCENARIO_DESCRIPTIONS
from pulseglobe.agents.workers import TavilyWorker, RAGWorker, SocialWorker
from pulseglobe.agents.workers.base import CrossKeywordResult
from pulseglobe.services.llm import get_json_llm_client

logger = logging.getLogger(__name__)


class KeywordOrchestrator:
    """
    关键词感知 Orchestrator
    
    协调 Tavily、RAG、Social 三个 Worker 进行迭代式关键词发现
    支持交叉更新：每个渠道的结果都会更新三类关键词列表
    """
    
    def __init__(self, config: OrchestratorConfig = None):
        self.config = config or OrchestratorConfig()
        self.llm = get_json_llm_client()
        
        # 初始化 Workers
        self._init_workers()
        
        # 构建 LangGraph
        self.graph = self._build_graph()
        
        logger.info(f"[Orchestrator] 初始化完成")
        logger.info(f"[Orchestrator]   最大迭代: {self.config.max_iterations}")
        logger.info(f"[Orchestrator]   收敛阈值: {self.config.convergence_threshold}")
        logger.info(f"[Orchestrator]   Workers: tavily={self.config.tavily_enabled}, "
                   f"rag={self.config.rag_enabled}, social={self.config.social_enabled}")
    
    def _init_workers(self):
        """初始化 Worker 实例"""
        self.tavily_worker = TavilyWorker() if self.config.tavily_enabled else None
        self.rag_worker = RAGWorker() if self.config.rag_enabled else None
        self.social_worker = SocialWorker(
            platforms=self.config.social_platforms,
            post_count=self.config.social_post_count,
            comments_per_post=self.config.social_comments_per_post,
        ) if self.config.social_enabled else None
    
    def _build_graph(self) -> StateGraph:
        """构建 LangGraph 状态图"""
        workflow = StateGraph(KeywordState)
        
        workflow.add_node("generate_initial_keywords", self._generate_initial_keywords)
        workflow.add_node("run_workers", self._run_workers)
        workflow.add_node("check_convergence", self._check_convergence)
        
        workflow.set_entry_point("generate_initial_keywords")
        
        workflow.add_edge("generate_initial_keywords", "run_workers")
        workflow.add_edge("run_workers", "check_convergence")
        
        workflow.add_conditional_edges(
            "check_convergence",
            self._should_continue,
            {"continue": "run_workers", "end": END}
        )
        
        return workflow.compile()
    
    async def run(self, country: str, query: str) -> KeywordState:
        """运行关键词感知流程"""
        logger.info(f"{'='*70}")
        logger.info(f"[Orchestrator] ▶ 开始关键词感知")
        logger.info(f"[Orchestrator]   国家: {country}")
        logger.info(f"[Orchestrator]   问题: {query}")
        logger.info(f"{'='*70}")
        
        initial_state: KeywordState = {
            "country": country,
            "query": query,
            "tavily_keywords": [],
            "social_keywords": [],
            "rag_keywords": [],
            "iteration": 0,
            "max_iterations": self.config.max_iterations,
            "converged": False,
            "iteration_stats": [],
        }
        
        final_state = await self.graph.ainvoke(initial_state)
        
        logger.info(f"{'='*70}")
        logger.info(f"[Orchestrator] ◀ 关键词感知完成")
        logger.info(f"[Orchestrator]   迭代次数: {final_state['iteration']}")
        logger.info(f"[Orchestrator]   Tavily ({len(final_state['tavily_keywords'])}): {final_state['tavily_keywords']}")
        logger.info(f"[Orchestrator]   Social ({len(final_state['social_keywords'])}): {final_state['social_keywords']}")
        logger.info(f"[Orchestrator]   RAG ({len(final_state['rag_keywords'])}): {final_state['rag_keywords']}")
        logger.info(f"{'='*70}")
        
        return final_state
    
    # ============ 节点实现 ============
    
    async def _generate_initial_keywords(self, state: KeywordState) -> KeywordState:
        """生成初始关键词"""
        logger.info(f"\n[Orchestrator] 📝 生成初始关键词...")
        
        country = state["country"]
        query = state["query"]
        
        tasks = []
        if self.config.tavily_enabled:
            tasks.append(self._generate_keywords_for_scenario("tavily", country, query))
        if self.config.social_enabled:
            tasks.append(self._generate_keywords_for_scenario("social", country, query))
        if self.config.rag_enabled:
            tasks.append(self._generate_keywords_for_scenario("rag", country, query))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        idx = 0
        if self.config.tavily_enabled:
            if not isinstance(results[idx], Exception):
                state["tavily_keywords"] = results[idx]
                logger.info(f"[Orchestrator]   Tavily初始: {results[idx]}")
            idx += 1
        
        if self.config.social_enabled:
            if not isinstance(results[idx], Exception):
                state["social_keywords"] = results[idx]
                logger.info(f"[Orchestrator]   Social初始: {results[idx]}")
            idx += 1
        
        if self.config.rag_enabled:
            if not isinstance(results[idx], Exception):
                state["rag_keywords"] = results[idx]
                logger.info(f"[Orchestrator]   RAG初始: {results[idx]}")
        
        return state
    
    async def _generate_keywords_for_scenario(
        self, scenario: str, country: str, query: str
    ) -> list[str]:
        """为特定场景生成初始关键词"""
        prompt = INITIAL_KEYWORD_PROMPT.format(
            scenario=scenario,
            country=country,
            query=query,
            scenario_description=SCENARIO_DESCRIPTIONS[scenario],
        )
        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            result = json.loads(response.content)
            return result.get("keywords", [])
        except Exception as e:
            logger.error(f"[Orchestrator] 生成{scenario}关键词失败: {e}")
            return []
    
    async def _run_workers(self, state: KeywordState) -> KeywordState:
        """并行运行三个 Worker（交叉更新）"""
        state["iteration"] += 1
        iteration = state["iteration"]
        
        logger.info(f"\n[Orchestrator] 🔄 迭代 {iteration}/{state['max_iterations']}")
        
        # 记录迭代前
        before = {
            "tavily": len(state["tavily_keywords"]),
            "social": len(state["social_keywords"]),
            "rag": len(state["rag_keywords"]),
        }
        
        # 并行运行 Workers，传入所有现有关键词用于去重
        tasks = []
        worker_names = []
        
        if self.tavily_worker and state["tavily_keywords"]:
            tasks.append(self.tavily_worker.run(
                country=state["country"],
                query=state["query"],
                keywords=state["tavily_keywords"],
                tavily_keywords=state["tavily_keywords"],
                social_keywords=state["social_keywords"],
                rag_keywords=state["rag_keywords"],
            ))
            worker_names.append("tavily")
        
        if self.social_worker and state["social_keywords"]:
            tasks.append(self.social_worker.run(
                country=state["country"],
                query=state["query"],
                keywords=state["social_keywords"],
                tavily_keywords=state["tavily_keywords"],
                social_keywords=state["social_keywords"],
                rag_keywords=state["rag_keywords"],
            ))
            worker_names.append("social")
        
        if self.rag_worker and state["rag_keywords"]:
            tasks.append(self.rag_worker.run(
                country=state["country"],
                query=state["query"],
                keywords=state["rag_keywords"],
                tavily_keywords=state["tavily_keywords"],
                social_keywords=state["social_keywords"],
                rag_keywords=state["rag_keywords"],
            ))
            worker_names.append("rag")
        
        if not tasks:
            logger.warning("[Orchestrator] 没有可运行的 Worker")
            return state
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 交叉合并：每个 Worker 的结果都更新三个列表
        new_counts = {"tavily": 0, "social": 0, "rag": 0}
        
        for name, result in zip(worker_names, results):
            if isinstance(result, Exception):
                logger.error(f"[Orchestrator] {name} Worker 失败: {result}")
                continue
            
            if not isinstance(result, CrossKeywordResult):
                continue
            
            # 合并到三个列表
            if result.tavily_new:
                state["tavily_keywords"] = self._merge_keywords(
                    state["tavily_keywords"], result.tavily_new
                )
                new_counts["tavily"] += len(result.tavily_new)
            
            if result.social_new:
                state["social_keywords"] = self._merge_keywords(
                    state["social_keywords"], result.social_new
                )
                new_counts["social"] += len(result.social_new)
            
            if result.rag_new:
                state["rag_keywords"] = self._merge_keywords(
                    state["rag_keywords"], result.rag_new
                )
                new_counts["rag"] += len(result.rag_new)
        
        # 记录统计
        after = {
            "tavily": len(state["tavily_keywords"]),
            "social": len(state["social_keywords"]),
            "rag": len(state["rag_keywords"]),
        }
        
        stats = {"iteration": iteration, "before": before, "after": after, "new": new_counts}
        state["iteration_stats"].append(stats)
        
        logger.info(f"[Orchestrator] 📊 迭代 {iteration} 统计（交叉更新）:")
        logger.info(f"[Orchestrator]   Tavily: {before['tavily']} → {after['tavily']} (+{new_counts['tavily']})")
        logger.info(f"[Orchestrator]   Social: {before['social']} → {after['social']} (+{new_counts['social']})")
        logger.info(f"[Orchestrator]   RAG: {before['rag']} → {after['rag']} (+{new_counts['rag']})")
        
        return state
    
    async def _check_convergence(self, state: KeywordState) -> KeywordState:
        """检查是否收敛"""
        if not state["iteration_stats"]:
            return state
        
        latest = state["iteration_stats"][-1]
        total_new = sum(latest["new"].values())
        total_current = sum(latest["after"].values())
        
        new_ratio = total_new / max(total_current, 1)
        
        if new_ratio < self.config.convergence_threshold:
            state["converged"] = True
            logger.info(f"[Orchestrator] ✅ 已收敛 ({new_ratio:.1%} < {self.config.convergence_threshold:.1%})")
        else:
            logger.info(f"[Orchestrator] ⏳ 未收敛 ({new_ratio:.1%} >= {self.config.convergence_threshold:.1%})")
        
        return state
    
    def _should_continue(self, state: KeywordState) -> Literal["continue", "end"]:
        if state["converged"]:
            return "end"
        if state["iteration"] >= state["max_iterations"]:
            logger.info(f"[Orchestrator] ⏹ 达到最大迭代 {state['max_iterations']}")
            return "end"
        return "continue"
    
    def _merge_keywords(self, existing: list[str], new: list[str]) -> list[str]:
        """合并关键词（字符串去重）"""
        seen = set()
        merged = []
        for kw in existing + new:
            kw_lower = kw.lower().strip()
            if kw_lower not in seen:
                seen.add(kw_lower)
                merged.append(kw)
        return merged[:self.config.max_keywords_per_list]
    
    def close(self):
        if self.rag_worker:
            self.rag_worker.close()
