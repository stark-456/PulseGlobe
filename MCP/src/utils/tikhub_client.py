"""
TikHub API 客户端封装
提供统一的 API 调用接口，处理认证、错误处理和重试
"""
import httpx
from typing import Dict, Any, Optional
import logging
from ..config import settings

logger = logging.getLogger(__name__)


class TikHubAPIError(Exception):
    """TikHub API 错误"""
    pass


class TikHubClient:
    """TikHub API 客户端"""
    
    def __init__(self):
        self.base_url = settings.tikhub_api_base_url
        self.api_token = settings.tikhub_api_token
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers=self._get_headers()
        )
    
    def _get_headers(self) -> Dict[str, str]:
        """构建请求头"""
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "User-Agent": "PulseGlobe-MCP/0.1.0"
        }
    
    async def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        发送 HTTP 请求到 TikHub API
        
        Args:
            method: HTTP 方法 (GET, POST, etc.)
            endpoint: API 端点路径
            params: URL 查询参数
            json_data: JSON 请求体
            max_retries: 最大重试次数
            
        Returns:
            API 响应数据
            
        Raises:
            TikHubAPIError: API 请求失败
        """
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(max_retries):
            try:
                response = await self.client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data
                )
                
                # 检查响应状态
                if response.status_code == 200:
                    data = response.json()
                    
                    # TikHub API 返回 {"code": 200, "message": "Request successful...", "data": {...}}
                    # code=200 表示成功
                    if data.get("code") == 200:
                        return data
                    else:
                        error_msg = data.get("message", "Unknown error")
                        error_code = data.get("code", "unknown")
                        logger.error(f"TikHub API error (code {error_code}): {error_msg}")
                        raise TikHubAPIError(f"API error (code {error_code}): {error_msg}")
                
                elif response.status_code == 401:
                    raise TikHubAPIError("Authentication failed. Please check your API token.")
                
                elif response.status_code == 429:
                    logger.warning(f"Rate limit exceeded, retry attempt {attempt + 1}/{max_retries}")
                    if attempt < max_retries - 1:
                        await httpx.AsyncClient().aclose()  # Wait before retry
                        continue
                    raise TikHubAPIError("Rate limit exceeded")
                
                else:
                    logger.error(f"HTTP {response.status_code}: {response.text}")
                    raise TikHubAPIError(f"HTTP {response.status_code}: {response.text}")
                    
            except httpx.RequestError as e:
                logger.error(f"Request failed: {e}")
                if attempt < max_retries - 1:
                    continue
                raise TikHubAPIError(f"Request failed: {e}")
        
        raise TikHubAPIError("Max retries exceeded")
    
    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """GET 请求"""
        return await self.request("GET", endpoint, params=params)
    
    async def post(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """POST 请求"""
        return await self.request("POST", endpoint, json_data=json_data)
    
    async def close(self):
        """关闭客户端连接"""
        await self.client.aclose()


# 全局客户端实例
_client: Optional[TikHubClient] = None


def get_client() -> TikHubClient:
    """获取全局 TikHub 客户端实例"""
    global _client
    if _client is None:
        _client = TikHubClient()
    return _client
