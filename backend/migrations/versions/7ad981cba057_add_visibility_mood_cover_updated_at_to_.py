"""add visibility/mood/cover/updated_at to works and plays_received to users

Revision ID: 7ad981cba057
Revises: 3c9c39630175
Create Date: 2025-12-12 18:44:21.620704
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision = '7ad981cba057'
down_revision = '3c9c39630175'
branch_labels = None
depends_on = None


def column_exists(conn, table: str, column: str) -> bool:
    sql = text(
        """
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = :table
          AND COLUMN_NAME = :column
        """
    )
    return conn.execute(sql, {"table": table, "column": column}).scalar() > 0


def upgrade() -> None:
    conn = op.get_bind()

    if not column_exists(conn, "works", "cover_url"):
        op.add_column("works", sa.Column("cover_url", sa.String(length=255), nullable=True))

    if not column_exists(conn, "works", "updated_at"):
        op.add_column(
            "works",
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )


def downgrade() -> None:
    # 仅撤销本次对 works 的新增列
    op.drop_column('works', 'updated_at')
    op.drop_column('works', 'cover_url')
