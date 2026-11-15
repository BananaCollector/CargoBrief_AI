import logging
import imaplib

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.ai import _check_rate_limit
from app.api.orders import build_order_detail, get_vehicles
from app.config import settings
from app.database import get_db
from app.models import IncomingEmail, TransportOrder
from app.schemas import (
    AIAnalyzeResponse,
    EmailInboxFilterRead,
    EmailInboxFilterUpdate,
    EmailSyncResult,
    IncomingEmailRead,
    TransportOrderCreate,
    TransportOrderDetail,
)
from app.services.ai_analyzer import (
    AIInvalidResponseError,
    AIProviderError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
    analyze_message,
)
from app.services.email_service import analysis_body, create_order_draft_from_analysis
from app.services.email_filter import read_email_inbox_filter, save_email_inbox_filter
from app.services.email_worker import analyze_pending_emails, poll_gmail_inbox

router = APIRouter(prefix="/email/inbox", tags=["email"])
logger = logging.getLogger(__name__)


def _build_incoming_email_read(incoming_email: IncomingEmail) -> IncomingEmailRead:
    analysis = (
        AIAnalyzeResponse.model_validate_json(incoming_email.analysis_json)
        if incoming_email.analysis_json
        else None
    )
    return IncomingEmailRead(
        id=incoming_email.id,
        sender_email=incoming_email.sender_email,
        subject=incoming_email.subject,
        body=incoming_email.body,
        status=incoming_email.status,
        analysis=analysis,
        converted_order_id=incoming_email.converted_order_id,
        created_at=incoming_email.created_at,
    )


@router.get("", response_model=list[IncomingEmailRead])
def list_incoming_emails(db: Session = Depends(get_db)) -> list[IncomingEmailRead]:
    emails = db.scalars(
        select(IncomingEmail)
        .order_by(IncomingEmail.created_at.desc(), IncomingEmail.id.desc())
        .limit(100)
    ).all()
    return [_build_incoming_email_read(incoming_email) for incoming_email in emails]


@router.get("/filter", response_model=EmailInboxFilterRead)
def get_incoming_email_filter(db: Session = Depends(get_db)) -> EmailInboxFilterRead:
    return read_email_inbox_filter(db)


@router.put("/filter", response_model=EmailInboxFilterRead)
def update_incoming_email_filter(
    payload: EmailInboxFilterUpdate,
    db: Session = Depends(get_db),
) -> EmailInboxFilterRead:
    return save_email_inbox_filter(db, payload)


@router.post("/sync", response_model=EmailSyncResult)
def sync_incoming_emails() -> EmailSyncResult:
    if not settings.gmail_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "gmail_not_configured",
                "message": "Skonfiguruj adres Gmail i hasło aplikacji w backend/.env.",
            },
        )
    try:
        imported_count = poll_gmail_inbox()
        analyzed_count = analyze_pending_emails() if (settings.gemini_api_key or "").strip() else 0
        return EmailSyncResult(
            imported_count=imported_count,
            analyzed_count=analyzed_count,
        )
    except (imaplib.IMAP4.error, OSError, SQLAlchemyError, ValueError) as error:
        logger.warning("Manual Gmail inbox synchronization failed.")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "gmail_sync_failed",
                "message": "Nie udało się sprawdzić skrzynki Gmail. Sprawdź konfigurację i spróbuj ponownie.",
            },
        ) from error


@router.post("/{email_id}/analyze", response_model=IncomingEmailRead)
def analyze_incoming_email(
    email_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> IncomingEmailRead:
    incoming_email = db.get(IncomingEmail, email_id)
    if incoming_email is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "email_not_found", "message": "Nie znaleziono wiadomości."},
        )
    if incoming_email.status == "converted":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "email_already_converted", "message": "Wiadomość została już zamieniona na zlecenie."},
        )
    if not (settings.gemini_api_key or "").strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "ai_unavailable", "message": "Ustaw GEMINI_API_KEY, aby analizować e-maile."},
        )
    _check_rate_limit(request)

    try:
        analysis = analyze_message(analysis_body(incoming_email))
    except AIProviderTimeoutError as error:
        logger.warning("Gemini analysis of an incoming email timed out")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={"code": "ai_timeout", "message": "Analiza e-maila nie odpowiedziała na czas."},
        ) from error
    except AIInvalidResponseError as error:
        logger.warning("Gemini returned an invalid incoming email analysis")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "ai_invalid_response", "message": "Nie udało się zweryfikować analizy e-maila."},
        ) from error
    except AIProviderUnavailableError as error:
        logger.warning("Gemini is unavailable for incoming email analysis")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "ai_unavailable", "message": "Usługa AI jest chwilowo niedostępna."},
        ) from error
    except AIProviderError as error:
        logger.warning("Gemini failed to analyze an incoming email")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "ai_provider_error", "message": "Nie udało się przeanalizować e-maila."},
        ) from error

    if analysis.mode != "ai":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "ai_unavailable", "message": "Analiza DEMO nie jest używana do e-maili klientów."},
        )
    create_order_draft_from_analysis(db, incoming_email, analysis)
    db.commit()
    db.refresh(incoming_email)
    return _build_incoming_email_read(incoming_email)


@router.post("/{email_id}/convert", response_model=TransportOrderDetail, status_code=status.HTTP_201_CREATED)
def convert_incoming_email(
    email_id: int,
    payload: TransportOrderCreate,
    db: Session = Depends(get_db),
) -> TransportOrderDetail:
    incoming_email = db.get(IncomingEmail, email_id)
    if incoming_email is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "email_not_found", "message": "Nie znaleziono wiadomości."},
        )
    if incoming_email.status == "converted":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "email_already_converted", "message": "Wiadomość została już zamieniona na zlecenie."},
        )

    order_data = payload.model_dump()
    order_data["original_message"] = incoming_email.body[:3000]
    if order_data["customer_email"] is None:
        order_data["customer_email"] = incoming_email.sender_email
    order = TransportOrder(**order_data, source_email_id=incoming_email.message_id)
    db.add(order)
    incoming_email.status = "converted"
    try:
        db.flush()
        incoming_email.converted_order_id = order.id
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "email_already_converted", "message": "Wiadomość została już przypisana do zlecenia."},
        ) from error
    db.refresh(order)
    return build_order_detail(order, get_vehicles(db))
