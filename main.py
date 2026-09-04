from fastapi import FastAPI, APIRouter

from demo import example_router
from homework_9_4 import love_router
from param import param_router
app = FastAPI()
app.include_router(param_router)
app.include_router(example_router)
app.include_router(love_router)

@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}
