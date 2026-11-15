from copy import deepcopy

from app.api import ai as ai_api
from app.services import ai_analyzer


def create_approved_order(
    client,
    *,
    pickup_location: str = "Warszawa",
    delivery_location: str = "Gdańsk",
    preferred_date: str | None = None,
    original_message: str = "Proszę przewieźć paczkę.",
    length_cm: float = 100,
    width_cm: float = 90,
    height_cm: float = 80,
    weight_kg: float = 100,
    delivery_street: str | None = None,
    delivery_building_number: str | None = None,
    delivery_postal_code: str | None = None,
) -> tuple[int, dict[str, object]]:
    payload: dict[str, object] = {
        "cargo_description": "Paczka",
        "length_cm": length_cm,
        "width_cm": width_cm,
        "height_cm": height_cm,
        "weight_kg": weight_kg,
        "quantity": 1,
        "pickup_location": pickup_location,
        "delivery_location": delivery_location,
        "delivery_street": delivery_street,
        "delivery_building_number": delivery_building_number,
        "delivery_postal_code": delivery_postal_code,
        "preferred_date": preferred_date,
        "original_message": original_message,
        "customer_email": "customer@example.com",
    }
    created = client.post("/api/v1/orders", json=payload)
    assert created.status_code == 201
    order_id = created.json()["id"]

    approved_payload = deepcopy(payload)
    approved_payload["status"] = "approved"
    approved = client.put(f"/api/v1/orders/{order_id}", json=approved_payload)
    assert approved.status_code == 200
    return order_id, approved_payload


def test_shipment_groups_approved_orders_and_reports_capacity(client) -> None:
    first_id, _ = create_approved_order(client, pickup_location="Warszawa")
    second_id, _ = create_approved_order(
        client,
        pickup_location="Poznań",
        delivery_location="  GDAŃSK  ",
    )
    available_response = client.get("/api/v1/shipments/available-orders")
    assert {order["id"] for order in available_response.json()} == {first_id, second_id}

    response = client.post(
        "/api/v1/shipments",
        json={
            "scheduled_date": "2026-11-18",
            "vehicle_id": 1,
            "order_ids": [first_id, second_id],
        },
    )

    assert response.status_code == 201
    shipment = response.json()
    assert shipment["destination"] == "Gdańsk"
    assert shipment["vehicle"]["name"] == "Van S"
    assert [order["id"] for order in shipment["orders"]] == [first_id, second_id]
    assert shipment["total_weight_kg"] == 200
    assert shipment["total_volume_cm3"] == 1_440_000
    assert any("wiele miejsc odbioru" in warning for warning in shipment["warnings"])
    assert client.get("/api/v1/shipments").json()[0]["id"] == shipment["id"]
    assert client.get("/api/v1/shipments/available-orders").json() == []


