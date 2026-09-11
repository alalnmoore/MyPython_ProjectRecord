from pydantic import BaseModel


class ExpenseChatRequest(BaseModel):
    threadId: str
    amount: float | None = None
    reason: str | None = None
    resume: str | None = None