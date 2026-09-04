from fastapi import FastAPI

from param import param_router

app = FastAPI()
app.include_router(param_router)

@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}
