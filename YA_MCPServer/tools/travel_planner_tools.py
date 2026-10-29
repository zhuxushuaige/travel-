from typing import Any, Dict, List, Optional
from tools import YA_MCPServer_Tool
import os
import httpx
from math import radians, cos, sin, asin, sqrt
import re
import traceback

AMAP_KEY = os.getenv("AMAP_API_KEY") 

# 兴趣到高德 type 映射
INTEREST_TO_TYPE = {
    "博物馆": "140100", "美术馆": "140400", "展览馆": "140200",
    "历史": "110201|140100|110205", "古迹": "110201", "遗址": "110201",
    "寺庙": "110205", "教堂": "141302", "文庙": "141303", "纪念馆": "110204",
    "公园": "110101|110200", "风景": "110100|110200", "植物园": "110103",
    "动物园": "110104", "游乐场": "160300", "主题乐园": "160300", "温泉": "160700",
}

def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlng / 2)**2
    c = 2 * asin(sqrt(a))
    return c * 6371

def _map_interests_to_types(interest_list: List[str]) -> str:
    matched_types = set()
    for interest in interest_list:
        if interest in INTEREST_TO_TYPE:
            matched_types.add(INTEREST_TO_TYPE[interest])
        else:
            for keyword, code in INTEREST_TO_TYPE.items():
                if keyword in interest:
                    matched_types.add(code)
                    break
    return "|".join(matched_types)[:200]

@YA_MCPServer_Tool(
    name="get_attractions",
    title="Get Travel Attractions",
    description="根据城市和兴趣获取旅游景点推荐。",
)
async def get_attractions(city: str, interests: Optional[str], max_results: int = 50) -> Dict[str, Any]:
    if not city or not city.strip():
        return {"error": "City parameter is required."}
    if not AMAP_KEY:
        return {"error": "AMap API key is not set."}
    city = city.strip()
    try:
        async with httpx.AsyncClient() as client:
            geo_resp = await client.get(
                "https://restapi.amap.com/v3/geocode/geo",
                params={"key": AMAP_KEY, "address": city, "output": "json"},
                timeout=10.0
            )
            geo_data = geo_resp.json()
            if geo_data.get("status") != "1" or not geo_data.get("geocodes"):
                return {"error": f"City '{city}' not found."}
            adcode = geo_data["geocodes"][0]["adcode"]
            types_str = _map_interests_to_types([x.strip() for x in re.split(r'[,\s，]+', interests) if x.strip()]) if interests else "060000"
            
            response = await client.get(
                "https://restapi.amap.com/v5/place/text",
                params={"key": AMAP_KEY, "city": adcode, "types": types_str, "limit": 20, "output": "json"},
                timeout=10.0
            )
            data = response.json()
            all_pois, seen_names = [], set()
            if data.get("status") == "1":
                non_tourism = ["幼儿园", "小学", "中学", "高中", "学校", "教育", "医院", "政府", "公司", "大厦"]
                for item in data.get("pois", []):
                    name = item.get("name", "")
                    if not name or name in seen_names or any(kw in name for kw in non_tourism):
                        continue
                    location = item.get("location")
                    if location:
                        all_pois.append({"name": name, "address": item.get("address", ""), "location": location, "type": item.get("type", "")})
                        seen_names.add(name)
                    if len(all_pois) >= max_results:
                        break
            return {"city": city, "interests": interests, "attractions": all_pois[:max_results]}
    except Exception as e:
        return {"error": str(e)}

def compute_center_location(attractions: List[Dict]) -> str:
    if not attractions:
        return "0,0"
    total_lat = total_lng = count = 0
    for a in attractions:
        try:
            lng, lat = map(float, a["location"].split(","))
            total_lat += lat
            total_lng += lng
            count += 1
        except:
            continue
    return f"{total_lng/count:.6f},{total_lat/count:.6f}" if count > 0 else "0,0"

