from datetime import date, datetime, time, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
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
        UniqueConstraint("source_email_id", name="uq_orders_source_email_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cargo_description: Mapped[str | None] = mapped_column(String(200))
    length_cm: Mapped[float | None] = mapped_column(Float)
    width_cm: Mapped[float | None] = mapped_column(Float)
    height_cm: Mapped[float | None] = mapped_column(Float)
    weight_kg: Mapped[float | None] = mapped_column(Float)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    pickup_location: Mapped[str | None] = mapped_column(String(255))
    delivery_location: Mapped[str | None] = mapped_column(String(255))
    pickup_street: Mapped[str | None] = mapped_column(String(255))
    pickup_building_number: Mapped[str | None] = mapped_column(String(30))
    pickup_apartment: Mapped[str | None] = mapped_column(String(30))
    pickup_postal_code: Mapped[str | None] = mapped_column(String(20))
    delivery_street: Mapped[str | None] = mapped_column(String(255))
    delivery_building_number: Mapped[str | None] = mapped_column(String(30))
    delivery_apartment: Mapped[str | None] = mapped_column(String(30))
    delivery_postal_code: Mapped[str | None] = mapped_column(String(20))
    preferred_date: Mapped[date | None] = mapped_column(Date)
    preferred_time: Mapped[time | None] = mapped_column(Time)
    pickup_floor: Mapped[int | None] = mapped_column(Integer)
    delivery_floor: Mapped[int | None] = mapped_column(Integer)
    pickup_has_elevator: Mapped[bool | None] = mapped_column(Boolean)
    delivery_has_elevator: Mapped[bool | None] = mapped_column(Boolean)
    notes: Mapped[str | None] = mapped_column(Text)
    original_message: Mapped[str | None] = mapped_column(Text)
    customer_email: Mapped[str | None] = mapped_column(String(254))
    customer_phone: Mapped[str | None] = mapped_column(String(32))
    source_email_id: Mapped[str | None] = mapped_column(String(255))
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


class TransportShipment(Base):
    __tablename__ = "transport_shipments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    destination: Mapped[str] = mapped_column(String(1000), nullable=False)
    vehicle_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("vehicles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class ShipmentOrder(Base):
    __tablename__ = "shipment_orders"
    __table_args__ = (
        UniqueConstraint("order_id", name="uq_shipment_orders_order_id"),
    )

    shipment_id: Mapped[int] = mapped_column(
        ForeignKey("transport_shipments.id", ondelete="CASCADE"),
        primary_key=True,
    )
    order_id: Mapped[int] = mapped_column(
        ForeignKey("transport_orders.id", ondelete="RESTRICT"),
        primary_key=True,
    )


class IncomingEmail(Base):
    __tablename__ = "incoming_emails"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending_analysis', 'ready', 'converted')",
            name="ck_incoming_emails_status",
        ),
        UniqueConstraint("message_id", name="uq_incoming_emails_message_id"),
        UniqueConstraint("converted_order_id", name="uq_incoming_emails_converted_order_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message_id: Mapped[str] = mapped_column(String(255), nullable=False)
    sender_email: Mapped[str | None] = mapped_column(String(254))
    subject: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    body: Mapped[str] = mapped_column(Text, nullable=False)
    analysis_json: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending_analysis")
    converted_order_id: Mapped[int | None] = mapped_column(
        ForeignKey("transport_orders.id", ondelete="SET NULL"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class EmailInboxFilter(Base):
    __tablename__ = "email_inbox_filter"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_email_inbox_filter_singleton"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    subject_phrase: Mapped[str] = mapped_column(String(200), nullable=False, default="")


class ShipmentNotification(Base):
    __tablename__ = "shipment_notifications"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'sending', 'sent', 'failed', 'not_configured')",
            name="ck_shipment_notifications_status",
        ),
        UniqueConstraint("order_id", name="uq_shipment_notifications_order_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shipment_id: Mapped[int] = mapped_column(
        ForeignKey("transport_shipments.id", ondelete="CASCADE"),
        nullable=False,
    )
    order_id: Mapped[int] = mapped_column(
        ForeignKey("transport_orders.id", ondelete="RESTRICT"),
        nullable=False,
    )
    recipient_email: Mapped[str] = mapped_column(String(254), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(String(500))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
