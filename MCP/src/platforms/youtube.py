"""
YouTube 平台工具
提供 YouTube 视频搜索和评论获取功能
"""
from typing import Dict, Any, Optional
import logging
from ..utils.tikhub_client import get_client, TikHubAPIError

logger = logging.getLogger(__name__)


async def search_videos(
    keywords: str,
    count: int = 20,
    order_by: str = "relevance",
    language_code: str = "zh-CN"
) -> Dict[str, Any]:
    """
    搜索 YouTube 视频
    
    Args:
        keywords: 搜索关键词
        count: 返回结果数量
        order_by: 排序方式 ("relevance": 相关性, "date": 日期, "viewCount": 观看次数)
        language_code: 语言代码
        
    Returns:
        包含视频列表的字典
    """
    try:
        client = get_client()
        
        params = {
            "search_query": keywords,
            "count": count,
            "order_by": order_by,
            "language_code": language_code
        }
        
        response = await client.get("/api/v1/youtube/search", params=params)
        
        videos = response.get("videos", [])
        
        return {
            "videos": [_normalize_video(v) for v in videos],
            "total": len(videos),
            "keywords": keywords,
            "platform": "youtube"
        }
        
    except TikHubAPIError as e:
        logger.error(f"YouTube search failed: {e}")
        return {
            "error": str(e),
            "videos": [],
            "total": 0,
            "keywords": keywords,
            "platform": "youtube"
        }


async def get_video_comments(
    video_id: str,
    max_comments: int = 100
) -> Dict[str, Any]:
    """
    获取 YouTube 视频评论（支持递归分页）
    
    Args:
        video_id: 视频 ID
        max_comments: 最大评论数量
        
    Returns:
        包含评论列表的字典
    """
    try:
        client = get_client()
        all_comments = []
        continuation_token = None
        
        while len(all_comments) < max_comments:
            params = {
                "video_id": video_id,
                "count": 50
            }
            
            if continuation_token:
                params["continuation"] = continuation_token
            
            response = await client.get("/api/v1/youtube/comments", params=params)
            
            comments = response.get("comments", [])
            if not comments:
                break
            
            all_comments.extend([_normalize_comment(c) for c in comments])
            
            # 检查是否有更多评论
            continuation_token = response.get("continuation_token")
            if not continuation_token:
                break
        
        return {
            "comments": all_comments[:max_comments],
            "total": len(all_comments[:max_comments]),
            "video_id": video_id,
            "has_more": continuation_token is not None,
            "platform": "youtube"
        }
        
    except TikHubAPIError as e:
        logger.error(f"Failed to get YouTube comments: {e}")
        return {
            "error": str(e),
            "comments": [],
            "total": 0,
            "video_id": video_id,
            "platform": "youtube"
        }


def _normalize_video(video: Dict[str, Any]) -> Dict[str, Any]:
    """标准化视频数据"""
    return {
        "id": video.get("videoId"),
        "title": video.get("title", {}).get("text", ""),
        "description": video.get("description", {}).get("text", ""),
        "author": {
            "id": video.get("channelId"),
            "name": video.get("channelName")
        },
        "published_at": video.get("publishedTimeText"),
        "metrics": {
            "views": video.get("viewCount"),
            "likes": video.get("likeCount"),
            "comments": video.get("commentCount")
        },
        "duration": video.get("lengthText"),
        "thumbnail": video.get("thumbnail", {}).get("thumbnails", [{}])[0].get("url"),
        "url": f"https://www.youtube.com/watch?v={video.get('videoId')}"
    }


def _normalize_comment(comment: Dict[str, Any]) -> Dict[str, Any]:
    """标准化评论数据"""
    return {
        "id": comment.get("commentId"),
        "text": comment.get("contentText", ""),
        "author": {
            "id": comment.get("authorChannelId"),
            "name": comment.get("authorText")
        },
        "published_at": comment.get("publishedTimeText"),
        "likes": comment.get("likeCount", 0),
        "reply_count": comment.get("replyCount", 0)
    }
