def test_vehicle_list_contains_seeded_fleet(client) -> None:
    response = client.get("/api/v1/vehicles")

    assert response.status_code == 200
    assert [vehicle["name"] for vehicle in response.json()] == [
        "Van S",
        "Van L2H2",
        "Van XL",
    ]


def test_vehicle_match_endpoint_returns_recommendation(client) -> None:
    response = client.post(
        "/api/v1/vehicles/match",
        json={
            "length_cm": 220,
            "width_cm": 90,
            "height_cm": 85,
            "weight_kg": 250,
        },
    )

    assert response.status_code == 200
    assert response.json()["recommended_vehicle"]["name"] == "Van L2H2"


def test_vehicle_match_endpoint_reports_missing_data(client) -> None:
    response = client.post(
        "/api/v1/vehicles/match",
        json={"length_cm": 220, "weight_kg": 250},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "missing_data"
    assert response.json()["recommended_vehicle"] is None
