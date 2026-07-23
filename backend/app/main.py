from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.db import init_db
from app.api import auth
from app.api.deps import get_current_user
from app.models.user import User


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()          # dev convenience; use Alembic migrations in production
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tighten to your app/admin origins in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "service": settings.app_name}


@app.get("/", tags=["system"])
def root():
    return {"message": "DearBaby API. See /docs for the interactive API."}
