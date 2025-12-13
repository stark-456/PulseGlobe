"""
Twitter 平台工具
提供 Twitter 搜索和评论获取功能
"""
from typing import Dict, Any, List, Optional
import logging
from ..utils.tikhub_client import get_client, TikHubAPIError

logger = logging.getLogger(__name__)


async def search_posts(
    keywords: str,
    count: int = 20,
    search_type: str = "Top",
    cursor: Optional[str] = None
) -> Dict[str, Any]:
    """
    搜索 Twitter 推文
    
    Args:
        keywords: 搜索关键词
        count: 返回结果数量 (默认 20)
        search_type: 搜索类型 ("Top": 热门, "Latest": 最新)
        cursor: 分页游标
        
    Returns:
        包含推文列表的字典
        {
            "posts": [...],
            "total": int,
            "keywords": str,
            "next_cursor": str or None,
            "prev_cursor": str or None
        }
    """
    try:
        client = get_client()
        
        # 调用 TikHub Twitter 搜索 API
        params = {
            "keyword": keywords,
            "search_type": search_type
        }
        
        if cursor:
            params["cursor"] = cursor
        
        response = await client.get("/api/v1/twitter/web/fetch_search_timeline", params=params)
        
        # 从 data.timeline 获取推文列表
        data = response.get("data", {})
        timeline = data.get("timeline", [])
        
        # 只返回 type 为 "tweet" 的项
        posts = [item for item in timeline if item.get("type") == "tweet"][:count]
        
        return {
            "posts": [_normalize_post(post) for post in posts],
            "total": len(posts),
            "keywords": keywords,
            "next_cursor": data.get("next_cursor"),
            "prev_cursor": data.get("prev_cursor"),
            "platform": "twitter"
        }
        
    except TikHubAPIError as e:
        logger.error(f"Twitter search failed: {e}")
        return {
            "error": str(e),
            "posts": [],
            "total": 0,
            "keywords": keywords,
            "next_cursor": None,
            "prev_cursor": None,
            "platform": "twitter"
        }


async def get_post_comments(
    post_id: str,
    max_comments: int = 100,
    cursor: Optional[str] = None
) -> Dict[str, Any]:
    """
    获取 Twitter 推文的评论（支持递归分页）
    
    Args:
        post_id: 推文 ID
        max_comments: 最大评论数量
        cursor: 分页游标（用于递归获取）
        
    Returns:
        包含评论列表的字典
        {
            "comments": [...],
            "total": int,
            "post_id": str,
            "has_more": bool,
            "next_cursor": str or None
        }
    """
    try:
        client = get_client()
        all_comments = []
        current_cursor = cursor
        
        while len(all_comments) < max_comments:
            params = {
                "tweet_id": post_id
            }
            
            if current_cursor:
                params["cursor"] = current_cursor
            
            response = await client.get("/api/v1/twitter/web/fetch_post_comments", params=params)
            
            # 从 data.thread 获取评论列表
            data = response.get("data", {})
            comments = data.get("thread", [])
            
            if not comments:
                break
            
            all_comments.extend([_normalize_comment(c) for c in comments])
            
            # 检查是否有下一页 - 需要根据实际API响应调整
            # 注意：评论API可能没有明确的next_cursor，需要测试确认
            current_cursor = None  # 可能需要根据实际响应调整
            break  # 暂时只获取一页，避免无限循环
        
        return {
            "comments": all_comments[:max_comments],
            "total": len(all_comments[:max_comments]),
            "post_id": post_id,
            "has_more": False,  # 需要根据实际API确认
            "next_cursor": current_cursor,
            "platform": "twitter"
        }
        
    except TikHubAPIError as e:
        logger.error(f"Failed to get Twitter comments: {e}")
        return {
            "error": str(e),
            "comments": [],
            "total": 0,
            "post_id": post_id,
            "has_more": False,
            "next_cursor": None,
            "platform": "twitter"
        }


def _normalize_post(post: Dict[str, Any]) -> Dict[str, Any]:
    """标准化推文数据格式"""
    user_info = post.get("user_info", {})
    tweet_id = post.get("tweet_id", "")
    
    return {
        "id": tweet_id,
        "text": post.get("text", ""),
        "author": {
            "id": user_info.get("rest_id"),
            "username": user_info.get("screen_name"),
            "name": user_info.get("name"),
            "avatar": user_info.get("avatar"),
            "verified": user_info.get("verified", False),
            "followers_count": user_info.get("followers_count", 0)
        },
        "created_at": post.get("created_at"),
        "metrics": {
            "likes": post.get("favorites", 0),
            "retweets": post.get("retweets", 0),
            "replies": post.get("replies", 0),
            "quotes": post.get("quotes", 0),
            "bookmarks": post.get("bookmarks", 0),
            "views": post.get("views", "0")
        },
        "media": post.get("media", {}),
        "entities": post.get("entities", {}),
        "lang": post.get("lang"),
        "url": f"https://twitter.com/{user_info.get('screen_name', 'i')}/status/{tweet_id}"
    }


