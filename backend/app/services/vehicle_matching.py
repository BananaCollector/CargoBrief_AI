from dataclasses import dataclass
from typing import Iterable, Literal

from app.models import Vehicle


MatchStatus = Literal["confirmed", "missing_data", "no_match"]

SIMULATION_NOTE = (
    "Uproszczona symulacja: nie uwzględnia pakowania wielu sztuk "
    "ani rzeczywistych ograniczeń transportu."
)


@dataclass(frozen=True)
class VehicleMatchResult:
    status: MatchStatus
    recommended_vehicle: Vehicle | None
    total_weight_kg: float | None
    missing_fields: tuple[str, ...]
    message: str
    simulation_note: str = SIMULATION_NOTE


def match_vehicle(
    *,
    length_cm: float | None,
    width_cm: float | None,
    height_cm: float | None,
    weight_kg: float | None,
    quantity: int,
    vehicles: Iterable[Vehicle],
) -> VehicleMatchResult:
    dimensions = {
        "length_cm": length_cm,
        "width_cm": width_cm,
        "height_cm": height_cm,
    }
    missing_fields = tuple(
        field for field, value in dimensions.items() if value is None
    )
    if weight_kg is None:
        missing_fields += ("weight_kg",)

    if missing_fields:
        return VehicleMatchResult(
            status="missing_data",
            recommended_vehicle=None,
            total_weight_kg=None,
            missing_fields=missing_fields,
            message="Niepotwierdzone dopasowanie: brakuje wymiarów ładunku lub jego wagi.",
        )

    cargo_dimensions = sorted(
        (length_cm, width_cm, height_cm)
    )
    total_weight_kg = weight_kg * quantity
    matching_vehicles = [
        vehicle
        for vehicle in vehicles
        if total_weight_kg <= vehicle.max_payload_kg
        and all(
            cargo_dimension <= vehicle_dimension
            for cargo_dimension, vehicle_dimension in zip(
                cargo_dimensions,
                sorted(
                    (
                        vehicle.max_length_cm,
                        vehicle.max_width_cm,
                        vehicle.max_height_cm,
                    )
                ),
            )
        )
    ]

    if not matching_vehicles:
        return VehicleMatchResult(
            status="no_match",
            recommended_vehicle=None,
            total_weight_kg=total_weight_kg,
            missing_fields=(),
            message="Żaden dostępny pojazd nie spełnia wymagań ładunku.",
        )

    recommended_vehicle = min(
        matching_vehicles,
        key=lambda vehicle: (
            vehicle.max_length_cm * vehicle.max_width_cm * vehicle.max_height_cm,
            vehicle.max_payload_kg,
            vehicle.name,
        ),
    )
    return VehicleMatchResult(
        status="confirmed",
        recommended_vehicle=recommended_vehicle,
        total_weight_kg=total_weight_kg,
        missing_fields=(),
        message=f"Rekomendowany pojazd: {recommended_vehicle.name}.",
    )
