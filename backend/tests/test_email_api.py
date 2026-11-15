from contextlib import contextmanager

from app.api import ai as ai_api
from app.api import email as email_api
from app.config import settings
from app.database import get_db
from app.main import app
from app.models import IncomingEmail
from app.schemas import AIAnalyzeResponse, AIAnalyzedOrder
from app.services import ai_analyzer, email_worker


def insert_incoming_email(
    *,
    message_id: str = "test-mailbox:<message-1@example.com>",
    sender_email: str | None = "customer@example.com",
    body: str = "Proszę przewieźć paczkę z Warszawy do Gdańska.",
    status: str = "ready",
    analysis_json: str | None = None,
) -> int:
    db_dependency = app.dependency_overrides[get_db]
    generator = db_dependency()
    db = next(generator)
    incoming_email = IncomingEmail(
        message_id=message_id,
        sender_email=sender_email,
        subject="Prośba o transport",
        body=body,
        status=status,
        analysis_json=analysis_json,
    )
    db.add(incoming_email)
    db.commit()
    db.refresh(incoming_email)
    incoming_email_id = incoming_email.id
    generator.close()
    return incoming_email_id


def session_factory_for_test():
    @contextmanager
    def session_context():
        db_dependency = app.dependency_overrides[get_db]
        generator = db_dependency()
        db = next(generator)
        try:
            yield db
        finally:
            generator.close()

    return session_context


def test_incoming_email_is_converted_to_an_order_once(client) -> None:
    analysis = AIAnalyzeResponse(
        order=AIAnalyzedOrder(
            cargo_description="Paczka",
            pickup_location="Warszawa",
            delivery_location="Gdańsk",
            original_message="Fragment",
        ),
        missing_fields=["length_cm", "weight_kg"],
        ambiguities=[],
        mode="ai",
    )
    email_id = insert_incoming_email(analysis_json=analysis.model_dump_json())

    response = client.get("/api/v1/email/inbox")
    assert response.status_code == 200
    assert response.json()[0]["analysis"]["order"]["cargo_description"] == "Paczka"

    response = client.post(
        f"/api/v1/email/inbox/{email_id}/convert",
        json={
            "cargo_description": "Paczka",
            "pickup_location": "Warszawa",
            "delivery_location": "Gdańsk",
            "customer_email": None,
            "customer_phone": "+48 500 600 700",
        },
    )

    assert response.status_code == 201
    order = response.json()
    assert order["customer_email"] == "customer@example.com"
    assert order["customer_phone"] == "+48 500 600 700"
    assert order["original_message"] == "Proszę przewieźć paczkę z Warszawy do Gdańska."
    inbox_after_conversion = client.get("/api/v1/email/inbox").json()
    assert len(inbox_after_conversion) == 1
    assert inbox_after_conversion[0]["status"] == "converted"
    assert inbox_after_conversion[0]["converted_order_id"] == order["id"]
    duplicate_response = client.post(
        f"/api/v1/email/inbox/{email_id}/convert",
        json={
            "cargo_description": "Paczka",
            "pickup_location": "Warszawa",
            "delivery_location": "Gdańsk",
        },
    )
    assert duplicate_response.status_code == 409


def test_incoming_email_analysis_requires_gemini_and_never_uses_demo(client, monkeypatch) -> None:
    email_id = insert_incoming_email(status="pending_analysis")
    monkeypatch.setattr(settings, "gemini_api_key", None)

    response = client.post(f"/api/v1/email/inbox/{email_id}/analyze")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "ai_unavailable"

    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(ai_api, "_rate_limit_state", {})
    monkeypatch.setattr(
        email_api,
        "analyze_message",
        lambda _message: AIAnalyzeResponse(
            order=AIAnalyzedOrder(
                cargo_description="Paczka",
                pickup_location="Warszawa",
                delivery_location="Gdańsk",
            ),
            missing_fields=[],
            ambiguities=[],
            mode="ai",
        ),
    )
    response = client.post(f"/api/v1/email/inbox/{email_id}/analyze")
    assert response.status_code == 200
    assert response.json()["status"] == "converted"
    assert response.json()["analysis"]["mode"] == "ai"
    orders = client.get("/api/v1/orders").json()
    assert len(orders) == 1
    assert orders[0]["cargo_description"] == "Paczka"
    assert orders[0]["status"] == "new"
    assert orders[0]["original_message"] == "Proszę przewieźć paczkę z Warszawy do Gdańska."
    inbox_after_analysis = client.get("/api/v1/email/inbox").json()
    assert len(inbox_after_analysis) == 1
    assert inbox_after_analysis[0]["status"] == "converted"
    assert inbox_after_analysis[0]["converted_order_id"] == orders[0]["id"]