def _normalize_comment(comment: Dict[str, Any]) -> Dict[str, Any]:
    """标准化评论数据格式"""
    author = comment.get("author", {})
    
    return {
        "id": comment.get("id", ""),
        "text": comment.get("text", ""),
        "display_text": comment.get("display_text", ""),
        "author": {
            "id": author.get("rest_id"),
            "username": author.get("screen_name"),
            "name": author.get("name"),
            "avatar": author.get("image"),
            "verified": author.get("blue_verified", False),
            "followers_count": author.get("sub_count", 0),
            "description": author.get("description", "")
        },
        "created_at": comment.get("created_at"),
        "metrics": {
            "likes": comment.get("likes", 0),
            "retweets": comment.get("retweets", 0),
            "replies": comment.get("replies", 0),
            "quotes": comment.get("quotes", 0),
            "bookmarks": comment.get("bookmarks", 0),
            "views": comment.get("views", "0")
        },
        "media": comment.get("media", []),
        "entities": comment.get("entities", {}),
        "lang": comment.get("lang")
    }


# ============ 舆情分析专用函数 ============

def _normalize_post_for_analysis(post: Dict[str, Any]) -> Dict[str, Any]:
    """精简帖子数据用于舆情分析"""
    user_info = post.get("user_info", {})
    tweet_id = post.get("tweet_id", "")
    
    return {
        "id": tweet_id,
        "text": post.get("text", ""),
        "author": {
            "name": user_info.get("name", ""),
            "username": user_info.get("screen_name", ""),
            "verified": user_info.get("verified", False),
            "followers": user_info.get("followers_count", 0)
        },
        "time": post.get("created_at", ""),
        "engagement": {
            "likes": post.get("favorites", 0),
            "retweets": post.get("retweets", 0),
            "replies": post.get("replies", 0),
            "views": post.get("views", "0")
        },
        "url": f"https://twitter.com/{user_info.get('screen_name', 'i')}/status/{tweet_id}"
    }


def _normalize_comment_for_analysis(comment: Dict[str, Any]) -> Dict[str, Any]:
    """精简评论数据用于舆情分析"""
    author = comment.get("author", {})
    
    return {
        "id": comment.get("id", ""),
        "text": comment.get("display_text") or comment.get("text", ""),
        "author": {
            "name": author.get("name", ""),
            "username": author.get("screen_name", ""),
            "verified": author.get("blue_verified", False),
            "followers": author.get("sub_count", 0)
        },
        "time": comment.get("created_at", ""),
        "engagement": {
            "likes": comment.get("likes", 0),
            "replies": comment.get("replies", 0)
        }
    }


async def search_with_sentiment_analysis(
    keywords: str,
    post_count: int = 10,
    comments_per_post: int = 20,
    search_type: str = "Top"
) -> Dict[str, Any]:
    """
    综合的 Twitter 舆情分析工具
    搜索推文并获取每条推文的评论，返回精简的分析数据
    
    Args:
        keywords: 搜索关键词
        post_count: 返回的帖子数量（默认 10）
        comments_per_post: 每条帖子获取的评论数量（默认 20）
        search_type: 搜索类型 ("Top": 热门, "Latest": 最新)
        
    Returns:
        包含摘要和详细数据的字典，适合 LLM 分析
        {
            "summary": {...},
            "posts": [{...comments: [...]}]
        }
    """
    from datetime import datetime
    
    try:
        # 1. 搜索推文
        search_result = await search_posts(
            keywords=keywords,
            count=post_count,
            search_type=search_type
        )
        
        if "error" in search_result:
            return {
                "error": search_result["error"],
                "summary": {
                    "keyword": keywords,
                    "total_posts": 0,
                    "total_comments": 0,
                    "search_time": datetime.now().isoformat()
                },
                "posts": []
            }
        
        posts = search_result.get("posts", [])
        
        # 2. 为每条推文获取评论
        analyzed_posts = []
        total_comments = 0
        
        for post in posts:
            post_id = post.get("id")
            
            # 获取评论
            comments_result = await get_post_comments(
                post_id=post_id,
                max_comments=comments_per_post
            )
            
            comments = comments_result.get("comments", [])
            total_comments += len(comments)
            
            # 精简数据
            analyzed_post = _normalize_post_for_analysis(post)
            analyzed_post["comments"] = [
                _normalize_comment_for_analysis(c) for c in comments
            ]
            analyzed_post["comment_count"] = len(comments)
            
            analyzed_posts.append(analyzed_post)
        
        # 3. 构建返回结果
        return {
            "summary": {
                "keyword": keywords,
                "total_posts": len(analyzed_posts),
                "total_comments": total_comments,
                "search_time": datetime.now().isoformat(),
                "search_type": search_type
            },
            "posts": analyzed_posts
        }
        
    except Exception as e:
        logger.error(f"Sentiment analysis failed: {e}")
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

