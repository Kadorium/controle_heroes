from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.foundation.audit_routes import router as audit_router
from app.foundation.auth_routes import router as auth_router
from app.foundation.database import SessionLocal
from app.foundation.document_routes import router as document_router
from app.foundation.errors import AppError, app_error_handler, http_error_handler
from app.foundation.health import router as health_router
from app.foundation.logging import configure_logging
from app.foundation.settings import ensure_runtime_dirs, get_settings
from app.identity.seed import ensure_seed
from app.catalog.routes import router as catalog_router
from app.orders.routes import router as orders_router
from app.billing.routes import router as billing_router
from app.treasury.routes import router as treasury_router
from app.treasury.fx_routes import router as treasury_fx_router
from app.reporting.routes import router as reporting_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    ensure_runtime_dirs(settings)
    if settings.app_env != "test":
        db = SessionLocal()
        try:
            ensure_seed(
                db,
                email=settings.seed_admin_email,
                password=settings.seed_admin_password,
                name=settings.seed_admin_name,
            )
            db.commit()
        finally:
            db.close()
    yield


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    application = FastAPI(title=settings.app_name, lifespan=lifespan)
    application.add_exception_handler(AppError, app_error_handler)
    application.add_exception_handler(HTTPException, http_error_handler)

    application.include_router(health_router, prefix="/api")
    application.include_router(auth_router, prefix="/api")
    application.include_router(audit_router, prefix="/api")
    application.include_router(document_router, prefix="/api")
    application.include_router(catalog_router, prefix="/api")
    application.include_router(orders_router, prefix="/api")
    application.include_router(billing_router, prefix="/api")
    application.include_router(treasury_router, prefix="/api")
    application.include_router(treasury_fx_router, prefix="/api")
    application.include_router(reporting_router, prefix="/api")
    dist = settings.frontend_dist_path
    if dist.exists():
        assets = dist / "assets"
        if assets.exists():
            application.mount("/assets", StaticFiles(directory=str(assets)), name="assets")

        @application.get("/{full_path:path}")
        async def spa_fallback(full_path: str):
            if full_path.startswith("api"):
                raise HTTPException(status_code=404, detail="Not found")
            index = dist / "index.html"
            if index.exists():
                return FileResponse(index)
            raise HTTPException(status_code=404, detail="Frontend not built")

    return application


app = create_app()
