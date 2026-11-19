"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.admin import admin_router
from app.api.v1.router import api_router
from app.cli import bootstrap_admin
from app.core.config import settings
from app.core.errors import register_exception_handlers


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Upsert the optional bootstrap admin, then serve requests."""
    bootstrap_admin()
    yield


app = FastAPI(title="Badminton Club Ranking API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(api_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
