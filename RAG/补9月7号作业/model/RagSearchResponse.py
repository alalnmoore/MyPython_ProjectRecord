from pydantic import BaseModel


class RagSearchResponse(BaseModel):
    query: str
    answer: str