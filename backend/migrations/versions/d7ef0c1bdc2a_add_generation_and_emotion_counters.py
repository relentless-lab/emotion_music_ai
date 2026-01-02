"""add generation/emotion counters and align total_works with published public works

Revision ID: d7ef0c1bdc2a
Revises: 7ad981cba057
Create Date: 2025-12-13 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = "d7ef0c1bdc2a"
down_revision = "7ad981cba057"
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

    if not column_exists(conn, "users", "total_generations"):
        op.add_column(
            "users",
            sa.Column("total_generations", sa.Integer(), nullable=False, server_default=sa.text("0")),
        )

    if not column_exists(conn, "users", "emotion_detection_count"):
        op.add_column(
            "users",
            sa.Column("emotion_detection_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        )

    # Backfill total_works to count only published & public works
    if column_exists(conn, "users", "total_works"):
        visibility_filter = "AND w.visibility = 'public'" if column_exists(conn, "works", "visibility") else ""
        op.execute(
            text(
                f"""
                UPDATE users u
                SET total_works = (
                  SELECT COUNT(*)
                  FROM works w
                  WHERE w.user_id = u.id
                    AND w.status = 'published'
                    {visibility_filter}
                )
                """
            )
        )

    # Remove server defaults to match SQLAlchemy model defaults
    if column_exists(conn, "users", "total_generations"):
        op.alter_column("users", "total_generations", server_default=None)
    if column_exists(conn, "users", "emotion_detection_count"):
        op.alter_column("users", "emotion_detection_count", server_default=None)


def downgrade() -> None:
    if column_exists(op.get_bind(), "users", "emotion_detection_count"):
        op.drop_column("users", "emotion_detection_count")
    if column_exists(op.get_bind(), "users", "total_generations"):
        op.drop_column("users", "total_generations")
