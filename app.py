from contextvars import ContextVar

import uvicorn
from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import JSONResponse

from filters.filter_engine import SqlAlchemyFilterEngine
from filters.models import Shop
from ss.audit.decorators import audit_event

app = FastAPI()


req: ContextVar[Request] = ContextVar("request")


async def foo():
    r = req.get(None)
    for k, v in r.items():
        print(k, v)


@app.get("/")
async def hello_world():
    await foo()
    return {"Hello": "World"}


@app.get("/login")
@audit_event("Логин")
async def login():
    a = 2 / 0
    return JSONResponse({"token": "<PASSWORD>"})


@app.get("/list")
async def list():
    filter_engine = SqlAlchemyFilterEngine(Shop)
    return JSONResponse({"token": "<PASSWORD>"})


@app.middleware("http")
async def create_context(request: Request, call_next):
    token = req.set(request)
    try:
        response = await call_next(request)
    finally:
        req.reset(token)
    return response


if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=7000, reload=True)
