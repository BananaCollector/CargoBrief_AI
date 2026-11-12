from datetime import date, datetime, time, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator


PositiveFloat = Annotated[float, Field(gt=0, allow_inf_nan=False)]
NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
OrderStatus = Literal["new", "in_review", "approved"]


class CargoMatchFields(BaseModel):
    length_cm: PositiveFloat | None = None
    width_cm: PositiveFloat | None = None
    height_cm: PositiveFloat | None = None
    weight_kg: PositiveFloat | None = None
    quantity: int = Field(default=1, ge=1)

    model_config = ConfigDict(extra="forbid")


class VehicleMatchInput(CargoMatchFields):
    pass


class AIAnalyzeInput(BaseModel):
    message: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=3000)
    ]

    model_config = ConfigDict(extra="forbid")


class AIAnalyzedOrder(BaseModel):
    cargo_description: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
    ] | None = None
    length_cm: PositiveFloat | None = None
    width_cm: PositiveFloat | None = None
    height_cm: PositiveFloat | None = None
    weight_kg: PositiveFloat | None = None
    quantity: int | None = Field(default=None, ge=1)
    pickup_location: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
    ] | None = None
    delivery_location: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
    ] | None = None
    preferred_date: date | None = None
    preferred_time: time | None = None
    pickup_floor: int | None = Field(default=None, ge=-5, le=100)
    delivery_floor: int | None = Field(default=None, ge=-5, le=100)
    pickup_has_elevator: bool | None = None
    delivery_has_elevator: bool | None = None
    notes: Annotated[str, StringConstraints(max_length=1000)] | None = None
    original_message: Annotated[
        str, StringConstraints(max_length=3000)
    ] | None = None

    model_config = ConfigDict(extra="forbid")


class AIModelAnalysis(BaseModel):
    order: AIAnalyzedOrder
    ambiguities: list[Annotated[str, StringConstraints(min_length=1, max_length=500)]] = Field(
        default_factory=list,
        max_length=10,
    )

    model_config = ConfigDict(extra="forbid")


class AIAnalyzeResponse(BaseModel):
    order: AIAnalyzedOrder
    missing_fields: list[str]
    ambiguities: list[str]
    mode: Literal["ai", "demo"]


class TransportOrderInput(CargoMatchFields):
    cargo_description: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
    ]
    pickup_location: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
    ]
    delivery_location: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
    ]
    preferred_date: date | None = None
    preferred_time: time | None = None
    pickup_floor: int | None = Field(default=None, ge=-5, le=100)
    delivery_floor: int | None = Field(default=None, ge=-5, le=100)
    pickup_has_elevator: bool | None = None
    delivery_has_elevator: bool | None = None
    notes: Annotated[str, StringConstraints(max_length=1000)] | None = None
    original_message: Annotated[str, StringConstraints(max_length=3000)] | None = None


class TransportOrderCreate(TransportOrderInput):
    pass


class TransportOrderUpdate(TransportOrderInput):
    status: OrderStatus | None = None


class VehicleRead(BaseModel):
    id: int
    name: str
    max_length_cm: float
    max_width_cm: float
    max_height_cm: float
    max_payload_kg: float

    model_config = ConfigDict(from_attributes=True)


class VehicleMatchResponse(BaseModel):
    status: Literal["confirmed", "missing_data", "no_match"]
    recommended_vehicle: VehicleRead | None
    total_weight_kg: float | None
    missing_fields: list[str]
    message: str
    simulation_note: str

    model_config = ConfigDict(from_attributes=True)


class TransportOrderRead(BaseModel):
    id: int
    cargo_description: str
    length_cm: float | None
    width_cm: float | None
    height_cm: float | None
    weight_kg: float | None
    quantity: int
    pickup_location: str
    delivery_location: str
    preferred_date: date | None
    preferred_time: time | None
    pickup_floor: int | None
    delivery_floor: int | None
    pickup_has_elevator: bool | None
    delivery_has_elevator: bool | None
    notes: str | None
    original_message: str | None
    status: OrderStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("created_at", "updated_at")
    @classmethod
    def normalize_timestamp_to_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class TransportOrderDetail(TransportOrderRead):
    match: VehicleMatchResponse
