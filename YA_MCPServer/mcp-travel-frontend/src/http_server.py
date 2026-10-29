import sys
from pathlib import Path
from dotenv import load_dotenv
import os

# 加载 .env
load_dotenv()
AMAP_WEB_KEY = os.getenv("AMAP_WEB_KEY", "").strip()

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(project_root))

# 导入模块（必须在路径设置后）
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn

from tools.travel_planner_tools import (
    create_travel_plan,
    get_weather,
    get_city_train_plan  
)

# 创建 FastAPI 实例
app = FastAPI(title="Travel Planner API")

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 根路径：动态注入 Key
@app.get("/")
def serve_frontend():
    html_path = Path(__file__).parent / "static" / "index.html"
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()
    html = html.replace("{{AMAP_WEB_KEY}}", AMAP_WEB_KEY)
    return HTMLResponse(html)

# ========================
# API 路由
# ========================

@app.post("/create_travel_plan")
async def plan_trip(request: dict):
    try:
        city = request.get("city", "").strip()
        days = int(request.get("days", 3))
        interests = request.get("interests", "").strip()
        if not city:
            return {"error": "City is required"}
        result = await create_travel_plan(city=city, days=days, interests=interests)
        return result
    except Exception as e:
        return {"error": str(e)}

@app.post("/get_weather")
async def weather(request: dict):
    try:
        city = request.get("city", "").strip()
        days = int(request.get("days", 3))
        if days < 1:
            days = 1
        result = await get_weather(city=city, days=days)
        return result
    except Exception as e:
        return {"error": str(e)}

@app.post("/get_city_train_plan")
async def city_train_plan(request: dict):
    """
    查询两个城市之间的火车方案
    请求体:
    {
        "departure_city": "上海",
        "arrival_city": "杭州",
        "date": "2024-03-15",
        "time": "09:00",  // 可选
        "strategy": 0     // 0=时间最短，1=花费最少
    }
    """
    try:
        departure_city = request.get("departure_city", "").strip()
        arrival_city = request.get("arrival_city", "").strip()
        date = request.get("date", "").strip()
        time = request.get("time")  # 可选，保持原样传递
        strategy = int(request.get("strategy", 0))
        
        # 调用工具函数
        result = await get_city_train_plan(
            departure_city=departure_city,
            arrival_city=arrival_city,
            date=date,
            time=time,
            strategy=strategy
        )
        return result
    except ValueError:
        return {"error": "strategy 参数必须是整数 (0 或 1)"}
    except Exception as e:
        return {"error": f"内部错误：{str(e)}"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8081)