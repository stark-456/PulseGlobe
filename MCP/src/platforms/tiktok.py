"""
TikTok 平台工具
提供 TikTok 视频搜索和评论获取功能
"""
from typing import Dict, Any, Optional
import logging
from ..utils.tikhub_client import get_client, TikHubAPIError

logger = logging.getLogger(__name__)


async def search_videos(
    keywords: str,
    count: int = 20,
    sort_type: int = 0
) -> Dict[str, Any]:
    """
    搜索 TikTok 视频
    
    Args:
        keywords: 搜索关键词
        count: 返回结果数量
        sort_type: 排序类型 (0: 综合, 1: 最新)
        
    Returns:
        包含视频列表的字典
    """
    try:
        client = get_client()
        
        params = {
            "keyword": keywords,
            "count": count,
            "sort_type": sort_type
        }
        
        response = await client.get("/api/v1/tiktok/search/video", params=params)
        
        videos = response.get("videos", [])
        
        return {
            "videos": [_normalize_video(v) for v in videos],
            "total": len(videos),
            "keywords": keywords,
            "platform": "tiktok"
        }
        
    except TikHubAPIError as e:
        logger.error(f"TikTok search failed: {e}")
        return {
            "error": str(e),
            "videos": [],
            "total": 0,
            "keywords": keywords,
            "platform": "tiktok"
        }


async def get_video_comments(
    aweme_id: str,
    max_comments: int = 100
) -> Dict[str, Any]:
    """
    获取 TikTok 视频评论（支持递归分页）
    
    Args:
        aweme_id: 视频 ID (aweme_id)
        max_comments: 最大评论数量
        
    Returns:
        包含评论列表的字典
    """
    try:
        client = get_client()
        all_comments = []
        cursor = 0
        
        while len(all_comments) < max_comments:
            params = {
                "aweme_id": aweme_id,
                "cursor": cursor,
                "count": 50
            }
            
            response = await client.get("/api/v1/tiktok/comments", params=params)
            
            comments = response.get("comments", [])
            if not comments:
                break
            
            all_comments.extend([_normalize_comment(c) for c in comments])
            
            # 检查是否有更多评论
            has_more = response.get("has_more", False)
            if not has_more:
                break
            
            cursor = response.get("cursor", cursor + len(comments))
        
        return {
            "comments": all_comments[:max_comments],
            "total": len(all_comments[:max_comments]),
            "video_id": aweme_id,
            "platform": "tiktok"
        }
        
    except TikHubAPIError as e:
        logger.error(f"Failed to get TikTok comments: {e}")
        return {
            "error": str(e),
            "comments": [],
            "total": 0,
            "video_id": aweme_id,
            "platform": "tiktok"
        }


def _normalize_video(video: Dict[str, Any]) -> Dict[str, Any]:
    """标准化视频数据"""
    return {
        "id": video.get("aweme_id"),
        "description": video.get("desc", ""),
        "author": {
            "id": video.get("author", {}).get("uid"),
            "username": video.get("author", {}).get("unique_id"),
            "nickname": video.get("author", {}).get("nickname")
        },
        "created_at": video.get("create_time"),
        "metrics": {
            "views": video.get("statistics", {}).get("play_count", 0),
            "likes": video.get("statistics", {}).get("digg_count", 0),
            "comments": video.get("statistics", {}).get("comment_count", 0),
            "shares": video.get("statistics", {}).get("share_count", 0)
        },
        "duration": video.get("video", {}).get("duration"),
        "cover": video.get("video", {}).get("cover", {}).get("url_list", [""])[0],
        "url": f"https://www.tiktok.com/@{video.get('author', {}).get('unique_id')}/video/{video.get('aweme_id')}"
    }


def _normalize_comment(comment: Dict[str, Any]) -> Dict[str, Any]:
    """标准化评论数据"""
    return {
        "id": comment.get("cid"),
        "text": comment.get("text", ""),
        "author": {
            "id": comment.get("user", {}).get("uid"),
            "username": comment.get("user", {}).get("unique_id"),
            "nickname": comment.get("user", {}).get("nickname")
        },
        "created_at": comment.get("create_time"),
        "likes": comment.get("digg_count", 0),
        "reply_count": comment.get("reply_comment_total", 0)
    }
