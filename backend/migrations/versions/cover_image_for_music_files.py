"""add cover_image_path to music_files for generated album covers

Revision ID: cover_image_for_music_files
Revises: d7ef0c1bdc2a
Create Date: 2025-12-18 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = "cover_image_for_music_files"
down_revision = "d7ef0c1bdc2a"
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

    if not column_exists(conn, "music_files", "cover_image_path"):
        op.add_column("music_files", sa.Column("cover_image_path", sa.String(length=500), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    if column_exists(conn, "music_files", "cover_image_path"):
        op.drop_column("music_files", "cover_image_path")












