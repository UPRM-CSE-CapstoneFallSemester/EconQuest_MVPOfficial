"""add summary/level/xp_reward to modules; create student tables

Revision ID: 2517f9b08096
Revises: c1473b0dcd4c
Create Date: 2025-09-03 01:23:03.699487

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '2517f9b08096'
down_revision = 'c1473b0dcd4c'
branch_labels = None
depends_on = None


def upgrade():
    # --- activities ---
    with op.batch_alter_table('activities', schema=None) as batch_op:
        batch_op.add_column(sa.Column('position', sa.Integer(), nullable=True))
        # IMPORTANTE: poner nullable=True para no romper con filas existentes en SQLite
        batch_op.add_column(sa.Column('title', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('is_published', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('content_json', sa.Text(), nullable=True))

        batch_op.alter_column(
            'type',
            existing_type=sa.VARCHAR(length=24),
            type_=sa.String(length=50),
            existing_nullable=False
        )
        batch_op.alter_column(
            'max_points',
            existing_type=sa.INTEGER(),
            nullable=True
        )

        batch_op.create_index(batch_op.f('ix_activities_module_id'), ['module_id'], unique=False)


        batch_op.drop_column('config_json')
        batch_op.drop_column('created_at')

    # --- modules ---
    with op.batch_alter_table('modules', schema=None) as batch_op:
        batch_op.add_column(sa.Column('summary', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('level', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('xp_reward', sa.Integer(), nullable=True))

        batch_op.alter_column(
            'title',
            existing_type=sa.VARCHAR(length=160),
            type_=sa.String(length=200),
            existing_nullable=False
        )
        batch_op.alter_column(
            'is_published',
            existing_type=sa.BOOLEAN(),
            nullable=True
        )

        batch_op.drop_column('lang')
        batch_op.drop_column('created_at')


def downgrade():
    # --- modules ---
    with op.batch_alter_table('modules', schema=None) as batch_op:
        batch_op.add_column(sa.Column('created_at', sa.DATETIME(), nullable=False))
        batch_op.add_column(sa.Column('lang', sa.VARCHAR(length=4), nullable=False))
        batch_op.alter_column(
            'is_published',
            existing_type=sa.BOOLEAN(),
            nullable=False
        )
        batch_op.alter_column(
            'title',
            existing_type=sa.String(length=200),
            type_=sa.VARCHAR(length=160),
            existing_nullable=False
        )
        batch_op.drop_column('xp_reward')
        batch_op.drop_column('level')
        batch_op.drop_column('summary')

    # --- activities ---
    with op.batch_alter_table('activities', schema=None) as batch_op:
        batch_op.add_column(sa.Column('created_at', sa.DATETIME(), nullable=False))
        batch_op.add_column(sa.Column('config_json', sqlite.JSON(), nullable=False))


        batch_op.drop_index(batch_op.f('ix_activities_module_id'))

        batch_op.alter_column(
            'max_points',
            existing_type=sa.INTEGER(),
            nullable=False
        )
        batch_op.alter_column(
            'type',
            existing_type=sa.String(length=50),
            type_=sa.VARCHAR(length=24),
            existing_nullable=False
        )
        batch_op.drop_column('content_json')
        batch_op.drop_column('is_published')
        batch_op.drop_column('title')
        batch_op.drop_column('position')
