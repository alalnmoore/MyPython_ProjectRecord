# FastAPI × LangChain × LangGraph

## 生产级 Agentic AI 后端技术栈

高性能异步 API · 有状态多智能体编排 · 持久化执行

---

## 📖 概览

本仓库展示了一种面向生产环境的架构，将三种互补技术有机结合：

| 层级 | 技术 | 职责 |
| --- | --- | --- |
| API 网关 | FastAPI | 高并发异步 HTTP 层、校验、鉴权、流式传输 |
| 智能体抽象 | LangChain | 模型、工具、提示词、检索、与提供商无关的集成 |
| 编排运行时 | LangGraph | 有状态图、循环、持久化、人在回路、多智能体 |

**关键洞察（2025–2026）**：LangChain 的新版 `create_agent` 运行在 LangGraph 运行时之上。

> 先从简单的 LangChain 入手；当你需要持久化状态、循环或细粒度控制时，再降级使用显式的 `StateGraph`。

---

## 🏗 架构

```text
┌─────────────────────────────────────────────────────────────────┐
│                          客户端                                   │
│              （Web / Mobile / 其他服务）                           │
└────────────────────────────┬────────────────────────────────────┘
                             │  HTTP / SSE
┌────────────────────────────▼────────────────────────────────────┐
│                        FastAPI 层                                │
│  • Pydantic 校验        • 依赖注入                                │
│  • 鉴权与限流           • lifespan（图只编译一次）                 │
│  • StreamingResponse    • OpenAPI 文档                           │
└────────────────────────────┬────────────────────────────────────┘
                             │  thread_id = session_id
┌────────────────────────────▼────────────────────────────────────┐
│                      LangGraph 运行时                            │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────────────┐   │
│  │   节点       │──▶│    边       │──▶│   条件路由            │   │
│  │ (LLM/工具)  │   │（状态迁移） │   │ （循环 / 分支）        │   │
│  └─────────────┘   └─────────────┘   └─────────────────────┘   │
│                                                                 │
│  状态  ←→  检查点器（Postgres / Redis）                           │
│  记忆  ←→  短期 + 长期                                           │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                   LangChain 构建模块                             │
│  • 聊天模型（OpenAI / Anthropic / 本地）                          │
│  • 工具与 MCP 适配器                                              │
│  • 检索器 / 向量数据库                                            │
│  • 提示词模板与输出解析器                                          │
└─────────────────────────────────────────────────────────────────┘
```

### 为什么选择这套技术栈？

- **FastAPI** 凭借原生 `async/await`、自动 OpenAPI 与一流的流式支持，带来卓越性能；
- **LangChain** 提供最丰富的模型集成、工具与检索组件生态；
- **LangGraph** 通过显式图、检查点（checkpointing）和人在回路（human-in-the-loop）原语，把智能体变成可靠、可观测、可恢复的程序。

---

## ✨ 核心能力

### FastAPI

- 全异步请求处理
- 面向智能体 / 图 / 检查点器的依赖注入
- 原生 `StreamingResponse` + 服务器推送事件（Server-Sent Events，SSE）
- 生命周期事件 → 启动时只编译一次图
- Pydantic v2 模型，实现严格的请求 / 响应契约
- 内置 OpenAPI / Swagger UI

### LangChain

- 与提供商无关的模型接口
- 工具调用与结构化输出
- RAG 流水线（分块、嵌入、混合检索）
- 对 MCP（Model Context Protocol）的一流支持
- 提供从简单智能体平滑迁移到复杂图的路径

### LangGraph

- `StateGraph` — 显式节点 + 边
- 循环与条件路由（智能体循环）
- 通过检查点器实现持久化执行（生产推荐使用 Postgres）
- 人在回路（`interrupt` / `resume`）
- 时间旅行调试与状态重放
- 多智能体模式：Supervisor、层级式、网络式、自定义
- 流式输出：`astream` / `astream_events`

---

## 🚀 快速开始

### 1. 环境要求

- Python >= 3.11

### 2. 安装

```bash
# 推荐使用 uv
uv add fastapi uvicorn[standard] langchain langgraph \
       langchain-openai langchain-community \
       pydantic-settings asyncpg redis

# 或者使用 pip
pip install "fastapi[standard]" langchain langgraph \
            langchain-openai pydantic-settings
```

### 3. 最小可运行示例

