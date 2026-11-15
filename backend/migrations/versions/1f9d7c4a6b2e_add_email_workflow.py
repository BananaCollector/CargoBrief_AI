"""add email workflow

Revision ID: 1f9d7c4a6b2e
Revises: 8a2f5ac1e4b7
Create Date: 2026-11-15 15:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "1f9d7c4a6b2e"
down_revision: Union[str, None] = "8a2f5ac1e4b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("transport_orders") as batch_op:
        batch_op.add_column(sa.Column("customer_email", sa.String(length=254), nullable=True))
        batch_op.add_column(sa.Column("source_email_id", sa.String(length=255), nullable=True))
        batch_op.create_unique_constraint(
            "uq_orders_source_email_id",
            ["source_email_id"],
        )

    op.create_table(
        "incoming_emails",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.String(length=255), nullable=False),
        sa.Column("sender_email", sa.String(length=254), nullable=True),
        sa.Column("subject", sa.String(length=500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("analysis_json", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("converted_order_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending_analysis', 'ready', 'converted')",
            name="ck_incoming_emails_status",
        ),
        sa.ForeignKeyConstraint(
            ["converted_order_id"],
            ["transport_orders.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("converted_order_id", name="uq_incoming_emails_converted_order_id"),
        sa.UniqueConstraint("message_id", name="uq_incoming_emails_message_id"),
    )
    op.create_table(
        "shipment_notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("shipment_id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("recipient_email", sa.String(length=254), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'sending', 'sent', 'failed', 'not_configured')",
            name="ck_shipment_notifications_status",
        ),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", name="uq_shipment_notifications_order_id"),
    )


def downgrade() -> None:
    op.drop_table("shipment_notifications")
    op.drop_table("incoming_emails")
    with op.batch_alter_table("transport_orders") as batch_op:
        batch_op.drop_constraint("uq_orders_source_email_id", type_="unique")
        batch_op.drop_column("source_email_id")
        batch_op.drop_column("customer_email")
