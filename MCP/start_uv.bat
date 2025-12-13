@echo off
chcp 65001 >nul
REM PulseGlobe MCP 服务器启动脚本 (使用 UV)

echo ========================================
echo PulseGlobe Social Search MCP Server
echo Powered by UV
echo ========================================
echo.

REM 检查 .env 文件是否存在
if not exist ".env" (
    echo [ERROR] .env 文件不存在！
    echo 请先复制 .env.example 为 .env 并配置您的 API Token
    echo.
    echo 命令: copy .env.example .env
    echo.
    pause
    exit /b 1
)

REM 检查 uv 是否安装
where uv >nul 2>nul
if errorlevel 1 (
    echo [ERROR] UV 未安装！
    echo 请先安装 UV: https://github.com/astral-sh/uv
    echo.
    echo 安装命令: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    echo.
    pause
    exit /b 1
)

echo [INFO] 使用 UV 启动 MCP 服务器...
echo.

REM 使用 uv 运行服务器（自动管理依赖）
uv run python -m src.server

echo.
echo [INFO] MCP 服务器已停止
pause
