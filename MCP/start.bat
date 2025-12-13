@echo off
REM PulseGlobe MCP 服务器启动脚本

echo ========================================
echo PulseGlobe Social Search MCP Server
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

REM 检查虚拟环境
if exist "venv\Scripts\activate.bat" (
    echo [INFO] 激活虚拟环境...
    call venv\Scripts\activate.bat
) else (
    echo [WARNING] 未找到虚拟环境，使用全局 Python
)

REM 检查依赖
echo [INFO] 检查依赖...
python -c "import mcp" 2>nul
if errorlevel 1 (
    echo [ERROR] 缺少依赖包！请先安装依赖：
    echo.
    echo 命令: pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo [INFO] 启动 MCP 服务器...
echo.

REM 启动服务器
python -m src.server

echo.
echo [INFO] MCP 服务器已停止
pause
