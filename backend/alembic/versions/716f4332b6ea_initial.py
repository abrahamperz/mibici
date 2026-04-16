"""initial

Revision ID: 716f4332b6ea
Revises:
Create Date: 2026-04-15 18:09:47.235473

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2
from geoalchemy2 import Geometry

# revision identifiers, used by Alembic.
revision: str = '716f4332b6ea'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'stations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('geom', Geometry(geometry_type='POINT', srid=4326, spatial_index=False), nullable=False),
        sa.Column('total_slots', sa.Integer(), nullable=False),
        sa.Column('available_bikes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('idx_stations_geom', 'stations', ['geom'], postgresql_using='gist')

    op.create_table(
        'reservations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('station_id', sa.Integer(), sa.ForeignKey('stations.id'), nullable=False),
        sa.Column('reserved_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('returned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
    )


def downgrade() -> None:
    op.drop_table('reservations')
    op.drop_index('idx_stations_geom', table_name='stations', postgresql_using='gist')
    op.drop_table('stations')
