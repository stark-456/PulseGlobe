"""
数据采集测试
测试完整的采集流程（关键词感知 → 数据采集）
"""
import asyncio
import logging
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


async def main():
    """测试完整采集流程"""
    from pulseglobe.agents import KeywordOrchestrator, OrchestratorConfig
    from pulseglobe.agents.collection_orchestrator import DataCollectionOrchestrator, CollectionConfig
    
    print("=" * 70)
    print("PulseGlobe 数据采集测试")
    print("=" * 70)
    
    # ============ 阶段一：关键词感知 ============
    print("\n【阶段一】关键词感知...")
    
    keyword_config = OrchestratorConfig(
        max_iterations=2,
        convergence_threshold=0.1,
        max_keywords_per_list=10,
        tavily_enabled=True,
        rag_enabled=True,
        social_enabled=True,
        social_platforms=["twitter"],
        social_post_count=3,
        social_comments_per_post=0,
    )
    
    keyword_orchestrator = KeywordOrchestrator(keyword_config)
    
    try:
        keyword_result = await keyword_orchestrator.run(
            country="蒙古",
            query="中蒙间新闻传播最新情况，新闻传播专业领域，中国新闻传播到蒙古国对其的影响",
        )
    finally:
        keyword_orchestrator.close()
    
    print(f"\n关键词感知结果:")
    print(f"  Tavily关键词 ({len(keyword_result['tavily_keywords'])}): {keyword_result['tavily_keywords'][:5]}...")
    print(f"  Social关键词 ({len(keyword_result['social_keywords'])}): {keyword_result['social_keywords'][:5]}...")
    print(f"  RAG关键词 ({len(keyword_result['rag_keywords'])}): {keyword_result['rag_keywords'][:5]}...")
    
    # ============ 阶段二：数据采集 ============
    print("\n【阶段二】数据采集...")
    
    collection_config = CollectionConfig(
        tavily_enabled=True,
        tavily_max_results=10,  # 测试时减少
        social_enabled=True,
        social_platforms=["twitter"],
        social_post_count=5,
        social_comments_per_post=5,
        rag_enabled=True,
        rag_max_results=10,
        translation_provider="llm",  # 使用 LLM 翻译测试
    )
    
    collection_orchestrator = DataCollectionOrchestrator(collection_config)
    
    try:
        collection_result = await collection_orchestrator.collect(
            tavily_keywords=keyword_result['tavily_keywords'][:3],  # 测试时只用3个
            social_keywords=keyword_result['social_keywords'][:2],
            rag_keywords=keyword_result['rag_keywords'][:3],
        )
    finally:
        collection_orchestrator.close()
    
    print(f"\n数据采集结果:")
    print(f"  Session ID: {collection_result.session_id}")
    print(f"  总数据量: {collection_result.stats['total']}")
    print(f"  - Tavily: {collection_result.stats.get('tavily', 0)}")
    print(f"  - Social: {collection_result.stats.get('social', 0)}")
    print(f"  - RAG: {collection_result.stats.get('rag', 0)}")
    print(f"  耗时: {collection_result.duration_seconds:.1f}s")
    
    print("\n" + "=" * 70)
    print("测试完成")
    print(f"Session ID: {collection_result.session_id}")
    print("可使用此ID查询采集的数据")


if __name__ == "__main__":
    asyncio.run(main())
