import asyncio
import imaplib
import logging
import smtplib
import ssl
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.database import SessionLocal
from app.models import EmailInboxFilter, IncomingEmail, ShipmentNotification, TransportOrder, TransportShipment
from app.services.ai_analyzer import AIProviderError, analyze_message
from app.services.email_service import (
    analysis_body,
    build_shipment_notification,
    create_order_draft_from_analysis,
    email_subject_matches,
    parse_incoming_email,
    store_incoming_email,
)

logger = logging.getLogger(__name__)
_MAX_NOTIFICATION_ATTEMPTS = 3
_MAX_MESSAGES_PER_POLL = 25
_MAX_NOTIFICATIONS_PER_POLL = 5


def poll_gmail_inbox() -> int:
    if not settings.gmail_configured:
        return 0

    with SessionLocal() as db:
        email_filter = db.get(EmailInboxFilter, 1)
        filter_enabled = email_filter.enabled if email_filter else False
        subject_phrase = email_filter.subject_phrase if email_filter else ""

    processed_count = 0
    with imaplib.IMAP4_SSL(
        settings.gmail_imap_host,
        settings.gmail_imap_port,
        ssl_context=ssl.create_default_context(),
        timeout=20,
    ) as mailbox:
        mailbox.login(
            settings.gmail_address or "",
            (settings.gmail_app_password or "").replace(" ", ""),
        )
        status, _ = mailbox.select("INBOX")
        if status != "OK":
            raise imaplib.IMAP4.error("Could not select the Gmail inbox.")
        status, search_data = mailbox.uid("search", None, "UNSEEN")
        if status != "OK":
            raise imaplib.IMAP4.error("Could not search the Gmail inbox.")
        if not search_data or not search_data[0]:
            return 0

        unread_uids = search_data[0].split()
        if not filter_enabled:
            unread_uids = unread_uids[:_MAX_MESSAGES_PER_POLL]
        for uid_bytes in unread_uids:
            uid = uid_bytes.decode("ascii", errors="replace")
            if filter_enabled:
                status, header_data = mailbox.uid(
                    "fetch",
                    uid,
                    "(BODY.PEEK[HEADER.FIELDS (SUBJECT)])",
                )
                if status != "OK" or not header_data:
                    logger.warning("Could not fetch an unread Gmail message subject.")
                    continue
                raw_headers = next(
                    (item[1] for item in header_data if isinstance(item, tuple)),
                    None,
                )
                if raw_headers is None or not email_subject_matches(raw_headers, subject_phrase):
                    continue
                if processed_count >= _MAX_MESSAGES_PER_POLL:
                    break
            status, fetch_data = mailbox.uid("fetch", uid, "(BODY.PEEK[])")
            if status != "OK" or not fetch_data:
                logger.warning("Could not fetch an unread Gmail message.")
                continue
            raw_message = next(
                (item[1] for item in fetch_data if isinstance(item, tuple)),
                None,
            )
            if raw_message is None:
                logger.warning("Gmail returned an unread message without a body.")
                continue

            incoming_email = parse_incoming_email(
                raw_message,
                mailbox=settings.gmail_address or "",
                uid=uid,
            )
            with SessionLocal() as db:
                was_stored = store_incoming_email(db, incoming_email)
            status, _ = mailbox.uid("store", uid, "+FLAGS", "\\Seen")
            if status != "OK":
                logger.warning("Could not mark a stored Gmail message as read.")
                continue
            if was_stored:
                processed_count += 1
    return processed_count


def analyze_one_pending_email() -> bool:
    if not (settings.gemini_api_key or "").strip():
        return False

    with SessionLocal() as db:
        incoming_email = db.scalar(
            select(IncomingEmail)
            .where(IncomingEmail.status == "pending_analysis")
            .order_by(IncomingEmail.created_at, IncomingEmail.id)
            .limit(1)
        )
        if incoming_email is None:
            return False

        try:
            analysis = analyze_message(analysis_body(incoming_email))
        except AIProviderError:
            logger.warning("Could not analyze incoming email %s; it will be retried.", incoming_email.id)
            return False

        if analysis.mode != "ai":
            logger.warning("Incoming email %s analysis did not use Gemini; keeping it pending.", incoming_email.id)
            return False
        create_order_draft_from_analysis(db, incoming_email, analysis)
        db.commit()
        return True


