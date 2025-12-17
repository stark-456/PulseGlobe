"""
Instagram 平台工具
提供 Instagram 搜索和评论获取功能
"""
from typing import Dict, Any, List, Optional
import logging
from ..utils.tikhub_client import get_client, TikHubAPIError

logger = logging.getLogger(__name__)


async def search_posts(
    keywords: str,
    count: int = 20,
    feed_type: str = "top",
    pagination_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    搜索 Instagram 话题标签帖子
    
    Args:
        keywords: 话题标签关键词 (不需要#)
        count: 返回结果数量 (默认 20)
        feed_type: 排序类型 ("top": 热门, "recent": 最新)
        pagination_token: 分页令牌
        
    Returns:
        包含帖子列表的字典
    """
    try:
        client = get_client()
        
        params = {
            "keyword": keywords,
            "feed_type": feed_type,
            "pagination_token": pagination_token or ""
        }
        
        response = await client.get("/api/v1/instagram/v2/fetch_hashtag_posts", params=params)
        
        # 从 data.data.items 获取帖子列表
        data = response.get("data", {})
        inner_data = data.get("data", {})
        items = inner_data.get("items", [])[:count]
        
        return {
            "posts": [_normalize_post(post) for post in items],
            "total": len(items),
            "keywords": keywords,
            "pagination_token": data.get("pagination_token"),
            "platform": "instagram"
        }
        
    except TikHubAPIError as e:
        logger.error(f"Instagram search failed: {e}")
        return {
            "error": str(e),
            "posts": [],
            "total": 0,
            "keywords": keywords,
            "pagination_token": None,
            "platform": "instagram"
        }


async def get_post_comments(
    post_id: str,
    max_comments: int = 100,
    sort_by: str = "recent",
    pagination_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    获取 Instagram 帖子的评论
    
    Args:
        post_id: 帖子 ID 或短代码
        max_comments: 最大评论数量
        sort_by: 排序方式 ("recent": 最新, "popular": 热门)
        pagination_token: 分页令牌
        
    Returns:
        包含评论列表的字典
    """
    try:
        client = get_client()
        all_comments = []
        current_token = pagination_token
        
        while len(all_comments) < max_comments:
            params = {
                "code_or_url": post_id,
                "sort_by": sort_by
            }
            
            if current_token:
                params["pagination_token"] = current_token
            
            response = await client.get("/api/v1/instagram/v2/fetch_post_comments", params=params)
            
            # 从 data.data.items 获取评论列表
            data = response.get("data", {})
            inner_data = data.get("data", {})
            comments = inner_data.get("items", [])
            
            if not comments:
                break
            
            all_comments.extend([_normalize_comment(c) for c in comments])
            
            # 检查是否有下一页
            current_token = data.get("pagination_token")
            if not current_token:
                break
        
        return {
            "comments": all_comments[:max_comments],
            "total": len(all_comments[:max_comments]),
            "post_id": post_id,
            "has_more": current_token is not None,
            "pagination_token": current_token,
            "platform": "instagram"
        }
        
    except TikHubAPIError as e:
        logger.error(f"Failed to get Instagram comments: {e}")
        return {
            "error": str(e),
            "comments": [],
            "total": 0,
            "post_id": post_id,
            "has_more": False,
            "pagination_token": None,
            "platform": "instagram"
        }


def _normalize_post(post: Dict[str, Any]) -> Dict[str, Any]:
    """标准化帖子数据格式"""
    user = post.get("user", {})
    
    return {
        "id": post.get("id", ""),
        "code": post.get("code", ""),
        "text": post.get("caption_text", ""),
        "hashtags": post.get("caption_hashtags", []),
        "author": {
            "id": user.get("id"),
            "username": user.get("username"),
            "name": user.get("full_name"),
            "avatar": user.get("profile_pic_url"),
            "verified": user.get("is_verified", False),
            "is_private": user.get("is_private", False)
        },
        "created_at": post.get("taken_at"),
        "media_type": post.get("media_name", ""),
        "is_video": post.get("is_video", False),
        "metrics": {
            "likes": post.get("like_count", 0),
            "comments": post.get("comment_count", 0),
            "views": post.get("play_count", 0) if post.get("is_video") else None
        },
        "thumbnail": post.get("thumbnail_url"),
        "url": f"https://www.instagram.com/p/{post.get('code', '')}"
    }


def _normalize_comment(comment: Dict[str, Any]) -> Dict[str, Any]:
    """标准化评论数据格式"""
    user = comment.get("user", {})
    
    return {
        "id": comment.get("id", ""),
        "text": comment.get("text", ""),
        "hashtags": comment.get("hashtags", []),
        "author": {
            "id": user.get("id"),
            "username": user.get("username"),
            "name": user.get("full_name"),
            "avatar": user.get("profile_pic_url"),
            "verified": user.get("is_verified", False)
        },
        "created_at": comment.get("created_at_utc"),
        "metrics": {
            "likes": comment.get("comment_like_count") or comment.get("like_count", 0),
            "replies": comment.get("child_comment_count", 0)
        },
        "is_pinned": comment.get("is_pinned", False)
    }


# ============ 舆情分析专用函数 ============

def _normalize_post_for_analysis(post: Dict[str, Any]) -> Dict[str, Any]:
    """精简帖子数据用于舆情分析"""
    user = post.get("user", {})
    
    return {
        "id": post.get("id", ""),
        "code": post.get("code", ""),
        "text": post.get("caption_text", ""),
        "hashtags": post.get("caption_hashtags", []),
        "author": {
            "name": user.get("full_name", ""),
            "username": user.get("username", ""),
            "verified": user.get("is_verified", False)
        },
        "time": post.get("taken_at", ""),
        "engagement": {
            "likes": post.get("like_count", 0),
            "comments": post.get("comment_count", 0),
            "views": post.get("play_count", 0) if post.get("is_video") else None
        },
        "url": f"https://www.instagram.com/p/{post.get('code', '')}"
    }


def _normalize_comment_for_analysis(comment: Dict[str, Any]) -> Dict[str, Any]:
    """精简评论数据用于舆情分析"""
    user = comment.get("user", {})
    
    return {
        "id": comment.get("id", ""),
        "text": comment.get("text", ""),
        "author": {
            "name": user.get("full_name", ""),
            "username": user.get("username", ""),
            "verified": user.get("is_verified", False)
        },
        "time": comment.get("created_at_utc", ""),
        "engagement": {
            "likes": comment.get("comment_like_count") or comment.get("like_count", 0),
            "replies": comment.get("child_comment_count", 0)
        }
    }


async def search_with_sentiment_analysis(
    keywords: str,
    post_count: int = 10,
    comments_per_post: int = 20,
    feed_type: str = "top"
) -> Dict[str, Any]:
    """
    综合的 Instagram 舆情分析工具
    搜索话题帖子并获取每条帖子的评论，返回精简的分析数据
    
    Args:
        keywords: 话题标签关键词
        post_count: 返回的帖子数量（默认 10）
        comments_per_post: 每条帖子获取的评论数量（默认 20）
        feed_type: 排序类型 ("top": 热门, "recent": 最新)
        
    Returns:
        包含摘要和详细数据的字典，适合 LLM 分析
    """
    from datetime import datetime
    
    try:
        client = get_client()
        
        # 1. 搜索帖子（直接调用API获取原始数据）
        params = {
            "keyword": keywords,
            "feed_type": feed_type,
            "pagination_token": ""
        }
        
        response = await client.get("/api/v1/instagram/v2/fetch_hashtag_posts", params=params)
        
        # 从 data.data.items 获取原始帖子列表
        data = response.get("data", {})
        inner_data = data.get("data", {})
        raw_posts = inner_data.get("items", [])[:post_count]
        
        if not raw_posts:
            return {
                "summary": {
                    "keyword": keywords,
                    "total_posts": 0,
                    "total_comments": 0,
                    "search_time": datetime.now().isoformat(),
                    "feed_type": feed_type
                },
                "posts": []
            }
        
        # 2. 为每条帖子获取评论
        analyzed_posts = []
        total_comments = 0
        
        for raw_post in raw_posts:
            post_id = raw_post.get("id") or raw_post.get("code")
            
            # 获取评论（直接调用API获取原始数据）
            comment_params = {
                "code_or_url": str(post_id),
                "sort_by": "recent"
            }
            
            try:
                comment_response = await client.get("/api/v1/instagram/v2/fetch_post_comments", params=comment_params)
                comment_data = comment_response.get("data", {})
                comment_inner_data = comment_data.get("data", {})
                raw_comments = comment_inner_data.get("items", [])[:comments_per_post]
            except Exception as e:
                logger.warning(f"Failed to get comments for post {post_id}: {e}")
                raw_comments = []
            
            total_comments += len(raw_comments)
            
            # 精简数据
            analyzed_post = _normalize_post_for_analysis(raw_post)
            analyzed_post["comments"] = [
                _normalize_comment_for_analysis(c) for c in raw_comments
            ]
            analyzed_post["comment_count"] = len(raw_comments)
            
            analyzed_posts.append(analyzed_post)
        
        # 3. 构建返回结果
        return {
            "summary": {
                "keyword": keywords,
                "total_posts": len(analyzed_posts),
                "total_comments": total_comments,
                "search_time": datetime.now().isoformat(),
                "feed_type": feed_type
            },
            "posts": analyzed_posts
        }
        
    except Exception as e:
        logger.error(f"Instagram sentiment analysis failed: {e}")
        return {
            "error": str(e),
            "summary": {
                "keyword": keywords,
                "total_posts": 0,
                "total_comments": 0,
                "search_time": datetime.now().isoformat()
            },
            "posts": []
        }
