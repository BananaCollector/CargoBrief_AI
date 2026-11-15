import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import ai, dev, email, orders, shipments, vehicles
from app.config import settings
from app.services.email_worker import run_email_worker


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    worker_task = (
        asyncio.create_task(run_email_worker())
        if settings.gmail_configured
        else None
    )
    yield
    if worker_task is not None:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="CargoBrief AI MVP backend",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(orders.router, prefix=settings.api_prefix)
app.include_router(email.router, prefix=settings.api_prefix)
app.include_router(shipments.router, prefix=settings.api_prefix)
app.include_router(vehicles.router, prefix=settings.api_prefix)
app.include_router(ai.router, prefix=settings.api_prefix)
app.include_router(dev.router, prefix=settings.api_prefix)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    error_count = len(exc.errors())
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": (
                    f"Dane żądania {request.method} są nieprawidłowe "
                    f"(liczba błędów: {error_count})."
                ),
            }
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    detail = exc.detail
    if not isinstance(detail, dict) or "code" not in detail or "message" not in detail:
        if exc.status_code == 404:
            detail = {
                "code": "not_found",
                "message": f"Nie znaleziono zasobu: {request.url.path}.",
            }
        elif exc.status_code == 405:
            detail = {
                "code": "method_not_allowed",
                "message": f"Metoda {request.method} nie jest dozwolona dla tego zasobu.",
            }
        else:
            detail = {"code": "http_error", "message": str(detail)}
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": detail},
        headers=exc.headers,
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
