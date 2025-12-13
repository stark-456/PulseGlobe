# OpenMCP 使用指南 - PulseGlobe MCP

## 连接配置说明

您的 MCP 服务器使用 **STDIO 模式**（标准输入输出模式）。

### 在 OpenMCP 中使用

1. **自动连接**（推荐）
   - 打开 VSCode
   - 点击右上角的 OpenMCP 图标
   - OpenMCP 会自动读取 `.openmcp/connection.json` 配置
   - 自动启动并连接 MCP 服务器

2. **手动连接**
   - 点击左侧 OpenMCP 侧边栏
   - 在「MCP 连接（工作区）」中查看连接状态
   - 如果需要，点击 + 添加新连接

### 配置说明

```json
{
  "name": "PulseGlobe Social Search",  // 服务器名称
  "type": "stdio",                      // STDIO 模式
  "command": "uv",                      // 使用 UV 启动
  "args": ["run", "python", "-m", "src.server"],
  "cwd": "d:\\develop\\PulseGlobe\\MCP"
}
```

### 可用工具列表

连接成功后，您可以在 OpenMCP 中看到 8 个工具：

#### Twitter
- `twitter_search_posts` - 搜索推文
- `twitter_get_post_comments` - 获取评论

#### Instagram
- `instagram_search_posts` - 搜索帖子
- `instagram_get_post_comments` - 获取评论

#### YouTube
- `youtube_search_videos` - 搜索视频
- `youtube_get_video_comments` - 获取评论

#### TikTok
- `tiktok_search_videos` - 搜索视频
- `tiktok_get_video_comments` - 获取评论

### 测试示例

连接成功后，您可以测试：

```
请搜索 Twitter 上关于 "AI" 的推文
```

OpenMCP 会自动调用 `twitter_search_posts` 工具。

---

## 故障排查

### 连接失败
- 检查 `.env` 文件中的 API Token 是否配置
- 确保 UV 已安装：`uv --version`
- 查看 OpenMCP 控制台日志

### 中文乱码
- 已在 `start_uv.bat` 中添加 UTF-8 编码设置
- 如果仍有问题，检查 VSCode 终端编码设置

### 工具调用错误
- 检查 TikHub API 端点是否正确
- 查看服务器日志确认错误信息