async def get_hotel(center_location: str, city: str) -> Dict[str, Any]:
    if not AMAP_KEY:
        return {"error": "AMap API key is not set."}
    
    # 过滤规则
    HOTEL_TYPECODE_PREFIX = "050"
    EXCLUDE_KEYWORDS = {
        "驿站", "快递", "代收", "便利店", "超市", "菜鸟", 
        "拼多多", "丰巢", "团购", "自提", "服务点", "社区"
    }
    
    try:
        center_lng, center_lat = map(float, center_location.split(","))
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://restapi.amap.com/v5/place/around",  #  删除末尾空格
                params={
                    "key": AMAP_KEY,
                    "keywords": "酒店",
                    "location": center_location,
                    "radius": 5000,
                    "limit": 15,
                    "output": "json",
                    "type": "100000",  #  精确搜索住宿服务
                },
                timeout=10.0
            )
            data = response.json()
            
            # 回退逻辑（同样修复 URL 和 type 参数）
            if data.get("status") != "1":
                geo_resp = await client.get(
                    "https://restapi.amap.com/v3/geocode/geo", 
                    params={"key": AMAP_KEY, "address": city, "output": "json"},
                    timeout=10.0
                )
                geo_data = geo_resp.json()
                if geo_data.get("status") == "1":
                    adcode = geo_data["geocodes"][0]["adcode"]
                    response = await client.get(
                        "https://restapi.amap.com/v5/place/text",  
                        params={
                            "key": AMAP_KEY,
                            "keywords": "酒店",
                            "city": adcode,
                            "limit": 15,
                            "output": "json",
                            "type": "100000", 
                        },
                        timeout=10.0
                    )
                    data = response.json()
            
            pois = data.get("pois", [])
            if not pois:
                return {"error": "No hotels found."}
            
            best_hotel, min_dist = None, float('inf')
            for poi in pois:
                typecode = poi.get("typecode", "")
                
                name = poi.get("name", "")
                if any(kw in name for kw in EXCLUDE_KEYWORDS):
                    continue
            
                loc = poi.get("location")
                if not loc:
                    continue
                    
                try:
                    lng, lat = map(float, loc.split(","))
                    dist = calculate_distance(center_lat, center_lng, lat, lng)
                    if dist < min_dist:
                        min_dist = dist
                        best_hotel = {
                            "name": name,
                            "address": poi.get("address", "N/A"),
                            "location": loc,
                            "rating": poi.get("biz_ext", {}).get("rating", "N/A"),
                            "distance_to_center_km": round(dist, 2)
                        }
                except Exception as e:
                    print(f"坐标解析失败: {loc}, error: {e}")
                    continue
            
            if not best_hotel:
                # 兜底：返回第一个通过过滤的酒店
                for poi in pois:
                    if poi.get("typecode", ""):
                        name = poi.get("name", "")
                        if not any(kw in name for kw in EXCLUDE_KEYWORDS):
                            loc = poi.get("location")
                            if loc:
                                return {"hotel": {
                                    "name": name,
                                    "address": poi.get("address", "N/A"),
                                    "location": loc,
                                    "rating": poi.get("biz_ext", {}).get("rating", "N/A"),
                                    "distance_to_center_km": "N/A"
                                }}
                return {"error": "No valid hotels found after filtering."}
                
            return {"hotel": best_hotel}
            
    except Exception as e:
        print(f"get_hotel error: {e}")
        return {"error": str(e)}
    
async def plan_route(origin: str, destination: str, weather_condition: str) -> Dict[str, Any]:
    if not AMAP_KEY:
        return {"error": "AMap API key is not set."}
    try:
        o_lng, o_lat = map(float, origin.split(","))
        d_lng, d_lat = map(float, destination.split(","))
        distance = calculate_distance(o_lat, o_lng, d_lat, d_lng)
        bad_weather = any(kw in weather_condition for kw in ["雨", "雪", "雹", "storm", "thunder", "rain", "snow"])
        mode = "driving" if distance < 5 else "transit" if bad_weather else "walking" if distance < 2 else "driving"
        reason = "天气不好，建议打车。" if (bad_weather and distance <5) else "天气不好，建议公共交通。" if bad_weather else "距离近，建议步行。" if distance <2 else "距离远，建议打车。"
        
        url_map = {"walking": "https://restapi.amap.com/v3/direction/walking", "driving": "https://restapi.amap.com/v3/direction/driving", "transit": "https://restapi.amap.com/v3/direction/transit/integrated"}
        response = await httpx.AsyncClient().get(url_map[mode], params={"key": AMAP_KEY, "origin": origin, "destination": destination, "output": "json"}, timeout=10.0)
        data = response.json()
        if data.get("status") != "1":
            return {"error": data.get("info", "Route failed")}
        
        duration, api_distance = 0, 0
        if mode == "transit":
            transits = data.get("route", {}).get("transits", [])
            if transits:
                duration = int(transits[0].get("duration", 0))
                api_distance = int(transits[0].get("distance", 0))
        else:
            paths = data.get("route", {}).get("paths", [])
            if paths:
                duration = int(paths[0].get("duration", 0))
                api_distance = int(paths[0].get("distance", 0))
        return {"recommended_transport": reason, "actual_mode_used": mode, "duration_seconds": duration, "distance_km": round(api_distance/1000, 2)}
    except Exception as e:
        return {"error": str(e)}

