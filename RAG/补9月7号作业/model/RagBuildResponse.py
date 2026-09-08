from pydantic import BaseModel


class RagBuildResponse(BaseModel):
    message: str
    chunkCount: int