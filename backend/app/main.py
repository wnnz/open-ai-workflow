from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    admin,
    api_keys,
    auth,
    knowledge,
    models,
    public,
    scripts,
    workflows,
    workspaces,
)
from app.core.config import get_settings

settings = get_settings()
app = FastAPI(
    title="Open AI Workflow API",
    version="0.1.0",
    description="Multi-workspace AI workflow and script management platform",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(workspaces.router, prefix="/api/v1")
app.include_router(scripts.router, prefix="/api/v1")
app.include_router(workflows.router, prefix="/api/v1")
app.include_router(models.router, prefix="/api/v1")
app.include_router(knowledge.router, prefix="/api/v1")
app.include_router(api_keys.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(public.router, prefix="/v1")


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
