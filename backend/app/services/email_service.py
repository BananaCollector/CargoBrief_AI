import re
from email import policy
from email.header import decode_header, make_header
from email.message import Message, EmailMessage
from email.parser import BytesParser
from email.utils import parseaddr
from html.parser import HTMLParser
from typing import Final

from pydantic import TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.models import IncomingEmail, ShipmentNotification, TransportOrder, TransportShipment
from app.schemas import AIAnalyzeResponse, CustomerEmail

_MAX_STORED_BODY_CHARS: Final = 20_000
_MAX_ANALYSIS_BODY_CHARS: Final = 3_000
_email_adapter = TypeAdapter(CustomerEmail)


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self._parts.append(data.strip())

    def text(self) -> str:
        return "\n".join(self._parts)


def validate_email_address(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return _email_adapter.validate_python(value.strip())
    except ValidationError:
        return None


def _decode_body(message: Message) -> str:
    plain_text: list[str] = []
    html_text: list[str] = []
    parts = message.walk() if message.is_multipart() else [message]

    for part in parts:
        if part.get_content_disposition() == "attachment":
            continue
        content_type = part.get_content_type()
        if content_type not in {"text/plain", "text/html"}:
            continue
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        charset = part.get_content_charset() or "utf-8"
        try:
            content = payload.decode(charset, errors="replace")
        except LookupError:
            content = payload.decode("utf-8", errors="replace")
        if content_type == "text/plain":
            plain_text.append(content)
        else:
            html_parser = _HTMLTextExtractor()
            html_parser.feed(content)
            html_text.append(html_parser.text())

    body = "\n\n".join(plain_text or html_text)
    return re.sub(r"\n{3,}", "\n\n", body).strip()[:_MAX_STORED_BODY_CHARS]


def email_subject_matches(raw_headers: bytes, phrase: str) -> bool:
    message = BytesParser(policy=policy.default).parsebytes(raw_headers)
    subject = str(make_header(decode_header(str(message.get("Subject", "")))))
    return phrase.casefold() in subject.casefold()


def parse_incoming_email(
    raw_message: bytes,
    *,
    mailbox: str,
    uid: str,
) -> IncomingEmail:
    message = BytesParser(policy=policy.default).parsebytes(raw_message)
    message_id_header = str(message.get("Message-ID", "")).strip()
    message_id = (
        f"{mailbox}:{message_id_header}"
        if message_id_header
        else f"{mailbox}:uid:{uid}"
    )[:255]
    sender_address = parseaddr(str(message.get("From", "")))[1]
    subject = str(make_header(decode_header(str(message.get("Subject", "")))))[:500]
    body = _decode_body(message)
    return IncomingEmail(
        message_id=message_id,
        sender_email=validate_email_address(sender_address),
        subject=subject,
        body=body,
        status="pending_analysis",
    )


def store_incoming_email(db: Session, incoming_email: IncomingEmail) -> bool:
    existing_id = db.scalar(
        select(IncomingEmail.id).where(IncomingEmail.message_id == incoming_email.message_id)
    )
    if existing_id is not None:
        return False
    db.add(incoming_email)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing_id = db.scalar(
            select(IncomingEmail.id).where(IncomingEmail.message_id == incoming_email.message_id)
        )
        if existing_id is not None:
            return False
        raise
    return True


def create_order_draft_from_analysis(
    db: Session,
    incoming_email: IncomingEmail,
    analysis: AIAnalyzeResponse,
) -> TransportOrder:
    existing_order = db.scalar(
        select(TransportOrder).where(
            TransportOrder.source_email_id == incoming_email.message_id
        )
    )
    if existing_order is not None:
        incoming_email.converted_order_id = existing_order.id
        incoming_email.status = "converted"
        return existing_order

    order_data = analysis.order.model_dump(exclude={"original_message"})
    order_data["quantity"] = order_data["quantity"] or 1
    order_data["customer_email"] = incoming_email.sender_email
    order_data["original_message"] = incoming_email.body[:_MAX_ANALYSIS_BODY_CHARS]
    order_data["source_email_id"] = incoming_email.message_id
    order_data["status"] = "new"
    order = TransportOrder(**order_data)
    db.add(order)
    db.flush()
    incoming_email.analysis_json = analysis.model_dump_json()
    incoming_email.converted_order_id = order.id
    incoming_email.status = "converted"
    return order


def build_shipment_notification(
    shipment: TransportShipment,
    order: TransportOrder,
    notification: ShipmentNotification,
) -> EmailMessage:
    if order.customer_email is None:
        raise ValueError("A customer email address is required to send a shipment notification.")

    message = EmailMessage()
    message["From"] = settings.gmail_address or ""
    message["To"] = notification.recipient_email
    message["Subject"] = "Informacja o terminie transportu"
    message.set_content(
        "\n".join(
            (
                "Dzień dobry,",
                "",
                f"Informujemy, że transport ładunku „{order.cargo_description}” "
                f"zaplanowano na {shipment.scheduled_date.isoformat()}.",
                f"Miejsce dostawy: {shipment.destination}.",
                "",
                "W razie pytań prosimy o odpowiedź na tę wiadomość.",
                "",
                "CargoBrief AI",
            )
        )
    )
    return message


def analysis_body(incoming_email: IncomingEmail) -> str:
    return incoming_email.body[:_MAX_ANALYSIS_BODY_CHARS]
