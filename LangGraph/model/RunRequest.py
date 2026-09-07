from pydantic import BaseModel


class RunRequest(BaseModel):
    threadId: str
    input: dict | None = None       # 首次执行时传入初始数据
    resume: str | None = None