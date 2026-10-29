# 适配新版 mcp 包的导入路径（核心修复点）
from mcp.server import Server  # 修正：从 mcp.server 导入 Server
from mcp.stdio import stdio_server
import asyncio
import os
from dotenv import load_dotenv

# 1. 加载 .env 文件（确保高德API密钥生效）
load_dotenv()

# 2. 导入旅行规划工具（核心，确保路径正确）
try:
    from tools.travel_planner_tools import (
        create_travel_plan,
        get_attractions,
        get_weather
    )
except ImportError as e:
    print(f"【错误】导入旅行工具失败：{e}")
    print(f"【排查】请确认 tools/travel_planner_tools.py 存在于 {os.getcwd()}/tools/ 目录")
    exit(1)

# 3. 检查高德API密钥
AMAP_API_KEY = os.getenv("AMAP_API_KEY")
if not AMAP_API_KEY:
    print("【警告】未配置高德API密钥！请在 .env 文件中添加 AMAP_API_KEY=你的密钥")
    print("【注意】服务器仍会启动，但调用工具时会失败")

async def main():
    """启动 MCP 标准 IO 服务器（适配新版 mcp 包）"""
    # 初始化 MCP 服务器（类名仍为 Server，仅导入路径变）
    server = Server(name="travel-mcp-server")
    
    # 注册旅行规划工具
    server.register_tool(create_travel_plan)
    server.register_tool(get_attractions)
    server.register_tool(get_weather)
    
    # 打印启动信息
    print("="*60)
    print("✅ MCP 标准 IO 服务器启动成功！")
    print(f"📌 服务器名称：travel-mcp-server")
    print(f"🔧 已注册工具：create_travel_plan / get_attractions / get_weather")
    print(f"💡 提示：按 CTRL+C 停止服务器")
    print("="*60)
    
    # 启动标准 IO 服务器
    await stdio_server(server)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 MCP 服务器已手动停止")
    except Exception as e:
        print(f"【错误】服务器启动失败：{e}")
        # 额外提示：若仍报错，检查 mcp 版本
        import mcp
        print(f"【当前 mcp 版本】：{mcp.__version__}")
