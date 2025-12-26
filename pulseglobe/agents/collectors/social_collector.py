"""
社交媒体数据采集器
采集 Twitter/TikTok/YouTube 等平台数据
"""
import logging

import httpx

from pulseglobe.core.config import get_config
from .base import BaseCollector

logger = logging.getLogger(__name__)


class SocialCollector(BaseCollector):
    """
    社交媒体采集器
    直接调用 TikHub API
    """
    
    def __init__(
        self,
        platforms: list[str] = None,
        post_count: int = 10,
        comments_per_post: int = 10,
        **kwargs
    ):
        """
        Args:
            platforms: 平台列表，默认 ["twitter", "tiktok", "youtube"]
            post_count: 每个关键词的帖子数
            comments_per_post: 每个帖子的评论数
        """
        super().__init__(**kwargs)
        
        self.platforms = platforms or ["twitter", "tiktok", "youtube"]
        self.post_count = post_count
        self.comments_per_post = comments_per_post
        
        # TikHub 客户端
        config = get_config()
        tikhub_config = config.get("tikhub", {})
        api_token = tikhub_config.get("api_token", "")
        base_url = tikhub_config.get("base_url", "https://api.tikhub.io")
        
        if not api_token:
            logger.warning("[SocialCollector] TikHub API token 未配置")
            self.client = None
        else:
            self.client = httpx.AsyncClient(
                base_url=base_url,
                timeout=30.0,
                headers={
                    "Authorization": f"Bearer {api_token}",
                    "Content-Type": "application/json",
                }
            )
        
        logger.info(f"[SocialCollector] 初始化完成")
        logger.info(f"[SocialCollector]   platforms={self.platforms}")
        logger.info(f"[SocialCollector]   post_count={post_count}, comments={comments_per_post}")
    
    @property
    def source_type(self) -> str:
        return "social"
    
    @property
    def source_detail(self) -> str:
        return ",".join(self.platforms)
    
    async def search(self, keyword: str) -> list[dict]:
        """在多个平台搜索"""
        if not self.client:
            logger.warning("[SocialCollector] 客户端未初始化")
            return []
        
        all_results = []
        
        for platform in self.platforms:
            try:
                results = await self._search_platform(platform, keyword)
                all_results.extend(results)
                logger.debug(f"[SocialCollector] {platform}: {len(results)} 条")
            except Exception as e:
                logger.warning(f"[SocialCollector] {platform} 搜索失败: {e}")
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
            return []
    
    async def _api_get(self, endpoint: str, params: dict) -> dict:
        """API GET 请求"""
        response = await self.client.get(endpoint, params=params)
        response.raise_for_status()
        data = response.json()
        if data.get("code") != 200:
            raise Exception(f"API error: {data.get('message')}")
        return data
    
    # ============ Twitter ============
    async def _search_twitter(self, keyword: str) -> list[dict]:
        results = []
        
        data = await self._api_get(
            "/api/v1/twitter/web/fetch_search_timeline",
            {"keyword": keyword, "search_type": "Top"}
        )
        
        timeline = data.get("data", {}).get("timeline", [])
        posts = [item for item in timeline if item.get("type") == "tweet"][:self.post_count]
        
        for post in posts:
            tweet_id = post.get("tweet_id", "")
            user_info = post.get("user_info", {})
            
            result = {
                "title": "",
                "content": post.get("text", ""),
                "url": f"https://twitter.com/{user_info.get('screen_name', 'i')}/status/{tweet_id}",
                "author": user_info.get("name", ""),
                "platform": "twitter",
                "engagement": {
                    "likes": post.get("favorites", 0),
                    "retweets": post.get("retweets", 0),
                    "views": post.get("views", 0),
                },
                "comments": [],
            }
            
            # 获取评论
            if self.comments_per_post > 0 and tweet_id:
                try:
                    comments = await self._get_twitter_comments(tweet_id)
                    result["comments"] = comments
                except:
                    pass
            
            results.append(result)
        
        return results
    
    async def _get_twitter_comments(self, tweet_id: str) -> list[dict]:
        data = await self._api_get(
            "/api/v1/twitter/web/fetch_post_comments",
            {"tweet_id": tweet_id}
        )
        comments = data.get("data", {}).get("thread", [])[:self.comments_per_post]
        return [{"text": c.get("display_text") or c.get("text", ""), "author": c.get("author", {}).get("name", "")} for c in comments]
    
    # ============ TikTok ============
    async def _search_tiktok(self, keyword: str) -> list[dict]:
        results = []
        
        data = await self._api_get(
            "/api/v1/tiktok/web/fetch_search_video",
            {"keyword": keyword, "count": self.post_count, "sort_type": 0, "region": "US"}
        )
        
        videos = data.get("data", {}).get("videos", [])[:self.post_count]
        
        for video in videos:
            aweme_id = video.get("aweme_id", "")
            author = video.get("author", {})
            
            result = {
                "title": video.get("desc", ""),
                "content": video.get("desc", ""),
                "url": f"https://www.tiktok.com/@{author.get('unique_id', '')}/video/{aweme_id}",
                "author": author.get("nickname", ""),
                "platform": "tiktok",
                "engagement": {
                    "likes": video.get("statistics", {}).get("digg_count", 0),
                    "views": video.get("statistics", {}).get("play_count", 0),
                    "comments_count": video.get("statistics", {}).get("comment_count", 0),
                },
                "comments": [],
            }
            
            if self.comments_per_post > 0 and aweme_id:
                try:
                    comments = await self._get_tiktok_comments(aweme_id)
                    result["comments"] = comments
                except:
                    pass
            
            results.append(result)
        
        return results
    
    async def _get_tiktok_comments(self, aweme_id: str) -> list[dict]:
        data = await self._api_get(
            "/api/v1/tiktok/web/fetch_video_comments",
            {"aweme_id": aweme_id, "count": self.comments_per_post}
        )
        comments = data.get("data", {}).get("comments", [])[:self.comments_per_post]
        return [{"text": c.get("text", ""), "author": c.get("user", {}).get("nickname", "")} for c in comments]
    
    # ============ YouTube ============
    async def _search_youtube(self, keyword: str) -> list[dict]:
        results = []
        
        data = await self._api_get(
            "/api/v1/youtube/web/search_videos",
            {"keyword": keyword, "count": self.post_count}
        )
        
        videos = data.get("data", {}).get("videos", [])[:self.post_count]
        
        for video in videos:
            video_id = video.get("video_id", "")
            
            result = {
                "title": video.get("title", ""),
                "content": video.get("description", ""),
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "author": video.get("channel_name", ""),
                "platform": "youtube",
                "engagement": {
                    "views": video.get("view_count", 0),
                    "likes": video.get("like_count", 0),
                },
                "comments": [],
            }
            
            if self.comments_per_post > 0 and video_id:
                try:
                    comments = await self._get_youtube_comments(video_id)
                    result["comments"] = comments
                except:
                    pass
            
            results.append(result)
        
        return results
    
    async def _get_youtube_comments(self, video_id: str) -> list[dict]:
        data = await self._api_get(
            "/api/v1/youtube/web/fetch_video_comments",
            {"video_id": video_id, "count": self.comments_per_post}
        )
        comments = data.get("data", {}).get("comments", [])[:self.comments_per_post]
        return [{"text": c.get("text", ""), "author": c.get("author_name", "")} for c in comments]
    
    # ============ Instagram ============
    async def _search_instagram(self, keyword: str) -> list[dict]:
        results = []
        hashtag = keyword.lstrip("#")
        
        data = await self._api_get(
            "/api/v1/instagram/web/fetch_hashtag_posts",
            {"tag_name": hashtag, "count": self.post_count}
        )
        
        posts = data.get("data", {}).get("posts", [])[:self.post_count]
        
        for post in posts:
            result = {
                "title": "",
                "content": post.get("caption", ""),
                "url": post.get("url", ""),
                "author": post.get("owner", {}).get("username", ""),
                "platform": "instagram",
                "engagement": {
                    "likes": post.get("like_count", 0),
                    "comments_count": post.get("comment_count", 0),
                },
                "comments": [],
            }
            results.append(result)
        
        return results
    
    async def close(self):
        if self.client:
            await self.client.aclose()
