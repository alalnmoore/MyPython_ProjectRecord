import json

import uvicorn
from fastapi import FastAPI
from langgraph.types import Command
from starlette.responses import StreamingResponse

from LangGraph.model.RunRequest import RunRequest
from LangGraph.node.orderGraph_test import compiled_order_graph

app = FastAPI()
@app.post("/order")
def order(req:RunRequest):
    def stream_event():
    # 接收用户输入的thread_id
        config = {"configurable":{"thread_id":req.threadId}}
        if req.input is not None:
        # 说明是第一次没有触发中断的环节
            graph_input = req.input
        else:
            graph_input =Command(resume=req.resume)

        for node in compiled_order_graph.stream(graph_input,config):
            if "__interrupt__" in node:
            # 拿到node这个字典中的interrupt键所对的值，是一个列表
                interrupt = node["__interrupt__"][0]
                value = interrupt.value
                payload = json.dumps({"type": "interrupt", "question": value}, ensure_ascii=False)
                yield f"data:{payload}\n\n"
                return
            for node_name in node:
                payload = json.dumps({"type":"node","node_name":node_name}, ensure_ascii=False)
                yield f"data:{payload}\n\n"
        yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
    return StreamingResponse(stream_event(), media_type="text/event-stream")





if __name__ == "__main__":
    print("🚀 启动 FastAPI 服务...")
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=9999,
        log_level="info"  # 显示详细日志
    )