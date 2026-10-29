from resources import YA_MCPServer_Resource
from typing import Any, Dict, List
import os
import yaml
from pathlib import Path

SAFE_RESOURCE_ROOT = Path("safe_resources").resolve()
os.makedirs(SAFE_RESOURCE_ROOT, exist_ok=True)

@YA_MCPServer_Resource(
    "travel://config",  # 资源 URI
    name="travel_config",  # 资源 ID
    title="Travel Config",  # 资源标题
    description="返回配置文件内容",  # 资源描述
)
def get_config() -> Dict[str, Any]:
    config_path = SAFE_RESOURCE_ROOT / "config.yaml"
    try:
        with open(SAFE_RESOURCE_ROOT / "config.yaml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            return config
    except FileNotFoundError:
        default_config = {
            "weather_api": "QWeather",
            "places_api": "AMap",
            "transit_api": "AMap",
            "supported_cities": ["Beijing", "Shanghai", "Guangzhou", "Shenzhen"],
            "max_interests": 3,
            "default_days": 3
        }
        return default_config
    except Exception as e:
        return {"error": str(e)}


@YA_MCPServer_Resource(
    "file:///{path}",  # 资源模板 URI
    name="server_files",  # 资源 ID
    title="Server Files",  # 资源标题
    description="返回文件内容",  # 资源描述
)
def server_files(path: str) -> Any:
    safe_path = (SAFE_RESOURCE_ROOT / path).resolve()
    if not str(safe_path).startswith(str(SAFE_RESOURCE_ROOT)):
        return {"error": "Access denied"}
    try:
        with open(safe_path, "r", encoding="utf-8") as f:
            content = f.read()
            return {"content": content}
    except FileNotFoundError:
        return {"error": "File not found"}
    except Exception as e:
        return {"error": str(e)}