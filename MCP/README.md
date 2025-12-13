# PulseGlobe MCP - 社交平台舆情搜索服务

基于 [TikHub API](https://tikhub.io) 的 MCP (Model Context Protocol) 服务器，为 AI 智能体提供强大的社交平台舆情搜索能力。

## 🚀 功能特性

支持以下社交平台的关键词搜索和评论获取：

- **Twitter (X)** - 推文搜索 + 评论获取
- **Instagram** - 帖子搜索 + 评论获取  
- **YouTube** - 视频搜索 + 评论获取
- **TikTok** - 视频搜索 + 评论获取

### 核心能力

✅ 基于关键词的智能搜索  
✅ 递归分页获取完整评论数据  
✅ 统一的数据格式  
✅ 自动重试和错误处理  
✅ 速率限制保护

## 📋 前置要求

- Python 3.10 或更高版本
- TikHub API Token（从 [tikhub.io](https://tikhub.io) 注册获取）

## 🛠️ 安装

### 方式 1: 使用 UV（推荐）

[UV](https://github.com/astral-sh/uv) 是一个极快的 Python 包管理器，可以自动管理依赖和虚拟环境。

#### 1. 安装 UV

```powershell
# Windows PowerShell
irm https://astral.sh/uv/install.ps1 | iex
```

#### 2. 进入项目目录

```bash
cd d:\develop\PulseGlobe\MCP
```

#### 3. 配置环境变量（见下方步骤 4）

UV 会自动处理依赖安装，无需手动创建虚拟环境！

---

### 方式 2: 使用传统 pip

#### 1. 进入项目目录

```bash
cd d:\develop\PulseGlobe\MCP
```

#### 2. 创建虚拟环境

```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

#### 3. 安装依赖

```bash
pip install -r requirements.txt
```

---

### 4. 配置环境变量（两种方式都需要）

复制 `.env.example` 为 `.env`：

```bash
copy .env.example .env
```

编辑 `.env` 文件，填入您的 TikHub API Token：

```env
TIKHUB_API_TOKEN=your_api_token_here
TIKHUB_API_BASE_URL=https://api.tikhub.io
```

> **注意**：如果您在中国大陆，请使用 `https://api.tikhub.cn` 作为 API 基础 URL。

## 🎯 使用方法

### 作为 MCP 服务器运行

#### 使用 UV（推荐）

**方式 A: 直接运行启动脚本**
```bash
start_uv.bat
```

**方式 B: 配置 Claude Desktop**

编辑 Claude Desktop 配置文件（通常在 `%APPDATA%\Claude\claude_desktop_config.json`）：

```json
{
  "mcpServers": {
    "pulseglobe": {
      "command": "uv",
      "args": [
        "run",
        "python",
        "-m",
        "src.server"
      ],
      "cwd": "d:\\develop\\PulseGlobe\\MCP"
    }
  }
}
```

#### 使用传统 Python

配置 Claude Desktop：

```json
{
  "mcpServers": {
    "pulseglobe": {
      "command": "python",
      "args": [
        "-m",
        "src.server"
      ],
      "cwd": "d:\\develop\\PulseGlobe\\MCP",
      "env": {
        "PATH": "d:\\develop\\PulseGlobe\\MCP\\venv\\Scripts;${PATH}"
      }
    }
  }
}
```

重启 Claude Desktop 后，MCP 服务器将自动启动。

### MCP 工具列表

#### Twitter 工具

1. **twitter_search_posts** - 搜索推文
   - `keywords`: 搜索关键词
   - `count`: 结果数量（默认 20）
   - `search_type`: "top" 或 "latest"

2. **twitter_get_post_comments** - 获取推文评论
   - `post_id`: 推文 ID
   - `max_comments`: 最大评论数（默认 100）

#### Instagram 工具

3. **instagram_search_posts** - 搜索帖子
   - `keywords`: 关键词（话题标签或用户名）
   - `count`: 结果数量
   - `search_type`: "hashtag" 或 "user"

4. **instagram_get_post_comments** - 获取帖子评论
   - `post_id`: 帖子 ID
   - `max_comments`: 最大评论数

#### YouTube 工具

5. **youtube_search_videos** - 搜索视频
   - `keywords`: 搜索关键词
   - `count`: 结果数量
   - `order_by`: "relevance", "date" 或 "viewCount"

6. **youtube_get_video_comments** - 获取视频评论
   - `video_id`: 视频 ID
   - `max_comments`: 最大评论数

#### TikTok 工具

7. **tiktok_search_videos** - 搜索视频
   - `keywords`: 搜索关键词
   - `count`: 结果数量
   - `sort_type`: 0(综合) 或 1(最新)

8. **tiktok_get_video_comments** - 获取视频评论
   - `aweme_id`: 视频 ID
   - `max_comments`: 最大评论数

## 📁 项目结构

```
PulseGlobe/MCP/
├── src/
│   ├── server.py              # MCP 服务器主入口
│   ├── config.py              # 配置管理
│   ├── platforms/             # 平台工具
│   │   ├── twitter.py
│   │   ├── instagram.py
│   │   ├── youtube.py
│   │   └── tiktok.py
│   └── utils/
│       └── tikhub_client.py   # TikHub API 客户端
├── requirements.txt           # Python 依赖
├── pyproject.toml            # 项目元数据
├── .env.example              # 环境变量模板
└── README.md                 # 本文档
```

## 🔧 开发

### 运行测试

```bash
pytest tests/ -v
```

### 日志配置

服务器默认使用 INFO 级别日志。可以在 `src/server.py` 中调整日志级别。

## 📝 示例

在 Claude Desktop 或其他 MCP 客户端中，您可以这样使用：

```
请使用 twitter_search_posts 工具搜索关键词 "AI" 的推文
```

```
帮我获取这个 YouTube 视频的前 50 条评论（视频 ID: dQw4w9WgXcQ）
```

## ⚠️ 注意事项

1. **API 速率限制**：TikHub API 有速率限制，请合理使用
2. **数据准确性**：返回的数据取决于 TikHub API 的可用性和准确性
3. **错误处理**：如遇到错误，检查 API Token 是否有效，以及网络连接是否正常

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 🔗 相关链接

- [TikHub 官网](https://tikhub.io)
- [TikHub API 文档](https://docs.tikhub.io)
- [MCP 协议](https://modelcontextprotocol.io)
