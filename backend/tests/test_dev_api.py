from app.config import settings


def test_dev_status_reports_database_and_tables_without_secrets(client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "gemini_api_key", "private-gemini-key")
    monkeypatch.setattr(settings, "gmail_address", "dev@example.com")
    monkeypatch.setattr(settings, "gmail_app_password", "private-mail-password")

    response = client.get("/api/v1/dev/status")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"]["connected"] is True
    assert data["database"]["dialect"] == "sqlite"
    assert data["tables"]
    assert data["integrations"] == {"gemini": True, "gmail": True}
    assert "private-gemini-key" not in response.text
    assert "private-mail-password" not in response.text


def test_dev_table_clearing_is_disabled_by_default(client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "dev_tools_enabled", False)

    response = client.post(
        "/api/v1/dev/tables/vehicles/clear",
        json={"confirm_table_name": "vehicles"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "dev_tools_disabled"


def test_dev_can_clear_one_confirmed_unreferenced_table(client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "dev_tools_enabled", True)

    response = client.post(
        "/api/v1/dev/tables/vehicles/clear",
        json={"confirm_table_name": "vehicles"},
    )

    assert response.status_code == 200
    assert response.json() == {"table_name": "vehicles", "deleted_count": 3}
    status_response = client.get("/api/v1/dev/status")
    vehicles = next(table for table in status_response.json()["tables"] if table["name"] == "vehicles")
    assert vehicles["row_count"] == 0


def test_dev_clear_requires_exact_name_and_protects_migrations(client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "dev_tools_enabled", True)

    mismatch_response = client.post(
        "/api/v1/dev/tables/vehicles/clear",
        json={"confirm_table_name": "vehicle"},
    )
    migration_response = client.post(
        "/api/v1/dev/tables/alembic_version/clear",
        json={"confirm_table_name": "alembic_version"},
    )

    assert mismatch_response.status_code == 400
    assert mismatch_response.json()["error"]["code"] == "confirmation_mismatch"
    assert migration_response.status_code == 404
    assert migration_response.json()["error"]["code"] == "table_not_clearable"


def test_dev_clear_prevents_orphaning_referenced_rows(client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "dev_tools_enabled", True)
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

    response = client.post(
        "/api/v1/dev/tables/vehicles/clear",
        json={"confirm_table_name": "vehicles"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "table_has_references"
