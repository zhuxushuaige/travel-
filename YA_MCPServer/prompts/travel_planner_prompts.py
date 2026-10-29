from typing import Any, Dict, List, Optional, Union
from prompts import YA_MCPServer_Prompt

@YA_MCPServer_Prompt(
    name="plan_trip",
    title="Travel Planning Assistant",
    description="根据用户的需求生成旅行计划。",
)
async def plan_trip(
    city: str,
    days: int,
    interests: Optional[Union[str, List[str]]] = None
) -> str:  # ← 关键：返回类型改为 str
    """
    生成个性化旅行计划指令（纯文本）。
    """
    if interests is None:
        interests = []
    elif isinstance(interests, str):
        if "," in interests:
            interests = [item.strip() for item in interests.split(",") if item.strip()]
        else:
            interests = [interests.strip()] if interests.strip() else []

    instruction = (
        f"请为用户规划一个前往 {city} 的 {days} 天旅行计划。\n"
        f"兴趣偏好: {', '.join(interests) if interests else '不限'}。\n"
        "要求：\n"
        "1. 查询每日天气；\n"
        "2. 推荐每天的景点（结合兴趣）；\n"
        "3. 根据景点间距离和当天天气，规划交通方式与路线；\n"
        "4. 若天数>1，推荐住宿选项。"
    )
    return instruction  # ← 直接返回字符串