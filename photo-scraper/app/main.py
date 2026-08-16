from fastapi import FastAPI

from .routers import router

app = FastAPI()

app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok"}
