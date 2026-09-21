"""projects + api_keys + run.project_id + step hierarchy

Revision ID: 002_projects
Revises: 001_init
Create Date: 2026-09-21
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002_projects"
down_revision: Union[str, None] = "001_init"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    # default project for existing data + demo
    op.execute("INSERT INTO projects (id, name) VALUES ('00000000-0000-0000-0000-000000000001', 'default') ON CONFLICT DO NOTHING")

    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("public_key", sa.String(length=64), nullable=False, unique=True),
        sa.Column("secret_hash", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.add_column("runs", sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True))
    op.create_index("ix_runs_project_id", "runs", ["project_id"])
    op.execute("UPDATE runs SET project_id='00000000-0000-0000-0000-000000000001' WHERE project_id IS NULL")

    op.add_column("steps", sa.Column("parent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("steps.id", ondelete="SET NULL"), nullable=True))
    op.add_column("steps", sa.Column("observation_type", sa.String(length=20), nullable=True))
    op.add_column("steps", sa.Column("model", sa.String(length=100), nullable=True))
    op.add_column("steps", sa.Column("usage", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("steps", "usage")
    op.drop_column("steps", "model")
    op.drop_column("steps", "observation_type")
    op.drop_column("steps", "parent_id")
    op.drop_index("ix_runs_project_id", table_name="runs")
    op.drop_column("runs", "project_id")
    op.drop_table("api_keys")
    op.drop_table("projects")
