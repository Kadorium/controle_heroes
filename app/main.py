from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.api import (
    auth,
    closure,
    customs,
    dashboard,
    demo,
    documents,
    finance,
    health,
    importations,
    imports,
    invoices,
    landed_cost,
    products,
    reconciliation,
    shipments,
    stock,
    suppliers,
    users,
)
from app.config import ensure_runtime_dirs, get_settings
from app.database import SessionLocal
from app.services.seed import run_initial_seed

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_runtime_dirs(settings)
    db: Session = SessionLocal()
    try:
        run_initial_seed(
            db,
            settings.seed_admin_email,
            settings.seed_admin_password,
            settings.seed_admin_name,
        )
    finally:
        db.close()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(suppliers.router, prefix="/api")
app.include_router(products.router, prefix="/api")
app.include_router(importations.router, prefix="/api")
app.include_router(invoices.router, prefix="/api")
app.include_router(finance.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(imports.router, prefix="/api")
app.include_router(shipments.router, prefix="/api")
app.include_router(customs.router, prefix="/api")
app.include_router(stock.router, prefix="/api")
app.include_router(landed_cost.router, prefix="/api")
app.include_router(reconciliation.router, prefix="/api")
app.include_router(closure.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(demo.router, prefix="/api")

dist = settings.frontend_dist_path
if dist.exists():
    assets_dir = dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        if full_path.startswith("api"):
            raise HTTPException(status_code=404)
        index = dist / "index.html"
        if index.exists():
            return FileResponse(index)
        raise HTTPException(status_code=404, detail="Frontend não buildado")


def main():
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.is_development,
    )


if __name__ == "__main__":
    main()
