"""
Worker Agent 测试
"""
import asyncio
import logging
import pytest
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志级别（测试时可调整）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class TestTavilyWorker:
    """Tavily Worker 测试"""
    
    @pytest.mark.asyncio
    async def test_search(self):
        """测试搜索功能"""
        from pulseglobe.agents.workers import TavilyWorker
        
        worker = TavilyWorker()
        results = await worker.search("Mongolia economy")
        
        assert isinstance(results, list)
        if results:
            assert "title" in results[0]
            assert "content" in results[0]
    
    @pytest.mark.asyncio
    async def test_run(self):
        """测试完整运行流程"""
        from pulseglobe.agents.workers import TavilyWorker
        
        worker = TavilyWorker()
        result = await worker.run(
            country="蒙古",
            query="蒙古国最新经济政策",
            keywords=["Mongolia economy", "Монгол эдийн засаг"],
        )
        
        assert "new_keywords" in result
        assert "search_count" in result
        assert result["search_count"] == 2


class TestRAGWorker:
    """RAG Worker 测试"""
    
    @pytest.mark.asyncio
    async def test_search(self):
        """测试向量检索"""
        from pulseglobe.agents.workers import RAGWorker
        
        worker = RAGWorker()
        try:
            results = await worker.search("蒙古国经济")
            assert isinstance(results, list)
        finally:
            worker.close()
    
    @pytest.mark.asyncio
    async def test_run(self):
        """测试完整运行流程"""
        from pulseglobe.agents.workers import RAGWorker
        
        worker = RAGWorker()
        try:
            result = await worker.run(
                country="蒙古",
                query="蒙古国最新经济政策",
                keywords=["蒙古国经济", "中蒙关系"],
            )
            
            assert "new_keywords" in result
            assert "search_count" in result
        finally:
            worker.close()


class TestSocialWorker:
    """Social Worker 测试"""
    
    @pytest.mark.asyncio
    async def test_search(self):
        """测试社交媒体搜索"""
        from pulseglobe.agents.workers import SocialWorker
        
        # 只测试 Twitter 平台
        worker = SocialWorker(platforms=["twitter"])
        results = await worker.search("#Mongolia")
        
        assert isinstance(results, list)


# 简单的命令行测试入口
async def main():
    """命令行测试入口"""
    print("=" * 60)
    print("PulseGlobe Worker Agents 测试")
    print("=" * 60)
    
    # 测试 Tavily
    print("\n[1] 测试 TavilyWorker...")
    from pulseglobe.agents.workers import TavilyWorker
    
    try:
        worker = TavilyWorker()
        result = await worker.run(
            country="蒙古",
            query="蒙古国舆情分析",
            keywords=["Mongolia news", "Монголын мэдээ"],
        )
        print(f"    搜索次数: {result['search_count']}")
        print(f"    结果数量: {result['result_count']}")
        print(f"    新关键词: {result['new_keywords']}")
    except Exception as e:
        print(f"    错误: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试 RAG
    print("\n[2] 测试 RAGWorker...")
    from pulseglobe.agents.workers import RAGWorker
    
    try:
        worker = RAGWorker()
        result = await worker.run(
            country="蒙古",
            query="蒙古国舆情分析",
            keywords=["蒙古国", "中蒙关系"],
        )
        print(f"    搜索次数: {result['search_count']}")
        print(f"    结果数量: {result['result_count']}")
        print(f"    新关键词: {result['new_keywords']}")
        worker.close()
    except Exception as e:
        print(f"    错误: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试 Social
    print("\n[3] 测试 SocialWorker...")
    from pulseglobe.agents.workers import SocialWorker
    
    try:
        worker = SocialWorker(platforms=["twitter"])
        result = await worker.run(
            country="蒙古",
            query="蒙古国舆情分析",
            keywords=["#Mongolia", "Mongolia news"],
        )
        print(f"    搜索次数: {result['search_count']}")
        print(f"    结果数量: {result['result_count']}")
        print(f"    新关键词: {result['new_keywords']}")
    except Exception as e:
        print(f"    错误: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("测试完成")


if __name__ == "__main__":
    asyncio.run(main())
