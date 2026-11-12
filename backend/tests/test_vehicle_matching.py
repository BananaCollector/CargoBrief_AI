from app.models import Vehicle
from app.services.vehicle_matching import match_vehicle


def make_vehicles() -> list[Vehicle]:
    return [
        Vehicle(
            id=1,
            name="Van S",
            max_length_cm=180,
            max_width_cm=115,
            max_height_cm=115,
            max_payload_kg=600,
        ),
        Vehicle(
            id=2,
            name="Van L2H2",
            max_length_cm=340,
            max_width_cm=170,
            max_height_cm=190,
            max_payload_kg=1000,
        ),
        Vehicle(
            id=3,
            name="Van XL",
            max_length_cm=420,
            max_width_cm=175,
            max_height_cm=210,
            max_payload_kg=1400,
        ),
    ]


def test_sofa_fits_van_l2h2_but_not_van_s() -> None:
    result = match_vehicle(
        length_cm=220,
        width_cm=90,
        height_cm=85,
        weight_kg=250,
        quantity=1,
        vehicles=make_vehicles(),
    )

    assert result.status == "confirmed"
    assert result.recommended_vehicle is not None
    assert result.recommended_vehicle.name == "Van L2H2"
    assert result.simulation_note


def test_load_can_be_rotated_to_fit_the_smallest_van() -> None:
    result = match_vehicle(
        length_cm=100,
        width_cm=160,
        height_cm=110,
        weight_kg=100,
        quantity=1,
        vehicles=make_vehicles(),
    )

    assert result.status == "confirmed"
    assert result.recommended_vehicle is not None
    assert result.recommended_vehicle.name == "Van S"


def test_total_weight_is_weight_per_item_times_quantity() -> None:
    result = match_vehicle(
        length_cm=100,
        width_cm=90,
        height_cm=80,
        weight_kg=400,
        quantity=3,
        vehicles=make_vehicles(),
    )

    assert result.status == "confirmed"
    assert result.total_weight_kg == 1200
    assert result.recommended_vehicle is not None
    assert result.recommended_vehicle.name == "Van XL"


def test_excess_total_weight_returns_no_match() -> None:
    result = match_vehicle(
        length_cm=100,
        width_cm=90,
        height_cm=80,
        weight_kg=500,
        quantity=3,
        vehicles=make_vehicles(),
    )

    assert result.status == "no_match"
    assert result.recommended_vehicle is None
    assert result.total_weight_kg == 1500


def test_oversized_cargo_returns_no_match() -> None:
    result = match_vehicle(
        length_cm=500,
        width_cm=200,
        height_cm=150,
        weight_kg=100,
        quantity=1,
        vehicles=make_vehicles(),
    )

    assert result.status == "no_match"
    assert result.recommended_vehicle is None
    assert "Żaden dostępny pojazd" in result.message


def test_missing_dimensions_return_unconfirmed_without_recommendation() -> None:
    result = match_vehicle(
        length_cm=220,
        width_cm=None,
        height_cm=85,
        weight_kg=250,
        quantity=1,
        vehicles=make_vehicles(),
    )

    assert result.status == "missing_data"
    assert result.recommended_vehicle is None
    assert result.missing_fields == ("width_cm",)


def test_missing_weight_returns_unconfirmed_without_recommendation() -> None:
    result = match_vehicle(
        length_cm=220,
        width_cm=90,
        height_cm=85,
        weight_kg=None,
        quantity=1,
        vehicles=make_vehicles(),
    )

    assert result.status == "missing_data"
    assert result.recommended_vehicle is None
    assert result.missing_fields == ("weight_kg",)
