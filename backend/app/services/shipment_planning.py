import re
from dataclasses import dataclass
from datetime import date
from typing import Iterable, Literal

from app.models import TransportOrder, Vehicle


CAPACITY_NOTE = (
    "Pojemność jest przybliżona: suma objętości i wymiary sztuk nie symulują "
    "fizycznego układania ładunków."
)


@dataclass(frozen=True)
class ShipmentEvaluation:
    eligible: bool
    destination: str
    recommended_vehicle: Vehicle | None
    total_weight_kg: float | None
    total_volume_cm3: float | None
    date_conflicts: tuple[int, ...]
    warnings: tuple[str, ...]
    message: str


def normalize_location(location: str) -> str:
    return re.sub(r"\s+", " ", location.strip()).casefold()


def format_address(
    city: str,
    street: str | None = None,
    building_number: str | None = None,
    apartment: str | None = None,
    postal_code: str | None = None,
) -> str:
    street_line = " ".join(
        part for part in (street, building_number) if part
    )
    if apartment:
        street_line = f"{street_line}/{apartment}" if street_line else apartment
    postal_line = " ".join(part for part in (postal_code, city) if part)
    return ", ".join(part for part in (street_line, postal_line) if part)


def format_order_address(
    order: TransportOrder,
    address_type: Literal["pickup", "delivery"],
) -> str:
    if address_type == "pickup":
        return format_address(
            order.pickup_location,
            order.pickup_street,
            order.pickup_building_number,
            order.pickup_apartment,
            order.pickup_postal_code,
        )
    return format_address(
        order.delivery_location,
        order.delivery_street,
        order.delivery_building_number,
        order.delivery_apartment,
        order.delivery_postal_code,
    )


def evaluate_shipment(
    orders: list[TransportOrder],
    vehicles: Iterable[Vehicle],
    scheduled_date: date,
    *,
    vehicle_id: int | None = None,
    confirm_date_override: bool = False,
) -> ShipmentEvaluation:
    destination = format_order_address(orders[0], "delivery") if orders else ""
    date_conflicts = tuple(
        order.id
        for order in orders
        if order.preferred_date is not None and order.preferred_date != scheduled_date
    )

    if not orders:
        return ShipmentEvaluation(
            False, destination, None, None, None, (), (), "Dodaj co najmniej jedno zlecenie."
        )

    normalized_destination = normalize_location(destination)
    if any(
        normalize_location(format_order_address(order, "delivery")) != normalized_destination
        for order in orders[1:]
    ):
        return ShipmentEvaluation(
            False,
            destination,
            None,
            None,
            None,
            date_conflicts,
            (),
            "Wszystkie zlecenia w wysyłce muszą mieć ten sam cel dostawy.",
        )

    if date_conflicts and not confirm_date_override:
        return ShipmentEvaluation(
            False,
            destination,
            None,
            None,
            None,
            date_conflicts,
            (),
            "Preferowane daty części zleceń różnią się od daty wysyłki.",
        )

    total_weight_kg = 0.0
    total_volume_cm3 = 0.0
    missing_order_ids: list[int] = []
    for order in orders:
        if (
            order.length_cm is None
            or order.width_cm is None
            or order.height_cm is None
            or order.weight_kg is None
        ):
            missing_order_ids.append(order.id)
            continue
        total_weight_kg += order.weight_kg * order.quantity
        total_volume_cm3 += (
            order.length_cm * order.width_cm * order.height_cm * order.quantity
        )
    if missing_order_ids:
        return ShipmentEvaluation(
            False,
            destination,
            None,
            None,
            None,
            date_conflicts,
            (),
            "Brakuje wymiarów lub wagi w zleceniach: "
            + ", ".join(f"#{order_id}" for order_id in missing_order_ids)
            + ".",
        )
    vehicles_to_check = [
        vehicle for vehicle in vehicles if vehicle_id is None or vehicle.id == vehicle_id
    ]
    matching_vehicles = [
        vehicle
        for vehicle in vehicles_to_check
        if total_weight_kg <= vehicle.max_payload_kg
        and total_volume_cm3
        <= vehicle.max_length_cm * vehicle.max_width_cm * vehicle.max_height_cm
        and all(
            _order_fits_vehicle(order, vehicle)
            for order in orders
        )
    ]
    if not matching_vehicles:
        return ShipmentEvaluation(
            False,
            destination,
            None,
            total_weight_kg,
            total_volume_cm3,
            date_conflicts,
            (),
            "Wybrany pojazd nie mieści łącznego ładunku albo nie spełnia ograniczeń wymiarów i wagi.",
        )

    recommended_vehicle = min(
        matching_vehicles,
        key=lambda vehicle: (
            vehicle.max_length_cm * vehicle.max_width_cm * vehicle.max_height_cm,
            vehicle.max_payload_kg,
            vehicle.name,
        ),
    )
    pickup_locations = {
        normalize_location(format_order_address(order, "pickup")) for order in orders
    }
    warnings = [CAPACITY_NOTE]
    if len(pickup_locations) > 1:
        warnings.append(
            "Wysyłka ma wiele miejsc odbioru; kolejność przystanków nie jest optymalizowana."
        )
    if date_conflicts:
        warnings.append(
            "Pracownik potwierdził ręczne nadpisanie preferowanych dat w zleceniach: "
            + ", ".join(f"#{order_id}" for order_id in date_conflicts)
            + "."
        )

    return ShipmentEvaluation(
        True,
        destination,
        recommended_vehicle,
        total_weight_kg,
        total_volume_cm3,
        date_conflicts,
        tuple(warnings),
        f"Zlecenia mogą jechać razem pojazdem {recommended_vehicle.name}.",
    )


def _order_fits_vehicle(order: TransportOrder, vehicle: Vehicle) -> bool:
    if order.length_cm is None or order.width_cm is None or order.height_cm is None:
        return False
    cargo_dimensions = sorted(
        (order.length_cm, order.width_cm, order.height_cm)
    )
    vehicle_dimensions = sorted(
        (vehicle.max_length_cm, vehicle.max_width_cm, vehicle.max_height_cm)
    )
    return all(
        cargo_dimension <= vehicle_dimension
        for cargo_dimension, vehicle_dimension in zip(
            cargo_dimensions,
            vehicle_dimensions,
        )
    )
