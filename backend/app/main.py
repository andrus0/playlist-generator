import logging
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import func, select

from .api.routes import limiter, router
from .config import settings
from .db import SessionLocal, init_db
from .models import Song

log = logging.getLogger(__name__)


def _auto_import() -> None:
    from .importers import billboard
    from .importers.base import compute_artist_stats

    with SessionLocal() as s:
        if s.scalar(select(func.count(Song.id))):
            return
        log.info("database empty – running initial import")
        billboard.run(s)
        compute_artist_stats(s)
        log.info("initial import done")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    if settings.auto_import:
        threading.Thread(target=_auto_import, daemon=True).start()
    yield


app = FastAPI(
    title="Playlist Generator",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
        allow_methods=["GET"],
        allow_headers=["*"],
    )
app.include_router(router)

# Serve the built frontend (SvelteKit static build) if present
_static = Path(settings.static_dir)
if _static.is_dir():
    app.mount("/", StaticFiles(directory=_static, html=True), name="static")