def safe_get(data, keys, default="N/A"):
    """通用容错取值函数"""
    try:
        current = data
        for key in keys:
            if isinstance(current, list):
                current = current[key] if len(current) > key else default
            elif isinstance(current, dict):
                current = current.get(key, default)
            else:
                return default
            if current == default:
                break
        return current
    except (IndexError, KeyError, TypeError):
        return default


def format_time(time_str):
    """时间格式处理：2359 → 23:59，0530 → 05:30"""
    if not isinstance(time_str, str) or not time_str.isdigit():
        return time_str
    if len(time_str) == 4:
        formatted = f"{time_str[:2]}:{time_str[2:]}"
        return f"次日{formatted}" if int(time_str) < 600 else formatted
    return time_str


async def geocode_city(city_name: str, client: httpx.AsyncClient) -> Optional[tuple]:
    """
    使用高德地理编码 API 获取城市中心坐标
    返回: (lng, lat) 或 None
    """
    try:
        params = {
            "key": AMAP_KEY,
            "address": city_name,
            "city": city_name,
            "output": "json"
        }
        resp = await client.get("https://restapi.amap.com/v3/geocode/geo", params=params, timeout=10.0)
        data = resp.json()
        
        if data.get("status") == "1" and data.get("geocodes"):
            location = data["geocodes"][0].get("location")
            if location and "," in location:
                lng, lat = location.split(",")
                return float(lng), float(lat)
        return None
    except Exception:
        return None


# ========================
# 策略映射
# ========================
STRATEGY_MAP = {
    0: "时间最短",
    1: "花费最少"
}


