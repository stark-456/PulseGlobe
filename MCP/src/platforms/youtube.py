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
    order_by: str = "this_month",
    language_code: str = "en",
    country_code: str = "",
    continuation_token: str = ""
) -> Dict[str, Any]:
    """
    搜索 YouTube 视频
    
    Args:
        keywords: 搜索关键词
        count: 返回结果数量
        order_by: 排序方式 ("last_hour", "today", "this_week", "this_month", "this_year")
        language_code: 语言代码 (如 "en", "zh")
        country_code: 国家代码 (如 "US", "CN", 空字符串为默认)
        continuation_token: 分页令牌 (用于获取下一页结果)
        
    Returns:
        包含视频列表的字典
    """
    try:
        client = get_client()
        
        params = {
            "search_query": keywords,
            "language_code": language_code,
            "order_by": order_by,
            "country_code": country_code,
            "continuation_token": continuation_token
        }
        
        response = await client.get("/api/v1/youtube/web/search_video", params=params)
        
        # 从 data.videos 获取视频列表
        data = response.get("data", {})
        videos = data.get("videos", [])[:count]
        
        return {
            "videos": [_normalize_video(v) for v in videos],
            "total": len(videos),
            "keywords": keywords,
            "continuation_token": data.get("continuation_token"),
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
    max_comments: int = 100,
    sort_by: str = "top",
    lang: str = "en-US"
) -> Dict[str, Any]:
    """
    获取 YouTube 视频评论（支持递归分页）
    
    Args:
        video_id: 视频 ID
        max_comments: 最大评论数量
        sort_by: 排序方式 ("top": 热门, "new": 最新)
        lang: 语言代码 (如 "en-US", "zh-CN")
        
    Returns:
        包含评论列表的字典
    """
    try:
        client = get_client()
        all_comments = []
        next_token = ""
        
        while len(all_comments) < max_comments:
            params = {
                "video_id": video_id,
                "lang": lang,
                "sortBy": sort_by,
                "nextToken": next_token
            }
            
            response = await client.get("/api/v1/youtube/web/get_video_comments_v2", params=params)
            
            # 从 data.items 获取评论列表
            data = response.get("data", {})
            comments = data.get("items", [])
            
            if not comments:
                break
            
            all_comments.extend([_normalize_comment(c) for c in comments])
            
            # 检查是否有更多评论
            next_token = data.get("nextToken", "")
            if not next_token:
                break
        
        return {
            "comments": all_comments[:max_comments],
            "total": len(all_comments[:max_comments]),
            "video_id": video_id,
            "has_more": bool(next_token),
            "next_token": next_token,
            "platform": "youtube"
        }
        
    except TikHubAPIError as e:
        logger.error(f"Failed to get YouTube comments: {e}")
        return {
            "error": str(e),
            "comments": [],
            "total": 0,
            "video_id": video_id,
            "has_more": False,
            "platform": "youtube"
        }


def _normalize_video(video: Dict[str, Any]) -> Dict[str, Any]:
    """标准化视频数据"""
    thumbnails = video.get("thumbnails", [])
    thumbnail_url = thumbnails[-1].get("url") if thumbnails else None
    
    return {
        "id": video.get("video_id"),
        "title": video.get("title", ""),
        "description": video.get("description", ""),
        "author": {
            "id": video.get("channel_id"),
            "name": video.get("author")
        },
        "published_at": video.get("published_time"),
        "metrics": {
            "views": video.get("number_of_views", 0)
        },
        "duration": video.get("video_length"),
        "type": video.get("type"),
        "is_live": video.get("is_live_content"),
        "thumbnail": thumbnail_url,
        "url": f"https://www.youtube.com/watch?v={video.get('video_id')}"
    }


def _normalize_comment(comment: Dict[str, Any]) -> Dict[str, Any]:
    """标准化评论数据"""
    channel = comment.get("channel", {})
    avatars = channel.get("avatar", [])
    
    return {
        "id": comment.get("id"),
        "text": comment.get("contentText", ""),
        "author": {
            "id": channel.get("id"),
            "name": channel.get("name"),
            "handle": channel.get("handle"),
            "verified": channel.get("isVerified", False),
            "avatar": avatars[0].get("url") if avatars else None
        },
        "published_at": comment.get("publishedTimeText"),
        "likes": comment.get("voteCountText", "0"),
        "is_pinned": comment.get("isPinned", False),
        "is_hearted": comment.get("isHearted", False)
    }


# ============ 舆情分析专用函数 ============

def _normalize_video_for_analysis(video: Dict[str, Any]) -> Dict[str, Any]:
    """精简视频数据用于舆情分析"""
    return {
        "id": video.get("video_id"),
        "title": video.get("title", ""),
        "description": video.get("description", ""),
        "author": {
            "name": video.get("author", ""),
            "channel_id": video.get("channel_id")
        },
        "time": video.get("published_time", ""),
        "engagement": {
            "views": video.get("number_of_views", 0)
        },
        "duration": video.get("video_length"),
        "url": f"https://www.youtube.com/watch?v={video.get('video_id')}"
    }


