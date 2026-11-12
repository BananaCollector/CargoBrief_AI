def order_payload() -> dict[str, object]:
    return {
        "cargo_description": "Kanapa",
        "length_cm": 220,
        "width_cm": 90,
        "height_cm": 85,
        "weight_kg": 250,
        "quantity": 1,
        "pickup_location": "Warszawa",
        "delivery_location": "Kraków",
        "preferred_date": "2026-11-15",
        "preferred_time": "12:30:00",
        "pickup_floor": 2,
        "delivery_floor": 0,
        "pickup_has_elevator": True,
        "delivery_has_elevator": None,
        "notes": "Kontakt przed przyjazdem",
        "original_message": "Proszę przewieźć kanapę.",
    }


def test_order_can_be_created_listed_read_updated_and_deleted(client) -> None:
    create_response = client.post("/api/v1/orders", json=order_payload())

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["cargo_description"] == "Kanapa"
    assert created["status"] == "new"
    assert created["created_at"].endswith("Z")
    assert created["updated_at"].endswith("Z")
    assert created["match"]["status"] == "confirmed"
    assert created["match"]["recommended_vehicle"]["name"] == "Van L2H2"

    order_id = created["id"]
    list_response = client.get("/api/v1/orders")
    assert list_response.status_code == 200
    assert [order["id"] for order in list_response.json()] == [order_id]

    read_response = client.get(f"/api/v1/orders/{order_id}")
    assert read_response.status_code == 200
    assert read_response.json()["pickup_location"] == "Warszawa"

    update_payload = order_payload()
    update_payload["status"] = "in_review"
    update_payload["notes"] = "Potwierdzić windę."
    update_response = client.put(
        f"/api/v1/orders/{order_id}",
        json=update_payload,
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "in_review"
    assert update_response.json()["notes"] == "Potwierdzić windę."

    delete_response = client.delete(f"/api/v1/orders/{order_id}")
    assert delete_response.status_code == 204
    assert client.get(f"/api/v1/orders/{order_id}").status_code == 404


def test_missing_order_returns_consistent_not_found_error(client) -> None:
    response = client.get("/api/v1/orders/999")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "order_not_found",
            "message": "Nie znaleziono zlecenia.",
        }
    }


def test_invalid_order_returns_consistent_validation_error(client) -> None:
    response = client.post("/api/v1/orders", json={"cargo_description": "Kanapa"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_order_rejects_out_of_range_floor(client) -> None:
    payload = order_payload()
    payload["pickup_floor"] = 101

    response = client.post("/api/v1/orders", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_order_rejects_unknown_fields(client) -> None:
    payload = order_payload()
    payload["unexpected"] = "value"

    response = client.post("/api/v1/orders", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
