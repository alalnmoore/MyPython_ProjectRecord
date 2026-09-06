from pydantic import BaseModel, Field


class SentimentResult(BaseModel):
    # Filed是对参数进行描述
    sentiment: str = Field(description="情感倾向：正面、负面、中性")
    score: int = Field(description="强烈程度，1-10分")
    keywords: list[str] = Field(description="关键词列表")