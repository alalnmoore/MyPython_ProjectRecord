from fastapi import APIRouter

from model import Person

param_router = APIRouter(prefix="/param")


@param_router.get("/message/{name}")
def path_param(name: str):
    return {"name": name}


# 获取查询参数
@param_router.get("/query")
def query_param(name: str, age: int):
    return f"姓名为:{name},年龄为:{age}"

# 获取请求体中的参数
@param_router.post("/request_body")
def request_body(user:Person):
    return f"用户名:{user.username},密码:{user.password},爱好:{user.hobby},年龄:{user.age}"
