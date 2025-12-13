# PulseGlobe MCP 工具 API 文档

本文档详细说明了所有可用的 MCP 工具及其参数。

## Twitter 工具

### twitter_search_posts

搜索 Twitter 推文。

**参数：**

| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| keywords | string | ✅ | - | 搜索关键词 |
| count | integer | ❌ | 20 | 返回结果数量（最大 100） |
| search_type | string | ❌ | "top" | 搜索类型："top"(热门) 或 "latest"(最新) |

**返回示例：**

```json
{
  "posts": [
    {
      "id": "1234567890",
      "text": "推文内容...",
      "author": {
        "id": "123456",
        "username": "example_user",
        "name": "示例用户"
      },
      "created_at": "2024-01-01T00:00:00Z",
      "metrics": {
        "likes": 100,
        "retweets": 50,
        "replies": 20
      },
      "url": "https://twitter.com/i/status/1234567890"
    }
  ],
  "total": 1,
  "keywords": "AI",
  "platform": "twitter"
}
```

---

### twitter_get_post_comments

获取 Twitter 推文的评论，支持递归分页。

**参数：**

| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| post_id | string | ✅ | - | 推文 ID |
| max_comments | integer | ❌ | 100 | 最大评论数量 |

**返回示例：**

```json
{
  "comments": [
    {
      "id": "9876543210",
      "text": "评论内容...",
      "author": {
        "id": "654321",
        "username": "commenter",
        "name": "评论者"
      },
      "created_at": "2024-01-01T01:00:00Z",
      "likes": 10
    }
  ],
  "total": 1,
  "post_id": "1234567890",
  "has_more": false,
  "next_cursor": null,
  "platform": "twitter"
}
```

---

### twitter_sentiment_search

**🆕 推荐使用** - Twitter 舆情分析综合工具。

自动搜索推文并获取每条推文的评论，返回精简的、适合大模型分析的数据结构。适用于舆情分析、情感分析等场景。

**参数：**

| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| keywords | string | ✅ | - | 搜索关键词 |
| post_count | integer | ❌ | 10 | 返回的帖子数量 |
| comments_per_post | integer | ❌ | 20 | 每条帖子获取的评论数量 |
| search_type | string | ❌ | "Top" | 搜索类型："Top"(热门) 或 "Latest"(最新) |

**返回示例：**

```json
{
  "summary": {
    "keyword": "AI",
    "total_posts": 10,
    "total_comments": 150,
    "search_time": "2025-12-12T17:55:17+08:00",
    "search_type": "Top"
  },
  "posts": [
    {
      "id": "1234567890",
      "text": "推文内容...",
      "author": {
        "name": "示例用户",
        "username": "example_user",
        "verified": true,
        "followers": 10000
      },
      "time": "Fri Dec 12 09:46:51 +0000 2025",
      "engagement": {
        "likes": 100,
        "retweets": 50,
        "replies": 30,
        "views": "5000"
      },
      "url": "https://twitter.com/example_user/status/1234567890",
      "comment_count": 15,
      "comments": [
        {
          "id": "9876543210",
          "text": "评论内容...",
          "author": {
            "name": "评论者",
            "username": "commenter",
            "verified": false,
            "followers": 500
          },
          "time": "Fri Dec 12 10:00:00 +0000 2025",
          "engagement": {
            "likes": 10,
            "replies": 2
          }
        }
      ]
    }
  ]
}
```

**数据精简说明：**

相比于 `twitter_search_posts` 和 `twitter_get_post_comments`，此工具返回的数据已经过精简，只包含舆情分析所需的核心字段：
- 文本内容
- 作者信息（名称、用户名、认证状态、粉丝数）
- 时间信息
- 互动指标（点赞、转发、回复、浏览量）

移除了 `media`、`entities`、`lang` 等与舆情分析关联度较低的字段。



## Instagram 工具

### instagram_search_posts

搜索 Instagram 帖子。

**参数：**

| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| keywords | string | ✅ | - | 搜索关键词（话题标签或用户名） |
| count | integer | ❌ | 20 | 返回结果数量 |
| search_type | string | ❌ | "hashtag" | 搜索类型："hashtag" 或 "user" |

**返回示例：**

