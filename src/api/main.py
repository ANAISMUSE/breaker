from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.routers.auth import router as auth_router
from src.api.routers.analytics import router as analytics_router
from src.api.routers.ingestion import router as ingestion_router
from src.api.routers.llm import router as llm_router
from src.api.routers.compliance import router as compliance_router
from src.api.routers.devices import router as devices_router
from src.api.routers.persona import router as persona_router
from src.api.routers.realtime import router as realtime_router
from src.api.routers.risk import router as risk_router
from src.api.routers.simulation import router as simulation_router
from src.api.routers.tasks import router as tasks_router
from src.api.routers.users import router as users_router
from src.api.routers.workbench import router as workbench_router
from src.api.routers.workflow import router as workflow_router
from src.config.settings import settings
from src.storage.mysql_store import MySqlStore

API_PREFIX = "/api"
_log = logging.getLogger(__name__)


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    return [o.strip() for o in raw.split(",") if o.strip()]


def _mount_frontend_if_present(app: FastAPI) -> None:
    root = Path(__file__).resolve().parent.parent.parent
    dist = root / "frontend" / "dist"
    if not dist.is_dir():
        return
    app.mount("/", StaticFiles(directory=str(dist), html=True), name="spa")


def create_app() -> FastAPI:
    settings.validate_runtime()
    app = FastAPI(title="Jianping API", version="0.1.0")

    if MySqlStore.enabled():
        try:
            MySqlStore.from_settings().init_tables()
        except Exception:
            _log.exception(
                "MySQL init_tables failed — check MYSQL_URL / mysqld. /api/health may work; "
                "persistence endpoints may error until DB is fixed."
            )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router, prefix=API_PREFIX)
    app.include_router(users_router, prefix=API_PREFIX)
    app.include_router(ingestion_router, prefix=API_PREFIX)
    app.include_router(llm_router, prefix=API_PREFIX)
    app.include_router(tasks_router, prefix=API_PREFIX)
    app.include_router(devices_router, prefix=API_PREFIX)
    app.include_router(risk_router, prefix=API_PREFIX)
    app.include_router(analytics_router, prefix=API_PREFIX)
    app.include_router(persona_router, prefix=API_PREFIX)
    app.include_router(realtime_router, prefix=API_PREFIX)
    app.include_router(simulation_router, prefix=API_PREFIX)
    app.include_router(compliance_router, prefix=API_PREFIX)
    app.include_router(workbench_router, prefix=API_PREFIX)
    app.include_router(workflow_router, prefix=API_PREFIX)

    @app.get("/health")
    def health_root() -> dict:
        return {"ok": True}

    @app.get(f"{API_PREFIX}/health")
    def health() -> dict:
        return {"ok": True}

    _mount_frontend_if_present(app)
    return app


app = create_app()