# ========================
# 核心工具：获取任意两城市间火车方案
# ========================
@YA_MCPServer_Tool(
    name="get_city_train_plan",
    title="Get City Train Plan",
    description="获取两个城市之间的火车出行方案，支持时间最短/花费最少两种策略",
)
async def get_city_train_plan(
    departure_city: str,
    arrival_city: str,
    date: str,
    time: Optional[str] = None,
    strategy: int = 0
) -> Dict[str, Any]:
    """
    获取任意两个城市之间的火车出行方案
    
    Args:
        departure_city: 出发城市名称（如"苏州"、"杭州"）
        arrival_city: 到达城市名称（如"南京"、"上海"）
        date: 出行日期，格式 YYYY-MM-DD
        time: 出发时间（可选），格式 HH:MM 或 HHMM
        strategy: 策略 0=时间最短，1=花费最少
    
    Returns:
        Dict: 包含火车方案列表的响应
    """
    # 1. 参数校验
    if not departure_city or not arrival_city:
        return {"error": "出发/到达城市不能为空"}
    
    departure_city = departure_city.strip()
    arrival_city = arrival_city.strip()
    
    if departure_city == arrival_city:
        return {"error": "出发城市和到达城市不能相同"}
    
    if not re.match(r"^\d{4}-\d{1,2}-\d{1,2}$", date.strip()):
        return {"error": "日期格式必须为 YYYY-MM-DD"}
    
    if strategy not in [0, 1]:
        return {"error": "策略仅支持 0(时间最短) 或 1(花费最少)"}
    
    if not AMAP_KEY:
        return {"error": "高德 API Key 未配置"}

    try:
        # 2. 异步获取城市坐标（并行请求）
        async with httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0 Chrome/120.0.0.0 Safari/537.36"},
            timeout=20.0
        ) as client:
            
            # 并行获取两个城市的坐标
            dep_coord_task = geocode_city(departure_city, client)
            arr_coord_task = geocode_city(arrival_city, client)
            
            dep_coord, arr_coord = await dep_coord_task, await arr_coord_task
            
            if not dep_coord:
                return {"error": f"无法解析出发城市 '{departure_city}' 的坐标，请检查城市名称"}
            if not arr_coord:
                return {"error": f"无法解析到达城市 '{arrival_city}' 的坐标，请检查城市名称"}
            
            dep_lnglat = f"{dep_coord[0]},{dep_coord[1]}"
            arr_lnglat = f"{arr_coord[0]},{arr_coord[1]}"

            # 3. 构造火车规划请求参数
            params = {
                "key": AMAP_KEY,
                "origin": dep_lnglat,
                "destination": arr_lnglat,
                "city": departure_city,
                "cityd": arrival_city,
                "extensions": "all",
                "strategy": strategy,
                "nightflag": 0,
                "output": "json",
                "date": date.strip()
            }
            if time and time.strip():
                # 时间格式转换：HH:MM → HHMM
                params["time"] = time.strip().replace(":", "")

            # 4. 调用高德火车规划 API
            resp = await client.get(
                "https://restapi.amap.com/v3/direction/transit/integrated",
                params=params
            )
            data = resp.json()

            if data.get("status") != "1":
                return {
                    "error": f"高德 API 错误：{data.get('info', '未知错误')}",
                    "departure_city": departure_city,
                    "arrival_city": arrival_city
                }

            # 5. 解析火车方案（严格过滤有效铁路段）
            train_plans = []
            transits = safe_get(data, ["route", "transits"], [])[:5]  # 最多返回 5 个方案

            for transit in transits:
                valid_train_segments = []
                total_duration = 0
                total_cost = 0.0

                for seg in safe_get(transit, ["segments"], []):
                    if "railway" not in seg:
                        continue  # 跳过非铁路段（如公交、步行）

                    railway = seg["railway"]
                    
                    # 关键校验：必须有车次和站点信息
                    train_no = safe_get(railway, ["trip"], "")
                    dep_station = safe_get(railway, ["departure_stop", "name"], "")
                    arr_station = safe_get(railway, ["arrival_stop", "name"], "")
                    
                    if not train_no or not dep_station or not arr_station:
                        continue  # 过滤无效接驳段

                    # 解析票价（取第一个席别）
                    spaces = safe_get(railway, ["spaces"], [])
                    price = safe_get(spaces[0], ["cost"], "0") if spaces else "0"
                    try:
                        price = float(price)
                    except (ValueError, TypeError):
                        price = 0.0

                    # 解析时长
                    seg_duration = safe_get(railway, ["time"], 0)
                    try:
                        seg_duration = int(seg_duration)
                    except (ValueError, TypeError):
                        seg_duration = 0

                    train_segment = {
                        "train_no": train_no,
                        "train_type": safe_get(railway, ["type"], "普通列车"),
                        "departure_station": dep_station,
                        "arrival_station": arr_station,
                        "departure_time": format_time(safe_get(railway, ["departure_stop", "time"], "")),
                        "arrival_time": format_time(safe_get(railway, ["arrival_stop", "time"], "")),
                        "duration_min": round(seg_duration / 60) if seg_duration > 0 else 0,
                        "price_yuan": round(price, 2)
                    }

                    valid_train_segments.append(train_segment)
                    total_duration += seg_duration
                    total_cost += price

                # 仅保留包含有效火车段的方案
                if valid_train_segments:
                    train_plans.append({
                        "total_duration_min": round(total_duration / 60),
                        "total_cost_yuan": round(total_cost, 2),
                        "train_segments": valid_train_segments
                    })

            # 6. 返回结果
            return {
                "departure_city": departure_city,
                "arrival_city": arrival_city,
                "date": date.strip(),
                "departure_time": time or "未指定",
                "strategy": STRATEGY_MAP.get(strategy, "未知"),
                "total_train_plans": len(train_plans),
                "train_plans": train_plans
            }

    except httpx.TimeoutException:
        return {"error": "请求超时，请检查网络连接或稍后重试"}
    except httpx.RequestError as e:
        return {"error": f"网络请求失败：{str(e)}"}
    except Exception as e:
        return {
            "error": f"内部错误：{str(e)}",
            "debug": traceback.format_exc()
        }

