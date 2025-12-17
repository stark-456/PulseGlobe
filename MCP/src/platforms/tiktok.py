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
    sort_type: int = 0,
    publish_time: int = 0,
    region: str = "US",
    offset: int = 0
) -> Dict[str, Any]:
    """
    搜索 TikTok 视频
    
    Args:
        keywords: 搜索关键词
        count: 返回结果数量
        sort_type: 排序类型 (0: 综合, 1: 最新)
        publish_time: 发布时间筛选 (0: 全部, 1: 一天内, 7: 一周内, 30: 一个月内, 90: 三个月内, 180: 半年内)
        region: 区域代码 (如 "US", "CN")
        offset: 分页偏移量
        
    Returns:
        包含视频列表的字典
    """
    try:
        client = get_client()
        
        params = {
            "keyword": keywords,
            "offset": str(offset),
            "count": str(count),
            "sort_type": str(sort_type),
            "publish_time": str(publish_time),
            "region": region.upper()  # 确保大写
        }
        
        response = await client.get("/api/v1/tiktok/app/v3/fetch_video_search_result", params=params)
        
        # 从 data.search_item_list 获取视频列表
        data = response.get("data", {})
        search_items = data.get("search_item_list", [])
        
        # 提取 aweme_info
        videos = []
        for item in search_items:
            aweme_info = item.get("aweme_info", {})
            if aweme_info:
                videos.append(_normalize_video(aweme_info))
        
        return {
            "videos": videos[:count],
            "total": len(videos),
            "keywords": keywords,
            "cursor": data.get("cursor"),
            "has_more": data.get("has_more", 0) == 1,
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
    max_comments: int = 100,
    cursor: int = 0
) -> Dict[str, Any]:
    """
    获取 TikTok 视频评论（支持递归分页）
    
    Args:
        aweme_id: 视频 ID (aweme_id)
        max_comments: 最大评论数量
        cursor: 分页游标
        
    Returns:
        包含评论列表的字典
    """
    try:
        client = get_client()
        all_comments = []
        current_cursor = cursor
        
        while len(all_comments) < max_comments:
            params = {
                "aweme_id": aweme_id,
                "cursor": str(current_cursor),
                "count": "50"
            }
            
            # 使用 TikHub V3 评论API
            response = await client.get("/api/v1/tiktok/app/v3/fetch_video_comments", params=params)
            
            # 从 data.comments 获取评论列表
            data = response.get("data", {})
            comments = data.get("comments", [])
            
            if not comments:
                break
            
            all_comments.extend([_normalize_comment(c) for c in comments])
            
            # 检查是否有更多评论
            has_more = data.get("has_more", 0) == 1
            if not has_more:
                break
            
            current_cursor = data.get("cursor", current_cursor + len(comments))
        
        return {
            "comments": all_comments[:max_comments],
            "total": len(all_comments[:max_comments]),
            "video_id": aweme_id,
            "has_more": len(all_comments) >= max_comments,
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


def _normalize_video(aweme_info: Dict[str, Any]) -> Dict[str, Any]:
    """标准化视频数据"""
    author = aweme_info.get("author", {})
    statistics = aweme_info.get("statistics", {})
    video = aweme_info.get("video", {})
    
    # 获取封面图
    cover = video.get("cover", {})
    cover_url = ""
    if cover:
        url_list = cover.get("url_list", [])
        if url_list:
            cover_url = url_list[0]
    
    return {
        "id": aweme_info.get("aweme_id"),
        "description": aweme_info.get("desc", ""),
        "author": {
            "id": author.get("uid"),
            "username": author.get("unique_id"),
            "nickname": author.get("nickname"),
            "sec_uid": author.get("sec_uid"),
            "follower_count": author.get("follower_count", 0)
        },
        "created_at": aweme_info.get("create_time"),
        "metrics": {
            "views": statistics.get("play_count", 0),
            "likes": statistics.get("digg_count", 0),
            "comments": statistics.get("comment_count", 0),
            "shares": statistics.get("share_count", 0),
            "collects": statistics.get("collect_count", 0)
        },
        "duration": video.get("duration"),
        "cover": cover_url,
        "share_url": aweme_info.get("share_url", ""),
        "url": f"https://www.tiktok.com/@{author.get('unique_id', '')}/video/{aweme_info.get('aweme_id')}"
    }


def _normalize_comment(comment: Dict[str, Any]) -> Dict[str, Any]:
    """标准化评论数据"""
    user = comment.get("user", {})
    
    return {
        "id": comment.get("cid"),
        "text": comment.get("text", ""),
        "author": {
            "id": user.get("uid"),
            "username": user.get("unique_id"),
            "nickname": user.get("nickname"),
            "sec_uid": user.get("sec_uid")
        },
        "created_at": comment.get("create_time"),
        "likes": comment.get("digg_count", 0),
        "reply_count": comment.get("reply_comment_total", 0),
        "is_author_digged": comment.get("is_author_digged", False)
    }


# ============ 舆情分析专用函数 ============

def _normalize_video_for_analysis(aweme_info: Dict[str, Any]) -> Dict[str, Any]:
    """精简视频数据用于舆情分析 - 保留重要文本内容"""
    author = aweme_info.get("author", {})
    statistics = aweme_info.get("statistics", {})
    
    # 提取话题标签
    hashtags = []
    cha_list = aweme_info.get("cha_list", []) or []
    for cha in cha_list:
        if cha.get("cha_name"):
            hashtags.append(cha.get("cha_name"))
    
    # 提取text_extra中的标签
    text_extra = aweme_info.get("text_extra", []) or []
    for extra in text_extra:
        if extra.get("hashtag_name"):
            hashtags.append(extra.get("hashtag_name"))
    
    # 提取文字贴纸内容
    text_stickers = []
    interaction_stickers = aweme_info.get("interaction_stickers", []) or []
    for sticker in interaction_stickers:
        if sticker.get("text_info"):
            text_stickers.append(sticker.get("text_info"))
    
    # 搜索描述（通常包含更完整的文本）
    search_desc = aweme_info.get("search_desc", "")
    
    return {
        "id": aweme_info.get("aweme_id"),
        "description": aweme_info.get("desc", ""),  # 视频描述/标题
        "search_desc": search_desc,  # 搜索描述（可能更完整）
        "text_stickers": text_stickers,  # 视频中的文字贴纸
        "hashtags": list(set(hashtags)),  # 去重后的话题标签
        "author": {
            "name": author.get("nickname", ""),
            "username": author.get("unique_id", "")
        },
        "time": aweme_info.get("create_time"),
        "engagement": {
            "views": statistics.get("play_count", 0),
            "likes": statistics.get("digg_count", 0),
            "comments": statistics.get("comment_count", 0),
            "shares": statistics.get("share_count", 0)
        },
        "url": f"https://www.tiktok.com/@{author.get('unique_id', '')}/video/{aweme_info.get('aweme_id')}"
    }


def _normalize_comment_for_analysis(comment: Dict[str, Any]) -> Dict[str, Any]:
    """精简评论数据用于舆情分析 - 保留完整评论内容"""
    user = comment.get("user", {})
    
    return {
        "id": comment.get("cid"),
        "text": comment.get("text", ""),  # 评论文本
        "author": {
            "name": user.get("nickname", ""),
            "username": user.get("unique_id", "")
        },
        "time": comment.get("create_time"),
        "engagement": {
            "likes": comment.get("digg_count", 0),
            "replies": comment.get("reply_comment_total", 0)
        },
        "is_author_liked": comment.get("is_author_digged", False)  # 作者是否点赞
    }


async def search_with_sentiment_analysis(
    keywords: str,
    video_count: int = 10,
    comments_per_video: int = 20,
    sort_type: int = 0,
    publish_time: int = 0,
    region: str = "US"
) -> Dict[str, Any]:
    """
    综合的 TikTok 舆情分析工具
    搜索视频并获取每个视频的评论，返回精简的分析数据
    
    Args:
        keywords: 搜索关键词
        video_count: 返回的视频数量（默认 10）
        comments_per_video: 每个视频获取的评论数量（默认 20）
        sort_type: 排序 (0: 综合, 1: 最新)
        publish_time: 发布时间筛选 (0: 全部, 1: 一天内, 7: 一周内, 30: 一个月内)
        region: 区域代码 (如 "US", "CN")
        
    Returns:
        包含摘要和详细数据的字典，适合 LLM 分析
    """
    from datetime import datetime
    
    try:
        client = get_client()
        
        # 1. 搜索视频（直接调用API获取原始数据）
        params = {
            "keyword": keywords,
            "offset": "0",
            "count": str(video_count),
            "sort_type": str(sort_type),
            "publish_time": str(publish_time),
            "region": region.upper()  # 确保大写
        }
        
        logger.info(f"TikTok search params: {params}")
        response = await client.get("/api/v1/tiktok/app/v3/fetch_video_search_result", params=params)
        
        # 从 data.search_item_list 获取原始视频列表
        data = response.get("data", {})
        search_items = data.get("search_item_list", [])[:video_count]
        
        if not search_items:
            detail = data.get("detail") if isinstance(data, dict) else None
            logger.warning(f"No videos found! Response data: {data}")
            return {
                "error": detail if detail else "No videos found",
                "summary": {
                    "keyword": keywords,
                    "total_videos": 0,
                    "total_comments": 0,
                    "search_time": datetime.now().isoformat(),
                    "sort_type": sort_type
                },
                "videos": []
            }
        
        # 2. 为每个视频获取评论
        analyzed_videos = []
        total_comments = 0
        
        for item in search_items:
            aweme_info = item.get("aweme_info", {})
            if not aweme_info:
                continue
                
            aweme_id = aweme_info.get("aweme_id")
            
            # 获取评论（直接调用API获取原始数据）
            comment_params = {
                "aweme_id": aweme_id,
                "cursor": "0",
                "count": str(comments_per_video)
            }
            
            try:
                comment_response = await client.get("/api/v1/tiktok/app/v3/fetch_video_comments", params=comment_params)
                comment_data = comment_response.get("data", {})
                raw_comments = comment_data.get("comments", [])[:comments_per_video]
            except Exception as e:
                logger.warning(f"Failed to get comments for video {aweme_id}: {e}")
                raw_comments = []
            
            total_comments += len(raw_comments)
            
            # 精简数据
            analyzed_video = _normalize_video_for_analysis(aweme_info)
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
                "sort_type": sort_type,
                "region": region
            },
            "videos": analyzed_videos
        }
        
    except TikHubAPIError as e:
        logger.error(f"TikTok sentiment analysis failed: {e}")
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
        logger.error(f"TikTok sentiment analysis failed: {e}")
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
