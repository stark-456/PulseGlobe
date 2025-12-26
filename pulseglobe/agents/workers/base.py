"""
Worker Agent 基类
定义关键词感知的通用流程
支持交叉关键词提取
"""
import json
import logging
from abc import ABC, abstractmethod
from typing import Any

from langchain_core.messages import HumanMessage
from pulseglobe.services.llm import get_json_llm_client
from pulseglobe.agents.prompts import CROSS_KEYWORD_EXTRACTION_PROMPT

logger = logging.getLogger(__name__)


class CrossKeywordResult:
    """交叉关键词提取结果"""
    def __init__(
        self,
        tavily_new: list[str] = None,
        social_new: list[str] = None,
        rag_new: list[str] = None,
        search_count: int = 0,
        result_count: int = 0,
    ):
        self.tavily_new = tavily_new or []
        self.social_new = social_new or []
        self.rag_new = rag_new or []
        self.search_count = search_count
        self.result_count = result_count


class BaseWorker(ABC):
    """
    Worker Agent 基类
    
    流程:
    1. 逐个关键词搜索
    2. 从结果中提取三类关键词（交叉更新）
    3. 返回新关键词
    """
    
    def __init__(self):
        self.llm = get_json_llm_client()
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Worker 名称"""
        pass
    
    @property
    @abstractmethod
    def source_type(self) -> str:
        """数据源类型描述，如 'Tavily网页搜索'、'社交媒体'、'RAG新闻库' """
        pass
    
    @abstractmethod
    async def search(self, keyword: str) -> list[dict]:
        """
        执行单个关键词搜索
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            搜索结果列表
        """
        pass
    
    async def run(
        self,
        country: str,
        query: str,
        keywords: list[str],
        tavily_keywords: list[str] = None,
        social_keywords: list[str] = None,
        rag_keywords: list[str] = None,
    ) -> CrossKeywordResult:
        """
        执行 Worker 任务（支持交叉关键词提取）
        
        Args:
            country: 目标国家
            query: 用户问题
            keywords: 本 Worker 使用的搜索关键词
            tavily_keywords: 现有 Tavily 关键词列表（用于去重）
            social_keywords: 现有社交关键词列表（用于去重）
            rag_keywords: 现有 RAG 关键词列表（用于去重）
            
        Returns:
            CrossKeywordResult 包含三类新关键词
        """
        logger.info(f"{'='*60}")
        logger.info(f"[{self.name}] ▶ 开始执行")
        logger.info(f"[{self.name}]   国家: {country}")
        logger.info(f"[{self.name}]   问题: {query[:50]}...")
        logger.info(f"[{self.name}]   输入关键词 ({len(keywords)}): {keywords[:5]}{'...' if len(keywords) > 5 else ''}")
        logger.info(f"{'='*60}")
        
        all_results = []
        search_count = 0
        
        # 逐个关键词搜索
        for i, keyword in enumerate(keywords, 1):
            logger.info(f"[{self.name}] 🔍 [{i}/{len(keywords)}] 搜索: '{keyword}'")
            try:
                results = await self.search(keyword)
                result_count = len(results)
                all_results.extend(results)
                search_count += 1
                logger.info(f"[{self.name}]    ✓ 获取 {result_count} 条结果")
            except Exception as e:
                logger.warning(f"[{self.name}]    ✗ 搜索失败: {e}")
                continue
        
        logger.info(f"[{self.name}] 📊 搜索完成: {search_count}/{len(keywords)} 成功，共 {len(all_results)} 条结果")
        
        if not all_results:
            logger.warning(f"[{self.name}] ⚠ 无搜索结果，跳过关键词提取")
            return CrossKeywordResult(search_count=search_count, result_count=0)
        
        # 交叉提取三类关键词
        logger.info(f"[{self.name}] 🤖 调用 LLM 提取三类关键词...")
        result = await self._extract_cross_keywords(
            country=country,
            query=query,
            tavily_keywords=tavily_keywords or [],
            social_keywords=social_keywords or [],
            rag_keywords=rag_keywords or [],
            search_results=all_results,
        )
        
        result.search_count = search_count
        result.result_count = len(all_results)
        
        logger.info(f"[{self.name}] ✨ 发现新关键词:")
        logger.info(f"[{self.name}]    Tavily +{len(result.tavily_new)}: {result.tavily_new}")
        logger.info(f"[{self.name}]    Social +{len(result.social_new)}: {result.social_new}")
        logger.info(f"[{self.name}]    RAG +{len(result.rag_new)}: {result.rag_new}")
        logger.info(f"[{self.name}] ◀ 执行完成")
        logger.info(f"{'='*60}")
        
        return result
    
    async def _extract_cross_keywords(
        self,
        country: str,
        query: str,
        tavily_keywords: list[str],
        social_keywords: list[str],
        rag_keywords: list[str],
        search_results: list[dict],
    ) -> CrossKeywordResult:
        """从搜索结果中提取三类关键词"""
        
        # 格式化搜索结果
        formatted = self._format_results(search_results, max_chars=8000)
        
        # 构建 Prompt
        prompt = CROSS_KEYWORD_EXTRACTION_PROMPT.format(
            country=country,
            query=query,
            source_type=self.source_type,
            tavily_keywords=json.dumps(tavily_keywords, ensure_ascii=False),
            social_keywords=json.dumps(social_keywords, ensure_ascii=False),
            rag_keywords=json.dumps(rag_keywords, ensure_ascii=False),
            search_results=formatted,
        )
        
        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            data = json.loads(response.content)
            
            reasoning = data.get("reasoning", "")
            if reasoning:
                logger.info(f"[{self.name}] 💡 LLM分析: {reasoning}")
            
            return CrossKeywordResult(
                tavily_new=data.get("tavily_new", []),
                social_new=data.get("social_new", []),
                rag_new=data.get("rag_new", []),
            )
        except json.JSONDecodeError as e:
            logger.error(f"[{self.name}] ✗ LLM响应解析失败: {e}")
            return CrossKeywordResult()
        except Exception as e:
            logger.error(f"[{self.name}] ✗ 关键词提取失败: {e}")
            return CrossKeywordResult()
    
    def _format_results(self, results: list[dict], max_chars: int = 8000) -> str:
        """格式化搜索结果为字符串"""
        formatted = []
        total_chars = 0
        
        for i, result in enumerate(results):
            title = result.get("title", "")
            content = result.get("content", "") or result.get("text", "") or result.get("description", "")
            
            if len(content) > 500:
                content = content[:500] + "..."
            
            item = f"[{i+1}] {title}\n{content}\n"
            
            if total_chars + len(item) > max_chars:
                break
            
            formatted.append(item)
            total_chars += len(item)
        
        return "\n".join(formatted)