def test_background_analysis_creates_incomplete_order_draft(client, monkeypatch) -> None:
    email_id = insert_incoming_email(
        status="pending_analysis",
        body="Chciałbym przewieźć mebel.",
    )
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(
        email_worker,
        "analyze_message",
        lambda _message: AIAnalyzeResponse(
            order=AIAnalyzedOrder(cargo_description="Mebel"),
            missing_fields=["pickup_location", "delivery_location"],
            ambiguities=[],
            mode="ai",
        ),
    )
    monkeypatch.setattr(email_worker, "SessionLocal", session_factory_for_test())

    assert email_worker.analyze_one_pending_email() is True
    orders = client.get("/api/v1/orders").json()

    assert len(orders) == 1
    order = orders[0]
    assert order["cargo_description"] == "Mebel"
    assert order["pickup_location"] is None
    assert order["delivery_location"] is None
    assert order["original_message"] == "Chciałbym przewieźć mebel."
    assert order["status"] == "new"
    inbox_after_analysis = client.get("/api/v1/email/inbox").json()
    assert len(inbox_after_analysis) == 1
    assert inbox_after_analysis[0]["status"] == "converted"
    assert inbox_after_analysis[0]["converted_order_id"] == order["id"]


def test_background_analysis_without_gemini_keeps_email_pending(client, monkeypatch) -> None:
    email_id = insert_incoming_email(status="pending_analysis")
    monkeypatch.setattr(settings, "gemini_api_key", None)
    monkeypatch.setattr(email_worker, "SessionLocal", session_factory_for_test())

    assert email_worker.analyze_one_pending_email() is False
    assert client.get("/api/v1/orders").json() == []
    assert client.get("/api/v1/email/inbox").json()[0]["id"] == email_id
    assert client.get("/api/v1/email/inbox").json()[0]["status"] == "pending_analysis"


