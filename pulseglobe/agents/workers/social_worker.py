"""
社交媒体 Worker
直接调用 TikHub API 进行社交平台搜索
"""
import logging
from typing import Optional

import httpx

from pulseglobe.core.config import get_config
from pulseglobe.agents.prompts import SOCIAL_KEYWORD_EXTRACTION_PROMPT
from .base import BaseWorker

logger = logging.getLogger(__name__)


class TikHubClient:
    """TikHub API 客户端"""
    
    def __init__(self, api_token: str, base_url: str = "https://api.tikhub.io"):
        self.base_url = base_url
        self.api_token = api_token
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
                "User-Agent": "PulseGlobe/0.1.0"
            }
        )
    
    async def get(self, endpoint: str, params: dict = None) -> dict:
        """发送 GET 请求"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            if data.get("code") == 200:
                return data
            else:
                raise Exception(f"API error: {data.get('message', 'Unknown')}")
        except httpx.HTTPStatusError as e:
            raise Exception(f"HTTP {e.response.status_code}: {e.response.text[:200]}")
    
    async def close(self):
        await self.client.aclose()


class SocialWorker(BaseWorker):
    """
    社交媒体搜索 Worker
    直接调用 TikHub API，支持 Twitter/TikTok/YouTube/Instagram
    """
    
    def __init__(
        self,
        platforms: list[str] = None,
        post_count: int = 5,
        comments_per_post: int = 0,
    ):
        """
        初始化社交媒体 Worker
        
        Args:
            platforms: 要搜索的平台列表，默认 ["twitter", "tiktok"]
            post_count: 每个关键词获取的帖子数量
            comments_per_post: 每个帖子获取的评论数量（0=不获取）
        """
        super().__init__()
        
        self.platforms = platforms or ["twitter", "tiktok"]
        self.post_count = post_count
        self.comments_per_post = comments_per_post
        
        # 初始化 TikHub 客户端
        config = get_config()
        tikhub_token = config.get("tikhub.api_token") or config.get("mcp.tikhub_api_token")
        tikhub_base_url = config.get("tikhub.base_url", "https://api.tikhub.io")
        
        if not tikhub_token:
            logger.warning("[SocialWorker] TikHub API token 未配置，将无法使用社交媒体搜索")
            self.client = None
        else:
            self.client = TikHubClient(tikhub_token, tikhub_base_url)
        
        logger.info(f"[SocialWorker] 初始化完成")
        logger.info(f"[SocialWorker]   平台: {self.platforms}")
        logger.info(f"[SocialWorker]   帖子数: {self.post_count}, 评论数: {self.comments_per_post}")
        logger.info(f"[SocialWorker]   API可用: {self.client is not None}")
    
    @property
    def name(self) -> str:
        return "SocialWorker"
    
    @property
    def source_type(self) -> str:
        return "社交媒体(Twitter/TikTok等)"
    
    @property
    def extraction_prompt(self) -> str:
        return SOCIAL_KEYWORD_EXTRACTION_PROMPT
    
    async def search(self, keyword: str) -> list[dict]:
        """
        在多个社交平台搜索
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            搜索结果列表，包含帖子和评论
        """
        if not self.client:
            logger.warning("[SocialWorker] API 客户端未初始化")
            return []
        
        all_results = []
        
        for platform in self.platforms:
            logger.info(f"[SocialWorker] 🔍 搜索平台: {platform}")
            try:
                results = await self._search_platform(platform, keyword)
                logger.info(f"[SocialWorker]    ✓ {platform}: 获取 {len(results)} 条结果")
                all_results.extend(results)
            except Exception as e:
                logger.warning(f"[SocialWorker]    ✗ {platform}: {e}")
                continue
        
        return all_results
    
    async def _search_platform(self, platform: str, keyword: str) -> list[dict]:
        """搜索单个平台"""
        if platform == "twitter":
            return await self._search_twitter(keyword)
        elif platform == "tiktok":
            return await self._search_tiktok(keyword)
        elif platform == "youtube":
            return await self._search_youtube(keyword)
        elif platform == "instagram":
            return await self._search_instagram(keyword)
        else:
            logger.warning(f"[SocialWorker] 不支持的平台: {platform}")
            return []
    
    # ============ Twitter ============
    async def _search_twitter(self, keyword: str) -> list[dict]:
        """搜索 Twitter"""
        results = []
        
        # 1. 搜索帖子
        response = await self.client.get(
            "/api/v1/twitter/web/fetch_search_timeline",
            params={"keyword": keyword, "search_type": "Top"}
        )
        
        timeline = response.get("data", {}).get("timeline", [])
        posts = [item for item in timeline if item.get("type") == "tweet"][:self.post_count]
        
        logger.debug(f"[SocialWorker] Twitter 获取 {len(posts)} 条帖子")
        
        for post in posts:
            tweet_id = post.get("tweet_id", "")
            user_info = post.get("user_info", {})
            
            result = {
                "platform": "twitter",
                "id": tweet_id,
                "title": "",
                "content": post.get("text", ""),
                "author": user_info.get("name", ""),
                "url": f"https://twitter.com/{user_info.get('screen_name', 'i')}/status/{tweet_id}",
                "comments": []
            }
            
            # 2. 获取评论（如果需要）
            if self.comments_per_post > 0:
                try:
                    comments = await self._get_twitter_comments(tweet_id)
                    result["comments"] = comments
                    logger.debug(f"[SocialWorker]   帖子 {tweet_id[:8]}... 获取 {len(comments)} 条评论")
                except Exception as e:
                    logger.warning(f"[SocialWorker]   获取评论失败: {e}")
            
            results.append(result)
        
        return results
    
    async def _get_twitter_comments(self, tweet_id: str) -> list[dict]:
        """获取 Twitter 评论"""
        response = await self.client.get(
            "/api/v1/twitter/web/fetch_post_comments",
            params={"tweet_id": tweet_id}
        )
        
        comments = response.get("data", {}).get("thread", [])[:self.comments_per_post]
        
        return [
            {
                "text": c.get("display_text") or c.get("text", ""),
                "author": c.get("author", {}).get("name", ""),
            }
            for c in comments
        ]
    
    # ============ TikTok ============
    async def _search_tiktok(self, keyword: str) -> list[dict]:
        """搜索 TikTok"""
        results = []
        
        response = await self.client.get(
            "/api/v1/tiktok/web/fetch_search_video",
            params={"keyword": keyword, "count": self.post_count, "sort_type": 0, "region": "US"}
        )
        
        videos = response.get("data", {}).get("videos", [])[:self.post_count]
        
        logger.debug(f"[SocialWorker] TikTok 获取 {len(videos)} 条视频")
        
        for video in videos:
            aweme_id = video.get("aweme_id", "")
            author = video.get("author", {})
            
            result = {
                "platform": "tiktok",
                "id": aweme_id,
                "title": video.get("desc", ""),
                "content": video.get("desc", ""),
                "author": author.get("nickname", ""),
                "url": f"https://www.tiktok.com/@{author.get('unique_id', '')}/video/{aweme_id}",
                "comments": []
            }
            
            if self.comments_per_post > 0:
                try:
                    comments = await self._get_tiktok_comments(aweme_id)
                    result["comments"] = comments
                except Exception as e:
                    logger.warning(f"[SocialWorker]   获取评论失败: {e}")
            
            results.append(result)
        
        return results
    
    async def _get_tiktok_comments(self, aweme_id: str) -> list[dict]:
        """获取 TikTok 评论"""
        response = await self.client.get(
            "/api/v1/tiktok/web/fetch_video_comments",
            params={"aweme_id": aweme_id, "count": self.comments_per_post}
        )
        
        comments = response.get("data", {}).get("comments", [])[:self.comments_per_post]
        
        return [
            {
                "text": c.get("text", ""),
                "author": c.get("user", {}).get("nickname", ""),
            }
            for c in comments
        ]
    
    # ============ YouTube ============
    async def _search_youtube(self, keyword: str) -> list[dict]:
        """搜索 YouTube"""
        results = []
        
        response = await self.client.get(
            "/api/v1/youtube/web/search_videos",
            params={"keyword": keyword, "count": self.post_count}
        )
        
        videos = response.get("data", {}).get("videos", [])[:self.post_count]
        
        logger.debug(f"[SocialWorker] YouTube 获取 {len(videos)} 条视频")
        
        for video in videos:
            video_id = video.get("video_id", "")
            
            result = {
                "platform": "youtube",
                "id": video_id,
                "title": video.get("title", ""),
                "content": video.get("description", ""),
                "author": video.get("channel_name", ""),
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "comments": []
            }
            
            if self.comments_per_post > 0:
                try:
                    comments = await self._get_youtube_comments(video_id)
                    result["comments"] = comments
                except Exception as e:
                    logger.warning(f"[SocialWorker]   获取评论失败: {e}")
            
            results.append(result)
        
        return results
    
    async def _get_youtube_comments(self, video_id: str) -> list[dict]:
        """获取 YouTube 评论"""
        response = await self.client.get(
            "/api/v1/youtube/web/fetch_video_comments",
            params={"video_id": video_id, "count": self.comments_per_post}
        )
        
        comments = response.get("data", {}).get("comments", [])[:self.comments_per_post]
        
        return [
            {
                "text": c.get("text", ""),
                "author": c.get("author_name", ""),
            }
            for c in comments
        ]
    
    # ============ Instagram ============
    async def _search_instagram(self, keyword: str) -> list[dict]:
        """搜索 Instagram (通过话题标签)"""
        results = []
        
        # 使用话题标签搜索
        hashtag = keyword.lstrip("#")
        
        response = await self.client.get(
            "/api/v1/instagram/web/fetch_hashtag_posts",
            params={"tag_name": hashtag, "count": self.post_count}
        )
        
        posts = response.get("data", {}).get("posts", [])[:self.post_count]
        
        logger.debug(f"[SocialWorker] Instagram 获取 {len(posts)} 条帖子")
        
        for post in posts:
            post_id = post.get("id", "")
            
            result = {
                "platform": "instagram",
                "id": post_id,
                "title": "",
                "content": post.get("caption", ""),
                "author": post.get("owner", {}).get("username", ""),
                "url": post.get("url", ""),
                "comments": []
            }
            
            if self.comments_per_post > 0:
                try:
                    comments = await self._get_instagram_comments(post_id)
                    result["comments"] = comments
                except Exception as e:
                    logger.warning(f"[SocialWorker]   获取评论失败: {e}")
            
            results.append(result)
        
        return results
    
    async def _get_instagram_comments(self, post_id: str) -> list[dict]:
        """获取 Instagram 评论"""
        response = await self.client.get(
            "/api/v1/instagram/web/fetch_post_comments",
            params={"post_id": post_id, "count": self.comments_per_post}
        )
        
        comments = response.get("data", {}).get("comments", [])[:self.comments_per_post]
        
        return [
            {
                "text": c.get("text", ""),
                "author": c.get("user", {}).get("username", ""),
            }
            for c in comments
        ]
    
    async def close(self):
        """关闭客户端"""
        if self.client:
            await self.client.close()
