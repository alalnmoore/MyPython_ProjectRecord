from pydantic import BaseModel


class RagSearchRequest(BaseModel):
    query: str