# YA MCPServer 旅行规划

基于 Model Context Protocol（MCP）和高德地图 API 的旅行规划项目。项目提供天气、景点、跨城市火车方案和行程规划工具，也提供一个通过 HTTP 使用这些能力的网页。

## 功能

- 根据城市与兴趣查询景点。
- 查询城市天气预报。
- 根据景点位置推荐酒店，并结合天气和距离生成行程及交通建议。
- 查询两个城市之间包含火车段的出行方案。
- 提供 MCP 提示词和资源，方便兼容 MCP 的客户端使用。

旅行数据依赖高德接口，结果受接口权限、数据覆盖范围和实时情况影响，请结合实际情况核实。

## 环境准备

- Python 3.10 或更新版本。
- 可访问高德地图 API 的网络，以及具有相应接口权限的高德 Web 服务 Key。
- 如需使用 React 开发界面，另需 Node.js 和 npm。

在项目根目录创建并激活虚拟环境（以下为 Windows PowerShell 示例）：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m pip install python-dotenv fastapi uvicorn
```

`python-dotenv`、`fastapi` 和 `uvicorn` 被代码直接使用，但未全部列入项目的直接依赖，因此上面单独安装。

## 配置密钥

在项目根目录的 `.env` 文件中配置：

```dotenv
AMAP_API_KEY=你的高德Web服务Key
AMAP_WEB_KEY=你的高德JavaScript API Key
```

`AMAP_API_KEY` 用于服务端的地理编码、天气、地点和路线查询；`AMAP_WEB_KEY` 用于网页加载高德地图。请根据高德平台要求配置应用、接口权限及安全设置。不要将真实密钥提交到公开仓库。当前旅行工具使用高德天气接口，不需要为该功能额外配置其他天气服务密钥。

## 启动网页和 HTTP API

在项目根目录运行：

```powershell
python mcp-travel-frontend/src/http_server.py
```

浏览器打开 [http://127.0.0.1:8081/](http://127.0.0.1:8081/)。FastAPI 还提供 [接口文档](http://127.0.0.1:8081/docs)。这个入口直接调用 Python 旅行工具，无需先启动 MCP Server。网页中的 API 地址固定为本机 `127.0.0.1:8081`，因此上述地址适合在运行服务的电脑上访问。

主要 HTTP 接口：

| 方法和路径 | 用途 | 请求字段 |
| --- | --- | --- |
| `POST /create_travel_plan` | 生成旅行计划 | `city`、`days`、`interests` |
| `POST /get_weather` | 查询天气 | `city`、`days` |
| `POST /get_city_train_plan` | 查询火车出行方案 | `departure_city`、`arrival_city`、`date`，可选 `time`、`strategy` |

例如，在另一个 PowerShell 窗口中调用：

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8081/create_travel_plan `
  -ContentType 'application/json; charset=utf-8' `
  -Body ([System.Text.Encoding]::UTF8.GetBytes('{"city":"杭州","days":2,"interests":"博物馆,公园"}'))
```

行程规划的 `days` 支持 1–7 天；天气预报实际返回的天数取决于高德接口。火车方案中的 `strategy` 支持 `0`（时间最短）或 `1`（花费最少）。接口遇到业务错误时通常返回包含 `error` 字段的 JSON。

## 启动 MCP Server

项目根目录的 `config.yaml` 控制服务名称和传输方式。默认使用 SSE，监听 `127.0.0.1:8080`：

```powershell
python server.py
```

SSE 入口为 `http://127.0.0.1:8080/`，消息路径为 `/messages/`。可在 `config.yaml` 的 `transport` 中调整 `type`、`host` 和 `port`；SSE 模式下 `HOST`、`PORT` 环境变量也可覆盖监听地址和端口。设置 `type: stdio` 可使用标准输入输出传输。请从项目根目录启动，以便正确加载配置、环境变量和资源目录。

注册的 MCP 工具：

| 工具 | 参数 | 说明 |
| --- | --- | --- |
| `get_attractions` | `city`, `interests`, `max_results` | 查询景点，`max_results` 默认 50 |
| `get_weather` | `city`, `days` | 查询天气，`days` 默认 3 |
| `get_city_train_plan` | `departure_city`, `arrival_city`, `date`, 可选 `time`, `strategy` | 查询跨城市火车方案 |
| `create_travel_plan` | `city`, `interests`, `days` | 生成包含酒店、天气、景点及路线的计划 |

提示词 `plan_trip` 生成旅行规划指令；资源 `travel://config` 提供旅行配置，`file:///{path}` 读取 `safe_resources` 下的文件。资源配置文件为 `safe_resources/config.yaml`，与服务启动配置 `config.yaml` 不同；前者不存在时使用代码中的默认值。

## React 开发界面（可选）

项目还包含独立的 React + Vite 界面。先按上文启动 HTTP API，再打开另一个终端：

```powershell
cd mcp-travel-frontend
npm install
npm run dev
```

按终端提示访问 Vite 地址。生产构建可运行 `npm run build`。React 界面与 FastAPI 根路径提供的静态网页是不同入口；静态网页不需要安装 Node.js。

## 项目结构

```text
YA_MCPServer/
├── server.py                    # MCP 服务入口
├── config.yaml                  # MCP 服务配置
├── tools/                       # 旅行工具及自动注册
├── prompts/                     # MCP 提示词
├── resources/                   # MCP 资源
├── safe_resources/              # 资源文件目录
├── modules/YA_Common/           # 公共配置、日志等模块
├── mcp-travel-frontend/
│   ├── src/http_server.py       # FastAPI 和静态网页入口
│   ├── src/static/index.html    # 静态网页
│   └── src/App.jsx              # React 界面
└── pyproject.toml               # Python 项目及依赖
```

## 常见问题

- **提示 `AMap API key is not set`**：检查项目根目录 `.env` 中的 `AMAP_API_KEY`，保存后重新启动服务。
- **查询失败或结果为空**：检查网络、高德 Key 的服务类型与接口权限、城市名称，以及高德接口返回的信息。
- **地图无法显示**：检查 `AMAP_WEB_KEY` 和高德 JavaScript API 的权限及安全配置。
- **端口被占用**：MCP SSE 端口可在 `config.yaml` 中修改；HTTP 网页入口的 8081 端口在 `http_server.py` 和静态页面中使用，调整时需同步检查。

