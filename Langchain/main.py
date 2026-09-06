import os
import json

import uvicorn
from fastapi import FastAPI
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from starlette.responses import StreamingResponse

app = FastAPI()

llm = ChatOpenAI(
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    api_key=os.getenv("Alibaba_Key"),
    model="qwen-plus"
)


@app.post("/stream/demo")  # ✅ 直接挂载到 app 上
def stream_chat(message: str):
    def event_stream():
        human_message = [HumanMessage(content=message)]
        for chunk in llm.stream(human_message):
            text = chunk.content
            if text:
                payload = json.dumps({"type": "delta", "text": text}, ensure_ascii=False)
                yield f"data: {payload}\n\n"
        yield f'data: {json.dumps({"type": "done"})}\n\n'

    return StreamingResponse(event_stream(), media_type="text/event-stream")

if __name__ == "__main__":
    print("🚀 启动 FastAPI 服务...")
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=9999,
        log_level="info"  # 显示详细日志
    )