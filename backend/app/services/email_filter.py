from sqlalchemy.orm import Session

from app.models import EmailInboxFilter
from app.schemas import EmailInboxFilterRead, EmailInboxFilterUpdate


def read_email_inbox_filter(db: Session) -> EmailInboxFilterRead:
    config = db.get(EmailInboxFilter, 1)
    if config is None:
        return EmailInboxFilterRead(enabled=False, subject_phrase="")
    return EmailInboxFilterRead(enabled=config.enabled, subject_phrase=config.subject_phrase)


def save_email_inbox_filter(
    db: Session,
    payload: EmailInboxFilterUpdate,
) -> EmailInboxFilterRead:
    config = db.get(EmailInboxFilter, 1)
    if config is None:
        config = EmailInboxFilter(id=1)
        db.add(config)
    config.enabled = payload.enabled
    config.subject_phrase = payload.subject_phrase if payload.enabled else ""
    db.commit()
    db.refresh(config)
    return EmailInboxFilterRead(enabled=config.enabled, subject_phrase=config.subject_phrase)
