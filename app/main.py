from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.chat import router as chat_router
from app.models.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(chat_router)


@app.get("/health")
def health():
    return {"status": "ok"}


app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
