"""create shipments

Revision ID: 8a2f5ac1e4b7
Revises: 5d311bdd6db1
Create Date: 2026-11-15 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8a2f5ac1e4b7"
down_revision: Union[str, None] = "5d311bdd6db1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "transport_shipments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("destination", sa.String(length=255), nullable=False),
        sa.Column("vehicle_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["vehicle_id"],
            ["vehicles.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "shipment_orders",
        sa.Column("shipment_id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["transport_orders.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["shipment_id"],
            ["transport_shipments.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("shipment_id", "order_id"),
        sa.UniqueConstraint("order_id", name="uq_shipment_orders_order_id"),
    )


def downgrade() -> None:
    op.drop_table("shipment_orders")
    op.drop_table("transport_shipments")
