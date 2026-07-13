# meta: alembic revision — additive issue-cluster columns (roadmap doc 11,
# clustering C1; Aarvin-approved schema change 2026-07-13).
"""issue clusters: parent_cluster_id, rationale, state, member_snapshot

Revision ID: 4d5c89485181
Revises: be61a6f8ddf0
Create Date: 2026-07-13 08:53:46.508723
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '4d5c89485181'
down_revision: Union[str, None] = 'be61a6f8ddf0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("clusters", sa.Column("parent_cluster_id", sa.String(), nullable=True))
    op.add_column("clusters", sa.Column("rationale", sa.Text(), nullable=True))
    op.add_column("clusters", sa.Column(
        "state", sa.String(), nullable=False, server_default="auto"))
    op.add_column("clusters", sa.Column(
        "member_snapshot", postgresql.JSONB(), nullable=False,
        server_default=sa.text("'{}'::jsonb")))
    op.create_foreign_key("fk_clusters_parent", "clusters", "clusters",
                          ["parent_cluster_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_clusters_parent", "clusters", type_="foreignkey")
    op.drop_column("clusters", "member_snapshot")
    op.drop_column("clusters", "state")
    op.drop_column("clusters", "rationale")
    op.drop_column("clusters", "parent_cluster_id")
