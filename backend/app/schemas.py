from datetime import date, datetime, time, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationInfo, field_validator


PositiveFloat = Annotated[float, Field(gt=0, allow_inf_nan=False)]
NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
OrderStatus = Literal["new", "in_review", "approved"]
CustomerEmail = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=3,
        max_length=254,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    ),
]
AddressStreet = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
AddressNumber = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=30),
]
PostalCode = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=20),
]
CustomerPhone = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=6,
        max_length=32,
        pattern=r"^[+0-9][0-9 ()-]*$",
    ),
]


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
    pickup_street: AddressStreet | None = None
    pickup_building_number: AddressNumber | None = None
    pickup_apartment: AddressNumber | None = None
    pickup_postal_code: PostalCode | None = None
    delivery_street: AddressStreet | None = None
    delivery_building_number: AddressNumber | None = None
    delivery_apartment: AddressNumber | None = None
    delivery_postal_code: PostalCode | None = None
    customer_phone: CustomerPhone | None = None
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
    pickup_street: AddressStreet | None = None
    pickup_building_number: AddressNumber | None = None
    pickup_apartment: AddressNumber | None = None
    pickup_postal_code: PostalCode | None = None
    delivery_street: AddressStreet | None = None
    delivery_building_number: AddressNumber | None = None
    delivery_apartment: AddressNumber | None = None
    delivery_postal_code: PostalCode | None = None
    preferred_date: date | None = None
    preferred_time: time | None = None
    pickup_floor: int | None = Field(default=None, ge=-5, le=100)
    delivery_floor: int | None = Field(default=None, ge=-5, le=100)
    pickup_has_elevator: bool | None = None
    delivery_has_elevator: bool | None = None
    notes: Annotated[str, StringConstraints(max_length=1000)] | None = None
    original_message: Annotated[str, StringConstraints(max_length=3000)] | None = None
    customer_email: CustomerEmail | None = None
    customer_phone: CustomerPhone | None = None


class TransportOrderCreate(TransportOrderInput):
    pass


class TransportOrderUpdate(TransportOrderInput):
    cargo_description: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
    ] | None = None
    pickup_location: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
    ] | None = None
    delivery_location: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
    ] | None = None
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
    cargo_description: str | None
    length_cm: float | None
    width_cm: float | None
    height_cm: float | None
    weight_kg: float | None
    quantity: int
    pickup_location: str | None
    delivery_location: str | None
    pickup_street: str | None
    pickup_building_number: str | None
    pickup_apartment: str | None
    pickup_postal_code: str | None
    delivery_street: str | None
    delivery_building_number: str | None
    delivery_apartment: str | None
    delivery_postal_code: str | None
    preferred_date: date | None
    preferred_time: time | None
    pickup_floor: int | None
    delivery_floor: int | None
    pickup_has_elevator: bool | None
    delivery_has_elevator: bool | None
    notes: str | None
    original_message: str | None
    customer_email: str | None
    customer_phone: str | None
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


class ShipmentCreate(BaseModel):
    scheduled_date: date
    vehicle_id: int = Field(gt=0)
    order_ids: list[int] = Field(min_length=1, max_length=50)
    confirm_date_override: bool = False

    model_config = ConfigDict(extra="forbid")

    @field_validator("order_ids")
    @classmethod
    def order_ids_must_be_unique(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            raise ValueError("Id zleceń nie mogą się powtarzać.")
        return value


class ShipmentSuggestInput(BaseModel):
    scheduled_date: date
    order_ids: list[int] = Field(min_length=1, max_length=20)

    model_config = ConfigDict(extra="forbid")

    @field_validator("order_ids")
    @classmethod
    def order_ids_must_be_unique(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            raise ValueError("Id zleceń nie mogą się powtarzać.")
        return value


class ShipmentOrderGroup(BaseModel):
    order_ids: list[int] = Field(min_length=1, max_length=20)
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]

    model_config = ConfigDict(extra="forbid")

    @field_validator("order_ids")
    @classmethod
    def order_ids_must_be_unique(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            raise ValueError("Id zleceń w grupie nie mogą się powtarzać.")
        return value


class AIShipmentSuggestions(BaseModel):
    groups: list[ShipmentOrderGroup] = Field(max_length=20)

    model_config = ConfigDict(extra="forbid")


class ShipmentSuggestionGroup(BaseModel):
    order_ids: list[int]
    destination: str
    eligible: bool
    recommended_vehicle: VehicleRead | None
    total_weight_kg: float | None
    total_volume_cm3: float | None
    date_conflicts: list[int]
    warnings: list[str]
    message: str


class ShipmentSuggestionsResponse(BaseModel):
    mode: Literal["ai", "demo"]
    groups: list[ShipmentSuggestionGroup]


class ShipmentRead(BaseModel):
    id: int
    scheduled_date: date
    destination: str
    vehicle: VehicleRead
    orders: list[TransportOrderRead]
    total_weight_kg: float
    total_volume_cm3: float
    warnings: list[str]
    notification_status: Literal["pending", "sending", "sent", "failed", "not_configured"]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("created_at")
    @classmethod
    def normalize_created_at_to_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class IncomingEmailRead(BaseModel):
    id: int
    sender_email: str | None
    subject: str
    body: str
    status: Literal["pending_analysis", "ready", "converted"]
    analysis: AIAnalyzeResponse | None
    converted_order_id: int | None
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def normalize_created_at_to_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class EmailSyncResult(BaseModel):
    imported_count: int = Field(ge=0)
    analyzed_count: int = Field(ge=0)


class EmailInboxFilterRead(BaseModel):
    enabled: bool
    subject_phrase: str


class EmailInboxFilterUpdate(BaseModel):
    enabled: bool
    subject_phrase: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]

    model_config = ConfigDict(extra="forbid")

    @field_validator("subject_phrase")
    @classmethod
    def enabled_filter_requires_phrase(cls, value: str, info: ValidationInfo) -> str:
        if info.data.get("enabled") and not value:
            raise ValueError("Wpisz frazę tematu albo wyłącz filtr.")
        return value


class DevTableInfo(BaseModel):
    name: str
    row_count: int | None
    exists: bool
    clearable: bool


class DevDatabaseStatus(BaseModel):
    connected: bool
    dialect: str
    location: str
    current_revision: str | None
    head_revision: str | None
    migration_status: Literal["unknown", "not_initialized", "up_to_date", "pending"]


class DevErrorInfo(BaseModel):
    timestamp: str
    level: str
    logger: str


class DevDiagnostics(BaseModel):
    status: Literal["ok"]
    app_name: str
    app_version: str
    python_version: str
    clear_enabled: bool
    database: DevDatabaseStatus
    tables: list[DevTableInfo]
    integrations: dict[str, bool]
    recent_errors: list[DevErrorInfo]


class DevTableClearRequest(BaseModel):
    confirm_table_name: NonEmptyString

    model_config = ConfigDict(extra="forbid")


class DevTableClearResult(BaseModel):
    table_name: str
    deleted_count: int = Field(ge=0)
