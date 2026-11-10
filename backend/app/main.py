from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="CargoBrief AI MVP backend",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(f"{settings.api_prefix}/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "database": "sqlite",
        "cors": "configured",
    }


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "CargoBrief AI backend is running."}