```json
{
  "posts": [
    {
      "id": "1234567890_123",
      "shortcode": "ABC123xyz",
      "caption": "帖子内容...",
      "author": {
        "id": "123456",
        "username": "example_user"
      },
      "created_at": 1640995200,
      "metrics": {
        "likes": 500,
        "comments": 50,
        "views": 1000
      },
      "media_type": "PHOTO",
      "url": "https://www.instagram.com/p/ABC123xyz"
    }
  ],
  "total": 1,
  "keywords": "ai",
  "platform": "instagram"
}
```

---

### instagram_get_post_comments

获取 Instagram 帖子的评论。

**参数：**

| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| post_id | string | ✅ | - | 帖子 ID 或短代码 |
| max_comments | integer | ❌ | 100 | 最大评论数量 |

---

## YouTube 工具

### youtube_search_videos

搜索 YouTube 视频。

**参数：**

| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| keywords | string | ✅ | - | 搜索关键词 |
| count | integer | ❌ | 20 | 返回结果数量 |
| order_by | string | ❌ | "relevance" | 排序方式："relevance", "date", "viewCount" |
| language_code | string | ❌ | "zh-CN" | 语言代码（如 "en-US"） |

**返回示例：**

```json
{
  "videos": [
    {
      "id": "dQw4w9WgXcQ",
      "title": "视频标题",
      "description": "视频描述...",
      "author": {
        "id": "UCxxxxxx",
        "name": "频道名称"
      },
      "published_at": "2 years ago",
      "metrics": {
        "views": 1000000,
        "likes": 50000,
        "comments": 5000
      },
      "duration": "3:42",
      "thumbnail": "https://i.ytimg.com/...",
      "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    }
  ],
  "total": 1,
  "keywords": "AI tutorial",
  "platform": "youtube"
}
```

---

### youtube_get_video_comments

获取 YouTube 视频评论，支持递归分页。

**参数：**

| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| video_id | string | ✅ | - | YouTube 视频 ID |
| max_comments | integer | ❌ | 100 | 最大评论数量 |

---

## TikTok 工具

### tiktok_search_videos

搜索 TikTok 视频。

**参数：**

| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| keywords | string | ✅ | - | 搜索关键词 |
| count | integer | ❌ | 20 | 返回结果数量 |
| sort_type | integer | ❌ | 0 | 排序类型：0(综合) 或 1(最新) |

**返回示例：**

```json
{
  "videos": [
    {
      "id": "7123456789012345678",
      "description": "视频描述 #hashtag",
      "author": {
        "id": "123456",
        "username": "example_user",
        "nickname": "示例用户"
      },
      "created_at": 1640995200,
      "metrics": {
        "views": 100000,
        "likes": 5000,
        "comments": 500,
        "shares": 100
      },
      "duration": 15000,
      "cover": "https://...",
      "url": "https://www.tiktok.com/@example_user/video/7123456789012345678"
    }
  ],
  "total": 1,
  "keywords": "ai",
  "platform": "tiktok"
}
```

---

### tiktok_get_video_comments

获取 TikTok 视频评论，支持递归分页。

**参数：**

| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| aweme_id | string | ✅ | - | TikTok 视频 ID (aweme_id) |
| max_comments | integer | ❌ | 100 | 最大评论数量 |

---

## 错误处理

所有工具在出错时会返回包含 `error` 字段的响应：

```json
{
  "error": "错误信息描述",
  "posts": [],  // 或 videos/comments
  "total": 0,
  "platform": "twitter"
}
```

常见错误：
- `Authentication failed` - API Token 无效或过期
- `Rate limit exceeded` - 超出速率限制，请稍后重试
- `HTTP 4xx/5xx` - API 请求失败

## 注意事项

1. **速率限制**：请遵守 TikHub API 的速率限制
2. **数据时效性**：社交平台数据实时变化,返回结果可能不是最新
3. **ID 格式**：不同平台的 ID 格式不同，请确保使用正确的 ID 格式
4. **评论分页**：`max_comments` 是建议值，实际返回数量可能略有不同
5. **舆情分析推荐**：对于舆情分析场景，推荐使用 `twitter_sentiment_search` 等综合工具，可获得精简的、适合 LLM 分析的数据结构

