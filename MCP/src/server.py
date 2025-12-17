"""
PulseGlobe MCP 服务器
社交平台舆情搜索服务主入口
"""
import logging
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

from .platforms import twitter, youtube, tiktok
from .platforms import instagram

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
        # Twitter 舆情分析工具
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
        
        # Instagram 舆情分析工具
        Tool(
            name="instagram_sentiment_search",
            description="Instagram舆情分析综合工具。自动搜索话题帖子并获取评论，返回精简的、适合大模型分析的数据结构。",
            inputSchema={
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "string",
                        "description": "话题标签关键词"
                    },
                    "post_count": {
                        "type": "integer",
                        "description": "返回的帖子数量(默认10)",
                        "default": 10
                    },
                    "comments_per_post": {
                        "type": "integer",
                        "description": "每条帖子获取的评论数量(默认20)",
                        "default": 20
                    },
                    "feed_type": {
                        "type": "string",
                        "description": "排序类型: top(热门) 或 recent(最新)",
                        "enum": ["top", "recent"],
                        "default": "top"
                    }
                },
                "required": ["keywords"]
            }
        ),
        
        # YouTube 舆情分析工具
        Tool(
            name="youtube_sentiment_search",
            description="YouTube舆情分析综合工具。自动搜索视频并获取评论，返回精简的、适合大模型分析的数据结构。",
            inputSchema={
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "string",
                        "description": "搜索关键词"
                    },
                    "video_count": {
                        "type": "integer",
                        "description": "返回的视频数量(默认10)",
                        "default": 10
                    },
                    "comments_per_video": {
                        "type": "integer",
                        "description": "每个视频获取的评论数量(默认20)",
                        "default": 20
                    },
                    "order_by": {
                        "type": "string",
                        "description": "视频排序: last_hour, today, this_week, this_month, this_year",
                        "enum": ["last_hour", "today", "this_week", "this_month", "this_year"],
                        "default": "this_month"
                    },
                    "language_code": {
                        "type": "string",
                        "description": "视频搜索语言代码(如 en, zh)",
                        "default": "en"
                    },
                    "country_code": {
                        "type": "string",
                        "description": "国家代码(如 US, CN)",
                        "default": ""
                    },
                    "comment_sort_by": {
                        "type": "string",
                        "description": "评论排序: top(热门) 或 new(最新)",
                        "enum": ["top", "new"],
                        "default": "top"
                    },
                    "comment_lang": {
                        "type": "string",
                        "description": "评论语言代码(如 en-US, zh-CN)",
                        "default": "en-US"
                    }
                },
                "required": ["keywords"]
            }
        ),
        
        # TikTok 舆情分析工具
        Tool(
            name="tiktok_sentiment_search",
            description="TikTok舆情分析综合工具。自动搜索视频并获取评论，返回精简的、适合大模型分析的数据结构。",
            inputSchema={
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "string",
                        "description": "搜索关键词"
                    },
                    "video_count": {
                        "type": "integer",
                        "description": "返回的视频数量(默认10)",
                        "default": 10
                    },
                    "comments_per_video": {
                        "type": "integer",
                        "description": "每个视频获取的评论数量(默认20)",
                        "default": 20
                    },
                    "sort_type": {
                        "type": "integer",
                        "description": "视频排序: 0(综合) 或 1(最新)",
                        "enum": [0, 1],
                        "default": 0
                    },
                    "publish_time": {
                        "type": "integer",
                        "description": "发布时间筛选: 0(全部), 1(一天内), 7(一周内), 30(一个月内)",
                        "enum": [0, 1, 7, 30, 90, 180],
                        "default": 0
                    },
                    "region": {
                        "type": "string",
                        "description": "区域代码(如 US, CN)",
                        "default": "US"
                    }
                },
                "required": ["keywords"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """调用工具"""
    try:
        logger.info(f"Calling tool: {name} with arguments: {arguments}")
        
        # 舆情分析工具
        if name == "twitter_sentiment_search":
            result = await twitter.search_with_sentiment_analysis(**arguments)
        elif name == "instagram_sentiment_search":
            result = await instagram.search_with_sentiment_analysis(**arguments)
        elif name == "youtube_sentiment_search":
            result = await youtube.search_with_sentiment_analysis(**arguments)
        elif name == "tiktok_sentiment_search":
            result = await tiktok.search_with_sentiment_analysis(**arguments)
        
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