@YA_MCPServer_Tool(
    name="get_weather",
    title="Get Weather",
    description="获取城市未来N天的天气信息。",
)
async def get_weather(city: str, days: int = 3) -> Dict[str, Any]:
    if not city or not city.strip():
        return {"error": "City parameter is required."}
    if not AMAP_KEY:
        return {"error": "AMap API key is not set."}
    try:
        async with httpx.AsyncClient() as client:
            geo_resp = await client.get("https://restapi.amap.com/v3/geocode/geo", params={"key": AMAP_KEY, "address": city, "output": "json"}, timeout=10.0)
            geo_data = geo_resp.json()
            if geo_data.get("status") != "1" or not geo_data.get("geocodes"):
                return {"error": f"City '{city}' not found."}
            adcode = geo_data["geocodes"][0]["adcode"]
            weather_resp = await client.get("https://restapi.amap.com/v3/weather/weatherInfo", params={"key": AMAP_KEY, "city": adcode, "extensions": "all", "output": "json"}, timeout=10.0)
            weather_data = weather_resp.json()
            if weather_data.get("status") != "1":
                return {"error": f"AMap Weather API error: {weather_data.get('info', 'Unknown')}"}
            forecasts = []
            if "forecasts" in weather_data and weather_data["forecasts"]:
                for i, day in enumerate(weather_data["forecasts"][0].get("casts", [])[:days]):
                    forecasts.append({
                        "day": f"Day {i + 1}", "date": day.get("date", "N/A"),
                        "weather": day.get("dayweather", "N/A"),
                        "temperature": f"{day.get('nighttemp', 'N/A')}~{day.get('daytemp', 'N/A')}°C",
                        "wind_dir": day.get("daywind", "N/A"), "wind_power": day.get("daypower", "N/A")
                    })
            return {"city": city, "forecast_days": len(forecasts), "forecast": forecasts}
    except Exception as e:
        return {"error": str(e)}

@YA_MCPServer_Tool(
    name="create_travel_plan",
    title="Create Travel Plan",
    description="根据城市、兴趣创建旅行计划（先选景点，再选酒店）。",
)
async def create_travel_plan(city: str, interests: Optional[str], days: int) -> Dict[str, Any]:
    if not city or not city.strip():
        return {"error": "City is required."}
    if days < 1 or days > 7:
        return {"error": "Days must be between 1 and 7."}
    city = city.strip()

    attractions_data = await get_attractions(city, interests, max_results=50)
    if "error" in attractions_data:
        return {"error": f"获取景点失败：{attractions_data['error']}"}
    attractions = attractions_data["attractions"]
    if not attractions:
        return {"error": f"{city}未找到符合{interests or '默认'}兴趣的景点"}

    selected_attractions = attractions[:days * 2]
    center_location = compute_center_location(selected_attractions)
    hotel_data = await get_hotel(center_location, city)
    if "error" in hotel_data:
        return {"error": f"获取酒店失败：{hotel_data['error']}"}
    hotel = hotel_data["hotel"]

    weather_data = await get_weather(city, days)
    if "error" in weather_data:
        return {"error": f"获取天气失败：{weather_data['error']}"}

    itinerary = []
    remaining = selected_attractions.copy()
    for day in range(days):
        if not remaining:
            break
        day_weather = weather_data["forecast"][day]["weather"] if day < len(weather_data["forecast"]) else "晴"
        day_attractions = [remaining.pop(0)]
        
        for i, cand in enumerate(remaining):
            try:
                a1_lng, a1_lat = map(float, day_attractions[0]["location"].split(","))
                c_lng, c_lat = map(float, cand["location"].split(","))
                if calculate_distance(a1_lat, a1_lng, c_lat, c_lng) <= 8.0:
                    day_attractions.append(remaining.pop(i))
                    break
            except:
                continue

        routes = []
        current_loc = hotel["location"]
        current_name = hotel["name"]
        for a in day_attractions:
            route = await plan_route(current_loc, a["location"], day_weather)
            routes.append({
                "from": current_name, "to": a["name"],
                "transport": route.get("recommended_transport", "建议地图导航"),
                "duration_min": round(route.get("duration_seconds", 0)/60) if "error" not in route else "N/A",
                "distance_km": route.get("distance_km", "N/A") if "error" not in route else "N/A",
                "error": route.get("error") if "error" in route else ""
            })
            current_loc = a["location"]
            current_name = a["name"]

        itinerary.append({
            "day": day + 1,
            "date": weather_data["forecast"][day]["date"] if day < len(weather_data["forecast"]) else "N/A",
            "weather": day_weather,
            "attractions": [{"name": a["name"], "location": a["location"]} for a in day_attractions],
            "routes": routes
        })

    weather_summary = "; ".join([f"{day['date']}:{day['weather']}" for day in weather_data["forecast"]])
    return {
        "city": city, "total_days": days, "interests": interests,
        "hotel": hotel, "weather_overview": weather_summary,
        "itinerary": itinerary, "note": "本计划基于高德数据生成，请结合实际调整。"
    }