def test_shipment_requires_matching_full_delivery_address(client) -> None:
    first_id, _ = create_approved_order(
        client,
        delivery_street="Długa",
        delivery_building_number="10",
        delivery_postal_code="80-831",
    )
    second_id, _ = create_approved_order(
        client,
        delivery_street="Floriańska",
        delivery_building_number="12",
        delivery_postal_code="31-021",
    )

    response = client.post(
        "/api/v1/shipments",
        json={
            "scheduled_date": "2026-11-18",
            "vehicle_id": 1,
            "order_ids": [first_id, second_id],
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "shipment_not_eligible"


def test_shipment_displays_full_delivery_address(client) -> None:
    order_id, _ = create_approved_order(
        client,
        delivery_street="Długa",
        delivery_building_number="10",
        delivery_postal_code="80-831",
    )

    response = client.post(
        "/api/v1/shipments",
        json={
            "scheduled_date": "2026-11-18",
            "vehicle_id": 1,
            "order_ids": [order_id],
        },
    )

    assert response.status_code == 201
    assert response.json()["destination"] == "Długa 10, 80-831 Gdańsk"


def test_shipment_requires_approved_orders_and_one_destination(client) -> None:
    unapproved = client.post(
        "/api/v1/orders",
        json={
            "cargo_description": "Paczka",
            "pickup_location": "Warszawa",
            "delivery_location": "Gdańsk",
        },
    ).json()["id"]
    response = client.post(
        "/api/v1/shipments",
        json={"scheduled_date": "2026-11-18", "vehicle_id": 1, "order_ids": [unapproved]},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "order_not_approved"

    first_id, _ = create_approved_order(client, delivery_location="Gdańsk")
    second_id, _ = create_approved_order(client, delivery_location="Sopot")
    response = client.post(
        "/api/v1/shipments",
        json={
            "scheduled_date": "2026-11-18",
            "vehicle_id": 1,
            "order_ids": [first_id, second_id],
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "shipment_not_eligible"


def test_shipment_requires_a_valid_email_for_every_customer(client) -> None:
    order_id, order_payload = create_approved_order(client)
    order_payload["customer_email"] = None
    update = client.put(f"/api/v1/orders/{order_id}", json=order_payload)
    assert update.status_code == 200

    response = client.post(
        "/api/v1/shipments",
        json={
            "scheduled_date": "2026-11-18",
            "vehicle_id": 1,
            "order_ids": [order_id],
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "customer_email_required"


def test_date_conflicts_need_employee_confirmation(client) -> None:
    order_id, _ = create_approved_order(
        client,
        preferred_date="2026-11-18",
    )
    payload = {
        "scheduled_date": "2026-11-19",
        "vehicle_id": 1,
        "order_ids": [order_id],
    }

    response = client.post("/api/v1/shipments", json=payload)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "shipment_date_conflict"

    payload["confirm_date_override"] = True
    response = client.post("/api/v1/shipments", json=payload)
    assert response.status_code == 201
    assert any("nadpisanie" in warning for warning in response.json()["warnings"])


def test_total_volume_is_checked_and_assigned_orders_are_locked(client) -> None:
    first_id, first_payload = create_approved_order(
        client,
        length_cm=180,
        width_cm=115,
        height_cm=115,
    )
    second_id, _ = create_approved_order(
        client,
        length_cm=180,
        width_cm=115,
        height_cm=115,
    )
    response = client.post(
        "/api/v1/shipments",
        json={
            "scheduled_date": "2026-11-18",
            "vehicle_id": 1,
            "order_ids": [first_id, second_id],
        },
    )
    assert response.status_code == 422

    response = client.post(
        "/api/v1/shipments",
        json={
            "scheduled_date": "2026-11-18",
            "vehicle_id": 2,
            "order_ids": [first_id, second_id],
        },
    )
    assert response.status_code == 201

    update_response = client.put(f"/api/v1/orders/{first_id}", json=first_payload)
    delete_response = client.delete(f"/api/v1/orders/{first_id}")
    assert update_response.status_code == 409
    assert delete_response.status_code == 409

    delete_shipment = client.delete(f"/api/v1/shipments/{response.json()['id']}")
    assert delete_shipment.status_code == 204
    assert client.delete(f"/api/v1/orders/{first_id}").status_code == 204


def test_demo_suggestions_are_checked_by_backend(client, monkeypatch) -> None:
    first_id, _ = create_approved_order(
        client,
        preferred_date="2026-11-19",
    )
    second_id, _ = create_approved_order(
        client,
        pickup_location="Poznań",
        preferred_date="2026-11-20",
    )
    monkeypatch.setattr(ai_analyzer.settings, "gemini_api_key", None)

    response = client.post(
        "/api/v1/shipments/suggest",
        json={
            "scheduled_date": "2026-11-21",
            "order_ids": [first_id, second_id],
        },
    )

    assert response.status_code == 200
    suggestion = response.json()
    assert suggestion["mode"] == "demo"
    assert suggestion["groups"][0]["eligible"] is True
    assert suggestion["groups"][0]["order_ids"] == [first_id, second_id]
    assert suggestion["groups"][0]["date_conflicts"] == [first_id, second_id]


def test_ai_suggestions_only_receive_minimized_order_data(client, monkeypatch) -> None:
    first_id, _ = create_approved_order(
        client,
        original_message="PRIVATE MESSAGE THAT MUST NOT REACH AI",
    )
    second_id, _ = create_approved_order(client, pickup_location="Poznań")
    recorded: dict[str, object] = {}

    class FakeInteractions:
        def create(self, **kwargs):
            recorded.update(kwargs)
            return type(
                "Response",
                (),
                {
                    "output_text": (
                        f'{{"groups":[{{"order_ids":[{first_id},{second_id}],'
                        '"reason":"Wspólny cel i termin."}]}'
                    )
                },
            )()

    class FakeClient:
        interactions = FakeInteractions()

        def __init__(self, **kwargs):
            recorded["client_options"] = kwargs

        def close(self):
            recorded["closed"] = True

    monkeypatch.setattr(ai_analyzer.settings, "gemini_api_key", "test-secret")
    monkeypatch.setattr(ai_analyzer.settings, "gemini_model", "test-model")
    monkeypatch.setattr(ai_analyzer.genai, "Client", FakeClient)
    monkeypatch.setattr(ai_api, "_rate_limit_state", {})

    response = client.post(
        "/api/v1/shipments/suggest",
        json={
            "scheduled_date": "2026-11-18",
            "order_ids": [first_id, second_id],
        },
    )

    assert response.status_code == 200
    assert response.json()["mode"] == "ai"
    assert response.json()["groups"][0]["eligible"] is True
    assert "PRIVATE MESSAGE THAT MUST NOT REACH AI" not in recorded["input"]
    assert recorded["model"] == "test-model"
    assert recorded["closed"] is True
