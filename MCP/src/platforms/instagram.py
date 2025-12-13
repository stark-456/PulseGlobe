"""
Instagram 平台工具
提供 Instagram 搜索和评论获取功能
"""
from typing import Dict, Any, Optional
import logging
from ..utils.tikhub_client import get_client, TikHubAPIError

logger = logging.getLogger(__name__)


async def search_posts(
    keywords: str,
    count: int = 20,
    search_type: str = "hashtag"
) -> Dict[str, Any]:
    """
    搜索 Instagram 帖子
    
    Args:
        keywords: 搜索关键词（可以是话题标签或用户名）
        count: 返回结果数量 (默认 20)
        search_type: 搜索类型 ("hashtag": 话题标签, "user": 用户)
        
    Returns:
        包含帖子列表的字典
    """
    try:
        client = get_client()
        
        params = {
            "query": keywords,
            "count": count,
            "type": search_type
        }
        
        response = await client.get("/api/v1/instagram/search", params=params)
        
        posts = response.get("posts", [])
        
        return {
            "posts": [_normalize_post(post) for post in posts],
            "total": len(posts),
            "keywords": keywords,
            "platform": "instagram"
        }
        
    except TikHubAPIError as e:
        logger.error(f"Instagram search failed: {e}")
        return {
            "error": str(e),
            "posts": [],
            "total": 0,
            "keywords": keywords,
            "platform": "instagram"
        }


async def get_post_comments(
    post_id: str,
    max_comments: int = 100
) -> Dict[str, Any]:
    """
    获取 Instagram 帖子的评论
    
    Args:
        post_id: 帖子 ID 或短代码
        max_comments: 最大评论数量
        
    Returns:
        包含评论列表的字典
    """
    try:
        client = get_client()
        all_comments = []
        end_cursor = None
        
        while len(all_comments) < max_comments:
            params = {
                "media_id": post_id,
                "count": 50
            }
            
            if end_cursor:
                params["end_cursor"] = end_cursor
            
            response = await client.get("/api/v1/instagram/comments", params=params)
            
            comments = response.get("comments", [])
            if not comments:
                break
            
            all_comments.extend([_normalize_comment(c) for c in comments])
            
            # 检查分页
            page_info = response.get("page_info", {})
            if not page_info.get("has_next_page"):
                break
            end_cursor = page_info.get("end_cursor")
        
        return {
            "comments": all_comments[:max_comments],
            "total": len(all_comments[:max_comments]),
            "post_id": post_id,
            "platform": "instagram"
        }
        
    except TikHubAPIError as e:
        logger.error(f"Failed to get Instagram comments: {e}")
        return {
            "error": str(e),
            "comments": [],
            "total": 0,
            "post_id": post_id,
            "platform": "instagram"
        }


def _normalize_post(post: Dict[str, Any]) -> Dict[str, Any]:
    """标准化帖子数据"""
    return {
        "id": post.get("id"),
        "shortcode": post.get("shortcode"),
        "caption": post.get("caption", {}).get("text", ""),
        "author": {
            "id": post.get("owner", {}).get("id"),
            "username": post.get("owner", {}).get("username")
        },
        "created_at": post.get("taken_at_timestamp"),
        "metrics": {
            "likes": post.get("like_count", 0),
            "comments": post.get("comment_count", 0),
            "views": post.get("view_count", 0)
        },
        "media_type": post.get("media_type"),
        "url": f"https://www.instagram.com/p/{post.get('shortcode', '')}"
    }


def _normalize_comment(comment: Dict[str, Any]) -> Dict[str, Any]:
    """标准化评论数据"""
    return {
        "id": comment.get("id"),
        "text": comment.get("text", ""),
        "author": {
            "id": comment.get("owner", {}).get("id"),
            "username": comment.get("owner", {}).get("username")
        },
        "created_at": comment.get("created_at"),
        "likes": comment.get("like_count", 0)
    }
