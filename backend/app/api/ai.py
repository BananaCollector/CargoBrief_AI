import logging
import time
from threading import Lock

from fastapi import APIRouter, HTTPException, Request, status

from app.config import settings
from app.schemas import AIAnalyzeInput, AIAnalyzeResponse
from app.services.ai_analyzer import (
    AIInvalidResponseError,
    AIProviderError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
    analyze_message,
)

router = APIRouter(prefix="/ai", tags=["ai"])
logger = logging.getLogger(__name__)

_RATE_LIMIT_WINDOW_SECONDS = 60
_RATE_LIMIT_MAX_REQUESTS = 10
_rate_limit_state: dict[str, tuple[float, int]] = {}
_rate_limit_lock = Lock()


def _check_rate_limit(request: Request) -> None:
    client_host = request.client.host if request.client else "unknown"
    now = time.monotonic()

    with _rate_limit_lock:
        expired_clients = [
            host
            for host, (window_start, _) in _rate_limit_state.items()
            if now - window_start >= _RATE_LIMIT_WINDOW_SECONDS
        ]
        for host in expired_clients:
            del _rate_limit_state[host]

        window_start, request_count = _rate_limit_state.get(client_host, (now, 0))
        if request_count >= _RATE_LIMIT_MAX_REQUESTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "ai_rate_limited",
                    "message": "Osiągnięto limit analiz. Spróbuj ponownie za minutę.",
                },
            )
        _rate_limit_state[client_host] = (window_start, request_count + 1)


@router.post("/analyze", response_model=AIAnalyzeResponse)
def analyze(payload: AIAnalyzeInput, request: Request) -> AIAnalyzeResponse:
    if (settings.gemini_api_key or "").strip():
        _check_rate_limit(request)

    try:
        return analyze_message(payload.message)
    except AIProviderTimeoutError as error:
        logger.warning("Gemini analysis timed out")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={
                "code": "ai_timeout",
                "message": "Analiza AI nie odpowiedziała w wymaganym czasie. Spróbuj ponownie.",
            },
        ) from error
    except AIInvalidResponseError as error:
        logger.warning("Gemini returned a response that failed validation")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "ai_invalid_response",
                "message": "Nie udało się bezpiecznie odczytać wyniku analizy AI. Spróbuj ponownie.",
            },
        ) from error
    except AIProviderUnavailableError as error:
        logger.warning("Gemini is temporarily unavailable")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "ai_unavailable",
                "message": "Usługa analizy AI jest chwilowo niedostępna. Spróbuj ponownie później.",
            },
        ) from error
    except AIProviderError as error:
        logger.warning("Gemini analysis failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "ai_provider_error",
                "message": "Nie udało się wykonać analizy AI. Sprawdź konfigurację i spróbuj ponownie.",
            },
        ) from error
