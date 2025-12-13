"""
PulseGlobe MCP 服务器
社交平台舆情搜索服务主入口
"""
import logging
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

from .platforms import twitter, instagram, youtube, tiktok

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建 MCP 服务器实例
app = Server("pulseglobe-social-search")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """列出所有可用的工具"""
    return [
        # Twitter 工具
        Tool(
            name="twitter_search_posts",
            description="搜索 Twitter 推文。使用关键词搜索推文内容，返回匹配的推文列表。",
            inputSchema={
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "string",
                        "description": "搜索关键词"
                    },
                    "count": {
                        "type": "integer",
                        "description": "返回结果数量（默认 20，最大 100）",
                        "default": 20
                    },
                    "search_type": {
                        "type": "string",
                        "description": "搜索类型：top(热门) 或 latest(最新)",
                        "enum": ["top", "latest"],
                        "default": "top"
                    }
                },
                "required": ["keywords"]
            }
        ),
        Tool(
            name="twitter_get_post_comments",
            description="获取 Twitter 推文的评论。支持递归分页获取所有评论。",
            inputSchema={
                "type": "object",
                "properties": {
                    "post_id": {
                        "type": "string",
                        "description": "推文 ID"
                    },
                    "max_comments": {
                        "type": "integer",
                        "description": "最大评论数量（默认 100）",
                        "default": 100
                    }
                },
                "required": ["post_id"]
            }
        ),
        Tool(
            name="twitter_sentiment_search",
            description="Twitter舆情分析综合工具。自动搜索推文并获取每条推文的评论，返回精简的、适合大模型分析的数据结构。适用于舆情分析、情感分析等场景。",
            inputSchema={
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "string",
                        "description": "搜索关键词"
                    },
                    "post_count": {
                        "type": "integer",
                        "description": "返回的帖子数量（默认 10）",
                        "default": 10
                    },
                    "comments_per_post": {
                        "type": "integer",
                        "description": "每条帖子获取的评论数量（默认 20）",
                        "default": 20
                    },
                    "search_type": {
                        "type": "string",
                        "description": "搜索类型：Top(热门) 或 Latest(最新)",
                        "enum": ["Top", "Latest"],
                        "default": "Top"
                    }
                },
                "required": ["keywords"]
            }
        ),
        
        # Instagram 工具
        Tool(
            name="instagram_search_posts",
            description="搜索 Instagram 帖子。可以根据话题标签(hashtag)或用户名搜索。",
            inputSchema={
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "string",
                        "description": "搜索关键词（话题标签或用户名）"
                    },
                    "count": {
                        "type": "integer",
                        "description": "返回结果数量（默认 20）",
                        "default": 20
                    },
                    "search_type": {
                        "type": "string",
                        "description": "搜索类型：hashtag(话题标签) 或 user(用户)",
                        "enum": ["hashtag", "user"],
                        "default": "hashtag"
                    }
                },
                "required": ["keywords"]
            }
        ),
        Tool(
            name="instagram_get_post_comments",
            description="获取 Instagram 帖子的评论。支持递归分页获取。",
            inputSchema={
                "type": "object",
                "properties": {
                    "post_id": {
                        "type": "string",
                        "description": "帖子 ID 或短代码"
                    },
                    "max_comments": {
                        "type": "integer",
                        "description": "最大评论数量（默认 100）",
                        "default": 100
                    }
                },
                "required": ["post_id"]
            }
        ),
        
        # YouTube 工具
        Tool(
            name="youtube_search_videos",
            description="搜索 YouTube 视频。使用关键词搜索视频内容。",
            inputSchema={
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "string",
                        "description": "搜索关键词"
                    },
                    "count": {
                        "type": "integer",
                        "description": "返回结果数量（默认 20）",
                        "default": 20
                    },
                    "order_by": {
                        "type": "string",
                        "description": "排序方式：relevance(相关性)、date(日期)、viewCount(观看次数)",
                        "enum": ["relevance", "date", "viewCount"],
                        "default": "relevance"
                    },
                    "language_code": {
                        "type": "string",
                        "description": "语言代码（如 zh-CN, en-US）",
                        "default": "zh-CN"
                    }
                },
                "required": ["keywords"]
            }
        ),
        Tool(
            name="youtube_get_video_comments",
            description="获取 YouTube 视频的评论。支持递归分页获取所有评论。",
            inputSchema={
                "type": "object",
                "properties": {
                    "video_id": {
                        "type": "string",
                        "description": "YouTube 视频 ID"
                    },
                    "max_comments": {
                        "type": "integer",
                        "description": "最大评论数量（默认 100）",
                        "default": 100
                    }
                },
                "required": ["video_id"]
            }
        ),
        
        # TikTok 工具
        Tool(
            name="tiktok_search_videos",
            description="搜索 TikTok 视频。使用关键词搜索视频内容。",
            inputSchema={
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "string",
                        "description": "搜索关键词"
                    },
                    "count": {
                        "type": "integer",
                        "description": "返回结果数量（默认 20）",
                        "default": 20
                    },
                    "sort_type": {
                        "type": "integer",
                        "description": "排序类型：0(综合) 或 1(最新)",
                        "enum": [0, 1],
                        "default": 0
                    }
                },
                "required": ["keywords"]
            }
        ),
        Tool(
            name="tiktok_get_video_comments",
            description="获取 TikTok 视频的评论。支持递归分页获取所有评论。",
            inputSchema={
                "type": "object",
                "properties": {
                    "aweme_id": {
                        "type": "string",
                        "description": "TikTok 视频 ID (aweme_id)"
                    },
                    "max_comments": {
                        "type": "integer",
                        "description": "最大评论数量（默认 100）",
                        "default": 100
                    }
                },
                "required": ["aweme_id"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """调用工具"""
    try:
        logger.info(f"Calling tool: {name} with arguments: {arguments}")
        
        # Twitter 工具
        if name == "twitter_search_posts":
            result = await twitter.search_posts(**arguments)
        elif name == "twitter_get_post_comments":
            result = await twitter.get_post_comments(**arguments)
        elif name == "twitter_sentiment_search":
            result = await twitter.search_with_sentiment_analysis(**arguments)
        
        # Instagram 工具
        elif name == "instagram_search_posts":
            result = await instagram.search_posts(**arguments)
        elif name == "instagram_get_post_comments":
            result = await instagram.get_post_comments(**arguments)
        
        # YouTube 工具
        elif name == "youtube_search_videos":
            result = await youtube.search_videos(**arguments)
        elif name == "youtube_get_video_comments":
            result = await youtube.get_video_comments(**arguments)
        
        # TikTok 工具
        elif name == "tiktok_search_videos":
            result = await tiktok.search_videos(**arguments)
        elif name == "tiktok_get_video_comments":
            result = await tiktok.get_video_comments(**arguments)
        
        else:
            raise ValueError(f"Unknown tool: {name}")
        
        # 将结果转换为字符串返回
        import json
        result_str = json.dumps(result, ensure_ascii=False, indent=2)
        
        return [TextContent(type="text", text=result_str)]
        
    except Exception as e:
        logger.error(f"Error calling tool {name}: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]


async def main():
    """主函数 - 启动 MCP 服务器"""
    logger.info("Starting PulseGlobe Social Search MCP Server...")
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
