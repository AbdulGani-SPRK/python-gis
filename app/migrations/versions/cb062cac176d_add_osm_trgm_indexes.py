"""add_osm_trgm_indexes

Revision ID: cb062cac176d
Revises: 
Create Date: 2026-06-27 09:39:37.189708+00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'cb062cac176d'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_osm_point_name_trgm ON osm.planet_osm_point USING gin (name gin_trgm_ops);")
    op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_osm_polygon_name_trgm ON osm.planet_osm_polygon USING gin (name gin_trgm_ops);")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS osm.idx_osm_polygon_name_trgm;")
    op.execute("DROP INDEX IF EXISTS osm.idx_osm_point_name_trgm;")

