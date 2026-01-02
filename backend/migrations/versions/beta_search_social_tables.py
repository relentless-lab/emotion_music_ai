"""beta search/social tables and metrics placeholders (3-day window)

Revision ID: beta_search_social_tables
Revises: cover_image_for_music_files
Create Date: 2025-12-19 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "beta_search_social_tables"
down_revision = "cover_image_for_music_files"
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


def table_exists(conn, table: str) -> bool:
    sql = text(
        """
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = :table
        """
    )
    return conn.execute(sql, {"table": table}).scalar() > 0


def upgrade() -> None:
    conn = op.get_bind()

    # 用户侧的预留统计字段
    if not column_exists(conn, "users", "plays_this_month"):
        op.add_column(
            "users",
            sa.Column("plays_this_month", sa.Integer(), nullable=False, server_default="0"),
        )
        op.alter_column("users", "plays_this_month", server_default=None)
    if not column_exists(conn, "users", "liked_works_count"):
        op.add_column(
            "users",
            sa.Column("liked_works_count", sa.Integer(), nullable=False, server_default="0"),
        )
        op.alter_column("users", "liked_works_count", server_default=None)

    # 播放日志：用于月播放数与 3 天热门计算
    if not table_exists(conn, "work_play_logs"):
        op.create_table(
            "work_play_logs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True, index=True),
            sa.Column("work_id", sa.Integer(), sa.ForeignKey("works.id"), nullable=False, index=True),
            sa.Column("played_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("source", sa.String(length=50), nullable=True),
        )
        op.create_index("ix_work_play_logs_work_time", "work_play_logs", ["work_id", "played_at"])

    # 3 天窗口的热门作品快照
    if not table_exists(conn, "work_popularity_snapshots"):
        op.create_table(
            "work_popularity_snapshots",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("work_id", sa.Integer(), sa.ForeignKey("works.id"), nullable=False, index=True),
            sa.Column("window_days", sa.Integer(), nullable=False, server_default="3"),
            sa.Column("start_time", sa.DateTime(), nullable=True),
            sa.Column("end_time", sa.DateTime(), nullable=True),
            sa.Column("plays", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("likes", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("rank", sa.Integer(), nullable=True),
            sa.Column("snapshot_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
        op.alter_column("work_popularity_snapshots", "window_days", server_default=None)
        op.alter_column("work_popularity_snapshots", "plays", server_default=None)
        op.alter_column("work_popularity_snapshots", "likes", server_default=None)
        op.alter_column("work_popularity_snapshots", "score", server_default=None)
        op.create_index(
            "ix_work_popularity_window_time",
            "work_popularity_snapshots",
            ["window_days", "snapshot_at"],
        )

    # 推荐创作者快照（同样使用 3 天窗口）
    if not table_exists(conn, "creator_recommendations"):
        op.create_table(
            "creator_recommendations",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
            sa.Column("window_days", sa.Integer(), nullable=False, server_default="3"),
            sa.Column("score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("reason", sa.String(length=255), nullable=True),
            sa.Column("snapshot_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
        op.alter_column("creator_recommendations", "window_days", server_default=None)
        op.alter_column("creator_recommendations", "score", server_default=None)
        op.create_index(
            "ix_creator_reco_window_time",
            "creator_recommendations",
            ["window_days", "snapshot_at"],
        )


def downgrade() -> None:
    conn = op.get_bind()

    if table_exists(conn, "creator_recommendations"):
        op.drop_index("ix_creator_reco_window_time", table_name="creator_recommendations")
        op.drop_table("creator_recommendations")

    if table_exists(conn, "work_popularity_snapshots"):
        op.drop_index("ix_work_popularity_window_time", table_name="work_popularity_snapshots")
        op.drop_table("work_popularity_snapshots")

    if table_exists(conn, "work_play_logs"):
        op.drop_index("ix_work_play_logs_work_time", table_name="work_play_logs")
        op.drop_table("work_play_logs")

    if column_exists(conn, "users", "liked_works_count"):
        op.drop_column("users", "liked_works_count")
    if column_exists(conn, "users", "plays_this_month"):
        op.drop_column("users", "plays_this_month")
