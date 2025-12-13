"""
TikHub 客户端测试
测试 API 连接和基本请求功能
"""
import pytest
import asyncio
from src.utils.tikhub_client import TikHubClient, TikHubAPIError


@pytest.mark.asyncio
async def test_client_initialization():
    """测试客户端初始化"""
    client = TikHubClient()
    assert client is not None
    assert client.base_url is not None
    assert client.api_token is not None
    await client.close()


@pytest.mark.asyncio
async def test_get_request():
    """测试 GET 请求（需要有效的 API token）"""
    client = TikHubClient()
    
    try:
        # 这里需要替换为实际可用的端点
        # response = await client.get("/api/v1/test")
        # assert response is not None
        pass
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_error_handling():
    """测试错误处理"""
    client = TikHubClient()
    
    try:
        # 测试无效端点
        with pytest.raises(TikHubAPIError):
            await client.get("/api/v1/invalid_endpoint")
    finally:
        await client.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