def test_gmail_poll_stores_unread_message_without_exposing_credentials(client, monkeypatch) -> None:
    raw_message = (
        b"From: Customer <customer@example.com>\r\n"
        b"To: company@example.com\r\n"
        b"Message-ID: <incoming-123@example.com>\r\n"
        b"Subject: Transport request\r\n"
        b"Content-Type: text/plain; charset=utf-8\r\n\r\n"
        b"Prosz\xc4\x99 przewie\xc5\xba\xc4\x87 kanap\xc4\x99 z Gda\xc5\x84ska do Gdyni."
    )
    calls: list[tuple[object, ...]] = []

    class FakeMailbox:
        def __init__(self, *_args, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def login(self, username, password):
            calls.append(("login", username, password))

        def select(self, mailbox):
            calls.append(("select", mailbox))
            return "OK", [b"1"]

        def uid(self, operation, *args):
            calls.append((operation, *args))
            if operation == "search":
                return "OK", [b"7"]
            if operation == "fetch":
                return "OK", [(b"7 BODY[]", raw_message)]
            if operation == "store":
                return "OK", [b"stored"]
            raise AssertionError(f"Unexpected IMAP operation: {operation}")

    monkeypatch.setattr(settings, "gmail_address", "company@example.com")
    monkeypatch.setattr(settings, "gmail_app_password", "test-app-password")
    monkeypatch.setattr(email_worker.imaplib, "IMAP4_SSL", FakeMailbox)
    monkeypatch.setattr(email_worker, "SessionLocal", session_factory_for_test())

    assert email_worker.poll_gmail_inbox() == 1
    response = client.get("/api/v1/email/inbox")

    assert response.status_code == 200
    assert response.json()[0]["sender_email"] == "customer@example.com"
    assert response.json()[0]["status"] == "pending_analysis"
    assert "Gdańska do Gdyni" in response.json()[0]["body"]
    assert any(call[0] == "store" and call[-1] == "\\Seen" for call in calls)
    assert calls[0] == ("login", "company@example.com", "test-app-password")


def test_manual_gmail_sync_imports_messages(client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "gmail_address", "company@example.com")
    monkeypatch.setattr(settings, "gmail_app_password", "test-app-password")
    monkeypatch.setattr(email_api, "poll_gmail_inbox", lambda: 2)

    response = client.post("/api/v1/email/inbox/sync")

    assert response.status_code == 200
    assert response.json() == {"imported_count": 2, "analyzed_count": 0}


def test_manual_gmail_sync_analyzes_pending_messages(client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "gmail_address", "company@example.com")
    monkeypatch.setattr(settings, "gmail_app_password", "test-app-password")
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(email_api, "poll_gmail_inbox", lambda: 1)
    monkeypatch.setattr(email_api, "analyze_pending_emails", lambda: 1)

    response = client.post("/api/v1/email/inbox/sync")

    assert response.status_code == 200
    assert response.json() == {"imported_count": 1, "analyzed_count": 1}


def test_manual_gmail_sync_requires_configuration(client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "gmail_address", None)
    monkeypatch.setattr(settings, "gmail_app_password", None)

    response = client.post("/api/v1/email/inbox/sync")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "gmail_not_configured"


def test_manual_gmail_sync_reports_connection_errors_safely(client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "gmail_address", "company@example.com")
    monkeypatch.setattr(settings, "gmail_app_password", "test-app-password")

    def fail_to_poll():
        raise OSError("private connection detail")

    monkeypatch.setattr(email_api, "poll_gmail_inbox", fail_to_poll)

    response = client.post("/api/v1/email/inbox/sync")

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "gmail_sync_failed"
    assert "private connection detail" not in response.text


def test_email_subject_filter_can_be_read_and_saved(client) -> None:
    initial = client.get("/api/v1/email/inbox/filter")
    assert initial.status_code == 200
    assert initial.json() == {"enabled": False, "subject_phrase": ""}

    updated = client.put(
        "/api/v1/email/inbox/filter",
        json={"enabled": True, "subject_phrase": "[CargoBrief]"},
    )
    assert updated.status_code == 200
    assert updated.json() == {"enabled": True, "subject_phrase": "[CargoBrief]"}
    assert client.get("/api/v1/email/inbox/filter").json() == updated.json()


def test_email_subject_filter_requires_phrase_when_enabled(client) -> None:
    response = client.put(
        "/api/v1/email/inbox/filter",
        json={"enabled": True, "subject_phrase": "   "},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_gmail_poll_only_downloads_messages_matching_subject_filter(client, monkeypatch) -> None:
    matching_message = (
        b"From: Customer <customer@example.com>\r\n"
        b"To: company@example.com\r\n"
        b"Message-ID: <matching@example.com>\r\n"
        b"Subject: Re: [CARGOBRIEF] Transport request\r\n"
        b"Content-Type: text/plain; charset=utf-8\r\n\r\n"
        b"Prosz\xc4\x99 przewie\xc5\xba\xc4\x87 kanap\xc4\x99."
    )
    headers = {
        b"21": b"Subject: Re: [CARGOBRIEF] Transport request\r\n\r\n",
        b"22": b"Subject: Family photos\r\n\r\n",
    }
    calls: list[tuple[object, ...]] = []

    class FakeMailbox:
        def __init__(self, *_args, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def login(self, *_args):
            return None

        def select(self, *_args):
            return "OK", [b"1"]

        def uid(self, operation, uid, *args):
            calls.append((operation, uid, *args))
            if operation == "search":
                return "OK", [b"21 22"]
            if operation == "fetch" and "HEADER.FIELDS" in args[0]:
                return "OK", [(b"header", headers[uid.encode()])]
            if operation == "fetch" and uid == "21":
                return "OK", [(b"body", matching_message)]
            if operation == "store":
                return "OK", [b"stored"]
            raise AssertionError(f"Unexpected IMAP operation: {operation}, {uid}, {args}")

    monkeypatch.setattr(settings, "gmail_address", "company@example.com")
    monkeypatch.setattr(settings, "gmail_app_password", "test-app-password")
    monkeypatch.setattr(email_worker.imaplib, "IMAP4_SSL", FakeMailbox)
    monkeypatch.setattr(email_worker, "SessionLocal", session_factory_for_test())
    filter_response = client.put(
        "/api/v1/email/inbox/filter",
        json={"enabled": True, "subject_phrase": "[CargoBrief]"},
    )
    assert filter_response.status_code == 200

    assert email_worker.poll_gmail_inbox() == 1
    imported_emails = client.get("/api/v1/email/inbox").json()
    assert len(imported_emails) == 1
    assert imported_emails[0]["subject"] == "Re: [CARGOBRIEF] Transport request"
    assert not any(call[0] == "fetch" and call[1] == "22" and "BODY.PEEK[]" in call[2] for call in calls)
    assert not any(call[0] == "store" and call[1] == "22" for call in calls)


def test_shipment_outbox_sends_notifications_to_each_customer(client, monkeypatch) -> None:
    order_payload = {
        "cargo_description": "Paczka",
        "length_cm": 100,
        "width_cm": 90,
        "height_cm": 80,
        "weight_kg": 100,
        "quantity": 1,
        "pickup_location": "Warszawa",
        "delivery_location": "Gdańsk",
        "customer_email": "customer@example.com",
    }
    created_order = client.post("/api/v1/orders", json=order_payload).json()
    order_payload["status"] = "approved"
    client.put(f"/api/v1/orders/{created_order['id']}", json=order_payload)
    shipment_response = client.post(
        "/api/v1/shipments",
        json={
            "scheduled_date": "2026-11-18",
            "vehicle_id": 1,
            "order_ids": [created_order["id"]],
        },
    )
    assert shipment_response.status_code == 201
    assert shipment_response.json()["notification_status"] == "not_configured"

    sent_messages = []

    class FakeSMTP:
        def __init__(self, *_args, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def login(self, username, password):
            assert username == "company@example.com"
            assert password == "test-app-password"

        def send_message(self, message):
            sent_messages.append(message)
            return {}

    monkeypatch.setattr(settings, "gmail_address", "company@example.com")
    monkeypatch.setattr(settings, "gmail_app_password", "test-app-password")
    monkeypatch.setattr(email_worker.smtplib, "SMTP_SSL", FakeSMTP)
    monkeypatch.setattr(email_worker, "SessionLocal", session_factory_for_test())

    assert email_worker.process_pending_notifications() == 1
    updated = client.get("/api/v1/shipments").json()[0]
    assert updated["notification_status"] == "sent"
    assert len(sent_messages) == 1
    assert sent_messages[0]["To"] == "customer@example.com"
    assert "2026-11-18" in sent_messages[0].get_content()