```python
# app/main.py
from contextlib import asynccontextmanager
from typing import Annotated, TypedDict

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver  # 生产环境可换成 Postgres
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# ── 状态 ────────────────────────────────────────────────
class AgentState(TypedDict):
    messages: Annotated[list, lambda x, y: x + y]

# ── 图的定义 ───────────────────────────────────────────
def create_graph():
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    def call_model(state: AgentState):
        response = llm.invoke(state["messages"])
        return {"messages": [response]}

    builder = StateGraph(AgentState)
    builder.add_node("agent", call_model)
    builder.add_edge(START, "agent")
    builder.add_edge("agent", END)

    # 生产环境：将 MemorySaver 替换为 AsyncPostgresSaver
    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)

# ── FastAPI 生命周期 ───────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.graph = create_graph()
    yield

app = FastAPI(title="Agent API", version="1.0.0", lifespan=lifespan)

@app.post("/chat")
async def chat(request: Request, message: str, session_id: str = "default"):
    graph = request.app.state.graph
    config = {"configurable": {"thread_id": session_id}}

    async def event_stream():
        async for event in graph.astream(
            {"messages": [HumanMessage(content=message)]},
            config=config,
            stream_mode="messages",
        ):
            # 简化的 token 流式输出
            if event:
                yield f"data: {event}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

启动运行：

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 🗂 推荐的项目结构

```text
agent-service/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 入口 + lifespan
│   ├── api/
│   │   ├── routes/
│   │   │   ├── chat.py
│   │   │   └── health.py
│   │   └── deps.py             # 依赖注入
│   ├── agents/
│   │   ├── graphs/
│   │   │   ├── research.py     # 复杂的 StateGraph
│   │   │   └── simple.py
│   │   ├── nodes/
│   │   └── tools/
│   ├── core/
│   │   ├── config.py           # pydantic-settings
│   │   ├── checkpointer.py     # Postgres / Redis 工厂
│   │   └── logging.py
│   ├── schemas/
│   │   └── chat.py             # 请求 / 响应模型
│   └── middleware/
├── tests/
├── Dockerfile
├── docker-compose.yml          # Postgres + Redis + App
├── pyproject.toml
└── README.md
```

---

## 🔑 生产实践模式

### 1. 只编译一次图（lifespan）

永远不要在请求处理函数内部编译图：

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.graph = create_production_graph()
    yield
    # 需要时在此清理
```

### 2. 会话隔离

```python
# 始终基于 用户 + 会话 派生 thread_id
thread_id = f"{tenant_id}:{user_id}:{session_id}"
config = {"configurable": {"thread_id": thread_id}}
```

### 3. 持久化检查点器

```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

async with AsyncPostgresSaver.from_conn_string(DATABASE_URL) as checkpointer:
    await checkpointer.setup()
    graph = builder.compile(checkpointer=checkpointer)
```

### 4. 使用 SSE 流式输出

```python
return StreamingResponse(
    graph.astream(..., stream_mode="messages"),
    media_type="text/event-stream",
)
```

当你需要节点级可观测性时，优先使用 `astream_events(version="v2")`。

### 5. 人在回路（Human-in-the-Loop）

```python
# 在某个节点内部
from langgraph.types import interrupt

decision = interrupt({"question": "是否批准此操作？"})
if decision.get("approved"):
    ...
```

之后使用相同的 `thread_id` 和 `Command(resume=...)` 恢复执行。

---

## 🧠 多智能体模式（LangGraph）

| 模式 | 描述 | 适用场景 |
| --- | --- | --- |
| Supervisor（主管） | 中央智能体将任务路由给专业的子智能体 | 任务层级清晰 |
| Hierarchical（层级式） | 主管的主管，层层嵌套 | 大型团队 / 复杂领域 |
| Network（网络式） | 任意智能体之间可互相调用 | 需要高度协作的智能体 |
| Custom Workflow（自定义工作流） | 显式边 + 选择性智能体决策 | 需要最大控制力与可审计性 |

---

## 🛡 安全与运维检查清单

- 密钥通过环境变量 / Vault 管理（绝不硬编码）
- 限流与鉴权中间件
- 使用 Pydantic 做输入校验
- 输出内容审核 / guardrails 节点
- 结构化日志 + 请求 ID
- 健康检查与就绪探针（health & readiness probes）
- 借助共享的 Postgres 检查点器实现水平扩展
- 可观测性：LangSmith / OpenTelemetry

---

## 📚 参考资料

- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [LangChain 文档](https://python.langchain.com/)
- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [LangGraph 持久化](https://langchain-ai.github.io/langgraph/concepts/persistence/)
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)

---

## 📄 许可证

MIT License — 欢迎将此架构作为生产级智能体系统的基础自由使用。

> 为那些致力于交付可靠 AI 系统的工程师而构建。
>
> **FastAPI 负责边缘 · LangChain 负责组件 · LangGraph 负责大脑**
