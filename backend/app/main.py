"""SocietyHub API entrypoint."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import Base, SessionLocal, engine
from .routers import auth, broadcasts, dashboard, departments, transactions, users
from .seed import run_seed

logging.basicConfig(level=logging.INFO)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        run_seed(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="SocietyHub API",
    description="Apartment society management: users, departments, credit/debit, broadcasts.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(departments.router)
app.include_router(transactions.router)
app.include_router(broadcasts.router)
app.include_router(dashboard.router)


@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok"}


@app.get("/api/config", tags=["config"])
def public_config():
    """Public runtime flags the frontend needs before login."""
    return {"require_otp": settings.REQUIRE_OTP, "app_name": settings.APP_NAME}


# Serve the web frontend (SPA) at the root. Mounted LAST so the /api/* routes and
# /docs registered above take priority; StaticFiles(html=True) serves index.html at "/".
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
