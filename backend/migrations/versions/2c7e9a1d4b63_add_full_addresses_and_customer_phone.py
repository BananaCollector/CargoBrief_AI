"""add full addresses and customer phone

Revision ID: 2c7e9a1d4b63
Revises: 1f9d7c4a6b2e
Create Date: 2026-11-15 15:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2c7e9a1d4b63"
down_revision: Union[str, None] = "1f9d7c4a6b2e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("transport_orders") as batch_op:
        batch_op.add_column(sa.Column("pickup_street", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("pickup_building_number", sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column("pickup_apartment", sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column("pickup_postal_code", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("delivery_street", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("delivery_building_number", sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column("delivery_apartment", sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column("delivery_postal_code", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("customer_phone", sa.String(length=32), nullable=True))

    with op.batch_alter_table("transport_shipments") as batch_op:
        batch_op.alter_column(
            "destination",
            existing_type=sa.String(length=255),
            type_=sa.String(length=1000),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("transport_shipments") as batch_op:
        batch_op.alter_column(
            "destination",
            existing_type=sa.String(length=1000),
            type_=sa.String(length=255),
            existing_nullable=False,
        )

    with op.batch_alter_table("transport_orders") as batch_op:
        batch_op.drop_column("customer_phone")
        batch_op.drop_column("delivery_postal_code")
        batch_op.drop_column("delivery_apartment")
        batch_op.drop_column("delivery_building_number")
        batch_op.drop_column("delivery_street")
        batch_op.drop_column("pickup_postal_code")
        batch_op.drop_column("pickup_apartment")
        batch_op.drop_column("pickup_building_number")
        batch_op.drop_column("pickup_street")
