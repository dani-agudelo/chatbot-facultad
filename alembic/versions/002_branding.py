"""Add branding fields to admin settings

Revision ID: 002_branding
Revises: 001_admin
Create Date: 2026-07-14
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_branding"
down_revision: Union[str, None] = "001_admin"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "chatbot_admin_settings",
        sa.Column("logo_url", sa.String(length=512), nullable=False, server_default=""),
    )
    op.add_column(
        "chatbot_admin_settings",
        sa.Column("primary_color", sa.String(length=7), nullable=False, server_default="#00407d"),
    )
    op.add_column(
        "chatbot_admin_settings",
        sa.Column("accent_color", sa.String(length=7), nullable=False, server_default="#f27022"),
    )
    op.add_column(
        "chatbot_admin_settings",
        sa.Column(
            "brand_name",
            sa.String(length=128),
            nullable=False,
            server_default="Chatbot Facultad",
        ),
    )
    op.add_column(
        "chatbot_admin_settings",
        sa.Column(
            "brand_subtitle",
            sa.String(length=128),
            nullable=False,
            server_default="Administración",
        ),
    )


def downgrade() -> None:
    op.drop_column("chatbot_admin_settings", "brand_subtitle")
    op.drop_column("chatbot_admin_settings", "brand_name")
    op.drop_column("chatbot_admin_settings", "accent_color")
    op.drop_column("chatbot_admin_settings", "primary_color")
    op.drop_column("chatbot_admin_settings", "logo_url")
