from pydantic import BaseModel


class Person(BaseModel):
    username: str
    password:str
    hobby:str
    age:int|None=None