def _normalize_comment_for_analysis(comment: Dict[str, Any]) -> Dict[str, Any]:
    """精简评论数据用于舆情分析"""
    channel = comment.get("channel", {})
    
    return {
        "id": comment.get("id"),
        "text": comment.get("contentText", ""),
        "author": {
            "name": channel.get("name", ""),
            "handle": channel.get("handle", ""),
            "verified": channel.get("isVerified", False)
        },
        "time": comment.get("publishedTimeText", ""),
        "engagement": {
            "likes": comment.get("voteCountText", "0")
        }
    }


async def search_with_sentiment_analysis(
    keywords: str,
    video_count: int = 10,
    comments_per_video: int = 20,
    order_by: str = "this_month",
    language_code: str = "en",
    country_code: str = "",
    comment_sort_by: str = "top",
    comment_lang: str = "en-US"
) -> Dict[str, Any]:
    """
    综合的 YouTube 舆情分析工具
    搜索视频并获取每个视频的评论，返回精简的分析数据
    
    Args:
        keywords: 搜索关键词
        video_count: 返回的视频数量（默认 10）
        comments_per_video: 每个视频获取的评论数量（默认 20）
        order_by: 排序方式 ("last_hour", "today", "this_week", "this_month", "this_year")
        language_code: 视频搜索语言代码 (如 "en", "zh")
        country_code: 国家代码 (如 "US", "CN")
        comment_sort_by: 评论排序 ("top": 热门, "new": 最新)
        comment_lang: 评论语言代码 (如 "en-US", "zh-CN")
        
    Returns:
        包含摘要和详细数据的字典，适合 LLM 分析
    """
    from datetime import datetime
    
    try:
        client = get_client()
        
        # 1. 搜索视频（直接调用API获取原始数据）
        params = {
            "search_query": keywords,
            "language_code": language_code,
            "order_by": order_by,
            "country_code": country_code,
            "continuation_token": ""
        }
        
        logger.info(f"YouTube search params: {params}")
        response = await client.get("/api/v1/youtube/web/search_video", params=params)
        logger.info(f"YouTube search response keys: {response.keys() if response else 'None'}")
        
        # 从 data.videos 获取原始视频列表
        data = response.get("data", {})
        logger.info(f"YouTube data keys: {data.keys() if data else 'None'}")
        
        raw_videos = data.get("videos", [])[:video_count]
        logger.info(f"YouTube found {len(raw_videos)} videos")
        
        if not raw_videos:
            # 检查是否有API错误
            detail = data.get("detail") if isinstance(data, dict) else None
            logger.warning(f"No videos found! Response data: {data}")
            return {
                "error": detail if detail else "No videos found",
                "summary": {
                    "keyword": keywords,
                    "total_videos": 0,
                    "total_comments": 0,
                    "search_time": datetime.now().isoformat(),
                    "order_by": order_by
                },
                "videos": [],
                "debug": {
                    "response_keys": list(response.keys()) if response else None,
                    "data_keys": list(data.keys()) if isinstance(data, dict) else None,
                    "data_detail": detail,
                    "data_type": str(type(data)),
                    "raw_data": data  # 显示完整的data内容以便调试
                }
            }
        
        # 2. 为每个视频获取评论
        analyzed_videos = []
        total_comments = 0
        
        for raw_video in raw_videos:
            video_id = raw_video.get("video_id")
            
            # 获取评论（直接调用API获取原始数据）
            comment_params = {
                "video_id": video_id,
                "lang": comment_lang,
                "sortBy": comment_sort_by,
                "nextToken": ""
            }
            
            try:
                comment_response = await client.get("/api/v1/youtube/web/get_video_comments_v2", params=comment_params)
                comment_data = comment_response.get("data", {})
                raw_comments = comment_data.get("items", [])[:comments_per_video]
            except Exception as e:
                logger.warning(f"Failed to get comments for video {video_id}: {e}")
                raw_comments = []
            
            total_comments += len(raw_comments)
            
            # 精简数据
            analyzed_video = _normalize_video_for_analysis(raw_video)
            analyzed_video["comments"] = [
                _normalize_comment_for_analysis(c) for c in raw_comments
            ]
            analyzed_video["comment_count"] = len(raw_comments)
            
            analyzed_videos.append(analyzed_video)
        
        # 3. 构建返回结果
        return {
            "summary": {
                "keyword": keywords,
                "total_videos": len(analyzed_videos),
                "total_comments": total_comments,
                "search_time": datetime.now().isoformat(),
                "order_by": order_by
            },
            "videos": analyzed_videos
        }
        
    except TikHubAPIError as e:
        logger.error(f"YouTube sentiment analysis failed: {e}")
        return {
            "error": str(e),
            "summary": {
                "keyword": keywords,
                "total_videos": 0,
                "total_comments": 0,
                "search_time": datetime.now().isoformat()
            },
            "videos": []
        }
    except Exception as e:
        logger.error(f"YouTube sentiment analysis failed: {e}")
        return {
            "error": str(e),
            "summary": {
                "keyword": keywords,
                "total_videos": 0,
                "total_comments": 0,
                "search_time": datetime.now().isoformat()
            },
            "videos": []
        }
