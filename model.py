from pydantic import BaseModel


class Person(BaseModel):
    username: str
    password:str
    hobby:str
    age:int|None=None

# 用于接收发送的json
class DiaryCreate(BaseModel):
    user_id: int|None=None
    content:str|None=None
    mood:str|None=None
    scene:str|None=None

# 保存的对象
class DiaryResponse(BaseModel):
    diary_id:int
    user_id:int
    content:str
    scene:str


