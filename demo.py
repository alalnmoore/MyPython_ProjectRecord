from fastapi import APIRouter
from pydantic import BaseModel
from fastapi.responses import PlainTextResponse

class UserCreate(BaseModel):
    username:str
    password:str
    age:int
    email:str|None = "该用户没有email"

class UserResponse(BaseModel):
    user_id:int
    username:str
    age:int
    email:str|None = "该用户没有email"

# 使用字典来存储数据
users_db = {}
next_user_id = 1

example_router = APIRouter(prefix="/example")

# 初始界面的展示
@example_router.get("/welcome")
def root():
    return "======================="+"\n"+ "欢迎来到员工管理界面"+"\n"+"======================="

# 添加用户的功能展示
@example_router.post("/user/add")
def create_user_funcion(user: UserCreate):
    global next_user_id
# 创建用户对象并存入字典中
    new_user = UserResponse(
        user_id=next_user_id,
        username=user.username,
        age=user.age,
        email=user.email
    )
# 将用户信息存储到字典中，然后global自增,作为键
    users_db[next_user_id] = new_user
    next_user_id += 1
    return new_user

# 进行用户的查询，通过id查询，id是字典中的键
@example_router.get("/user/{user_id}")
def query_user(user_id:int):
    if user_id not in users_db:
        return "用户不存在"
    else:
        return users_db[user_id]
if __name__ == "__main__":
    print(users_db)

# 进行分页查询，然后进行切查询
@example_router.get("/user/select")
def select_user(page:int,page_size:int):
# 先进性获取字典中的所有用户的信息，放进一个list中
    user_message_list = list(users_db.value())
    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    return{
        "total":len(user_message_list),
        "page":page,
        "page_size":page_size,
        "user":user_message_list[start_index:end_index]
    }