def analyze_pending_emails(limit: int = _MAX_MESSAGES_PER_POLL) -> int:
    analyzed_count = 0
    for _ in range(limit):
        if not analyze_one_pending_email():
            break
        analyzed_count += 1
    return analyzed_count


def _send_notification(notification_id: int) -> None:
    with SessionLocal() as db:
        now = datetime.now(timezone.utc)
        claim = db.execute(
            update(ShipmentNotification)
            .where(
                ShipmentNotification.id == notification_id,
                ShipmentNotification.status == "pending",
            )
            .values(
                status="sending",
                attempts=ShipmentNotification.attempts + 1,
                updated_at=now,
            )
        )
        if claim.rowcount != 1:
            db.rollback()
            return
        db.commit()

        notification = db.get(ShipmentNotification, notification_id)
        if notification is None:
            return

        shipment = db.get(TransportShipment, notification.shipment_id)
        order = db.get(TransportOrder, notification.order_id)
        if shipment is None or order is None:
            notification.status = "failed"
            notification.last_error = "Shipment or order no longer exists."
            db.commit()
            return

        try:
            message = build_shipment_notification(shipment, order, notification)
            with smtplib.SMTP_SSL(
                settings.gmail_smtp_host,
                settings.gmail_smtp_port,
                timeout=20,
                context=ssl.create_default_context(),
            ) as smtp:
                smtp.login(
                    settings.gmail_address or "",
                    (settings.gmail_app_password or "").replace(" ", ""),
                )
                refused = smtp.send_message(message)
                if refused:
                    raise smtplib.SMTPRecipientsRefused(refused)
        except (OSError, smtplib.SMTPException, ValueError):
            notification.status = "failed"
            notification.last_error = "Gmail did not accept the notification."
            notification.updated_at = datetime.now(timezone.utc)
            db.commit()
            logger.warning("Gmail rejected a shipment notification.")
            return

        notification.status = "sent"
        notification.last_error = None
        notification.sent_at = datetime.now(timezone.utc)
        notification.updated_at = notification.sent_at
        db.commit()


def process_pending_notifications() -> int:
    if not settings.gmail_configured:
        return 0

    now = datetime.now(timezone.utc)
    stale_sending_before = now - timedelta(minutes=5)
    with SessionLocal() as db:
        db.execute(
            update(ShipmentNotification)
            .where(
                ShipmentNotification.status == "not_configured",
            )
            .values(status="pending", updated_at=now)
        )
        db.execute(
            update(ShipmentNotification)
            .where(
                ShipmentNotification.status == "sending",
                ShipmentNotification.updated_at < stale_sending_before,
            )
            .values(status="pending", updated_at=now)
        )
        db.execute(
            update(ShipmentNotification)
            .where(
                ShipmentNotification.status == "failed",
                ShipmentNotification.attempts < _MAX_NOTIFICATION_ATTEMPTS,
            )
            .values(status="pending", updated_at=now)
        )
        db.commit()
        notification_ids = list(
            db.scalars(
                select(ShipmentNotification.id)
                .where(ShipmentNotification.status == "pending")
                .order_by(ShipmentNotification.id)
                .limit(_MAX_NOTIFICATIONS_PER_POLL)
            ).all()
        )

    for notification_id in notification_ids:
        _send_notification(notification_id)
    return len(notification_ids)


async def run_email_worker() -> None:
    while True:
        try:
            await asyncio.to_thread(poll_gmail_inbox)
        except (imaplib.IMAP4.error, OSError, SQLAlchemyError, ValueError):
            logger.warning("Gmail inbox polling failed; it will be retried.")

        if (settings.gemini_api_key or "").strip():
            try:
                await asyncio.to_thread(analyze_pending_emails, 1)
            except (AIProviderError, SQLAlchemyError):
                logger.warning("Pending email analysis failed; it will be retried.")

        try:
            await asyncio.to_thread(process_pending_notifications)
        except (OSError, smtplib.SMTPException, SQLAlchemyError):
            logger.warning("Shipment notification processing failed; it will be retried.")

        await asyncio.sleep(settings.email_poll_interval_seconds)
