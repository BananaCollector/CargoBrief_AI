from datetime import date, datetime, time, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Vehicle(Base):
    __tablename__ = "vehicles"
    __table_args__ = (
        CheckConstraint("max_length_cm > 0", name="ck_vehicles_length_positive"),
        CheckConstraint("max_width_cm > 0", name="ck_vehicles_width_positive"),
        CheckConstraint("max_height_cm > 0", name="ck_vehicles_height_positive"),
        CheckConstraint("max_payload_kg > 0", name="ck_vehicles_payload_positive"),
        UniqueConstraint("name", name="uq_vehicles_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    max_length_cm: Mapped[float] = mapped_column(Float, nullable=False)
    max_width_cm: Mapped[float] = mapped_column(Float, nullable=False)
    max_height_cm: Mapped[float] = mapped_column(Float, nullable=False)
    max_payload_kg: Mapped[float] = mapped_column(Float, nullable=False)


class TransportOrder(Base):
    __tablename__ = "transport_orders"
    __table_args__ = (
        CheckConstraint("length_cm IS NULL OR length_cm > 0", name="ck_orders_length_positive"),
        CheckConstraint("width_cm IS NULL OR width_cm > 0", name="ck_orders_width_positive"),
        CheckConstraint("height_cm IS NULL OR height_cm > 0", name="ck_orders_height_positive"),
        CheckConstraint("weight_kg IS NULL OR weight_kg > 0", name="ck_orders_weight_positive"),
        CheckConstraint("quantity >= 1", name="ck_orders_quantity_positive"),
        CheckConstraint(
            "pickup_floor IS NULL OR pickup_floor BETWEEN -5 AND 100",
            name="ck_orders_pickup_floor_range",
        ),
        CheckConstraint(
            "delivery_floor IS NULL OR delivery_floor BETWEEN -5 AND 100",
            name="ck_orders_delivery_floor_range",
        ),
        CheckConstraint(
            "status IN ('new', 'in_review', 'approved')",
            name="ck_orders_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cargo_description: Mapped[str] = mapped_column(String(200), nullable=False)
    length_cm: Mapped[float | None] = mapped_column(Float)
    width_cm: Mapped[float | None] = mapped_column(Float)
    height_cm: Mapped[float | None] = mapped_column(Float)
    weight_kg: Mapped[float | None] = mapped_column(Float)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    pickup_location: Mapped[str] = mapped_column(String(255), nullable=False)
    delivery_location: Mapped[str] = mapped_column(String(255), nullable=False)
    preferred_date: Mapped[date | None] = mapped_column(Date)
    preferred_time: Mapped[time | None] = mapped_column(Time)
    pickup_floor: Mapped[int | None] = mapped_column(Integer)
    delivery_floor: Mapped[int | None] = mapped_column(Integer)
    pickup_has_elevator: Mapped[bool | None] = mapped_column(Boolean)
    delivery_has_elevator: Mapped[bool | None] = mapped_column(Boolean)
    notes: Mapped[str | None] = mapped_column(Text)
    original_message: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="new",
        server_default="new",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
