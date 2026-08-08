# ASRA

AI Styling Recommendation Assistant

## 项目介绍

ASRA 是基于 LangGraph 的 AI 穿搭推荐 Agent。用户通过自然语言描述城市、场景和风格，Agent 动态决定调用天气、场景、记忆和推荐工具，生成可解释的穿搭方案。

## 核心功能

- 数字衣柜
- 用户画像
- 个性化推荐
- 天气 Agent
- 场景 Agent
- User Memory
- LLM 解释（无 Key 时自动兜底）
- Top N 穿搭推荐

## Agent 架构

```text
User
  |
Agent Router
  |
LangGraph
  |
Decision
  |
Tool Registry
  |
----------------
Weather
Scene
Memory
Recommend
----------------
```

Agent 根据 `tool_plan` 按顺序动态调用工具，不依赖固定流程。

## 技术栈

- Python
- FastAPI
- SQLAlchemy
- SQLite
- LangGraph
- LLM API
- Open-Meteo

## API

```text
POST /agent/recommend
GET  /recommend/
POST /profile/create
PUT  /profile/me
GET  /profile/me
POST /feedback/
GET  /history/
GET  /memory/
```

## 启动

```powershell
cd C:\Users\m1594\Desktop\ASRA
.\venv\Scripts\uvicorn backend.main:app --reload --reload-dir backend --reload-dir database
```

打开：

```text
http://127.0.0.1:8000/docs
```

## 环境变量

```text
SECRET_KEY=your_secret_key
DATABASE_URL=sqlite:///./asra.db
USE_WEATHER_API=true
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
```

## 测试

```powershell
.\venv\Scripts\python.exe -m pytest -q
```
