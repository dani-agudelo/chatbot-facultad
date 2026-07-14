"""Add encrypted API key columns to admin settings

Revision ID: 003_api_keys
Revises: 002_branding
Create Date: 2026-07-14
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_api_keys"
down_revision: Union[str, None] = "002_branding"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "chatbot_admin_settings",
        sa.Column("gemini_api_key_enc", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "chatbot_admin_settings",
        sa.Column("nvidia_api_key_enc", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("chatbot_admin_settings", "nvidia_api_key_enc")
    op.drop_column("chatbot_admin_settings", "gemini_api_key_enc")
