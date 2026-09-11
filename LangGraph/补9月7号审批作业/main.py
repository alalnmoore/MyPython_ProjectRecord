"""
FastAPI 入口
POST /api/state-graph/expense/chat
SSE 流式输出
"""
import json
import sys
from pathlib import Path

_PROJECT_DIR = Path(__file__).resolve().parent
if str(_PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(_PROJECT_DIR))

import uvicorn
from fastapi import FastAPI
from langgraph.types import Command
from starlette.responses import StreamingResponse

from model.ExpenseChatRequest import ExpenseChatRequest
from node.expenseGraph import compiled_expense_graph

app = FastAPI()


@app.post("/api/state-graph/expense/chat")
def expense_chat(req: ExpenseChatRequest):
    def stream_event():
        config = {"configurable": {"thread_id": req.threadId}}

        # 判断是首次请求还是恢复执行
        if req.resume is None:
            graph_input = {"amount": req.amount, "reason": req.reason}
        else:
            graph_input = Command(resume=req.resume)

        for node in compiled_expense_graph.stream(graph_input, config):
            # 中断事件
            if "__interrupt__" in node:
                interrupt = node["__interrupt__"][0]
                value = interrupt.value
                if isinstance(value, dict):
                    message = value.get("message", str(value))
                else:
                    message = str(value)
                payload = json.dumps(
                    {"type": "interrupt", "node": "wait_review", "message": message},
                    ensure_ascii=False,
                )
                yield f"data:{payload}\n\n"
                continue

            # 普通节点 / 最终节点
            for node_name, state_update in node.items():
                payload_out = {"type": "node", "node": node_name}
                if node_name == "process_expense" and isinstance(state_update, dict):
                    msg = state_update.get("process_result")
                    if msg:
                        payload_out["message"] = msg
                payload = json.dumps(payload_out, ensure_ascii=False)
                yield f"data:{payload}\n\n"

        yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(stream_event(), media_type="text/event-stream")


if __name__ == "__main__":
    print("🚀 启动 FastAPI 服务...")
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=9999,
        log_level="info",
    )