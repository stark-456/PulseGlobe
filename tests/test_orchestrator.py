"""
Orchestrator 测试脚本
运行完整的关键词感知流程
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
    """测试 Orchestrator"""
    from pulseglobe.agents import KeywordOrchestrator, OrchestratorConfig
    
    print("=" * 70)
    print("PulseGlobe 关键词感知 Orchestrator 测试")
    print("=" * 70)
    
    # 配置
    config = OrchestratorConfig(
        max_iterations=2,              # 测试时减少迭代次数
        convergence_threshold=0.1,
        max_keywords_per_list=15,
        tavily_enabled=True,
        rag_enabled=True,
        social_enabled=True,           # 如果没有 TikHub token 可设为 False
        social_platforms=["twitter", "tiktok", "youtube"],  # 三个平台
        social_post_count=3,
        social_comments_per_post=0,
    )
    
    # 创建 Orchestrator
    orchestrator = KeywordOrchestrator(config)
    
    try:
        # 运行
        result = await orchestrator.run(
            country="蒙古",
            query="中蒙间新闻传播最新情况，新闻传播专业领域，中国新闻传播到蒙古国对其的影响",
        )
        
        print("\n" + "=" * 70)
        print("最终结果")
        print("=" * 70)
        print(f"\n迭代次数: {result['iteration']}")
        print(f"是否收敛: {result['converged']}")
        
        print(f"\n📌 Tavily 关键词 ({len(result['tavily_keywords'])}):")
        for i, kw in enumerate(result['tavily_keywords'], 1):
            print(f"  {i}. {kw}")
        
        print(f"\n📌 Social 关键词 ({len(result['social_keywords'])}):")
        for i, kw in enumerate(result['social_keywords'], 1):
            print(f"  {i}. {kw}")
        
        print(f"\n📌 RAG 关键词 ({len(result['rag_keywords'])}):")
        for i, kw in enumerate(result['rag_keywords'], 1):
            print(f"  {i}. {kw}")
        
        print("\n📊 迭代统计:")
        for stat in result['iteration_stats']:
            print(f"  第 {stat['iteration']} 轮: "
                  f"Tavily +{stat['new']['tavily']}, "
                  f"Social +{stat['new']['social']}, "
                  f"RAG +{stat['new']['rag']}")
        
    finally:
        orchestrator.close()
    
    print("\n" + "=" * 70)
    print("测试完成")


if __name__ == "__main__":
    asyncio.run(main())
