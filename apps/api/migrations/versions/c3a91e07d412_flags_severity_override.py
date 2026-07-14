# meta: alembic revision — additive flags.severity_override (per-flag
# severity increment, 2026-07-14). NULL = inherit rule severity (the AI
# recommendation). Overrides affect DISPLAY AND METRICS ONLY: persisted
# score_rows/outcome_rows are never rewritten (they are the audit trail of
# what the checker concluded at run time).
"""flags severity_override

Revision ID: c3a91e07d412
Revises: 94a47fceda41
Create Date: 2026-07-14 08:20:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3a91e07d412'
down_revision: Union[str, None] = '94a47fceda41'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("flags", sa.Column("severity_override", sa.String(),
                                     nullable=True))


def downgrade() -> None:
    op.drop_column("flags", "severity_override")
