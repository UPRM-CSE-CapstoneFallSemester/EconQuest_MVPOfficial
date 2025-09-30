"""teacher groups + module assignments

Revision ID: t_groups_assign
Revises: 2517f9b08096
Create Date: 2025-09-03 01:45:00
"""
from alembic import op
import sqlalchemy as sa

# IDs
revision = 't_groups_assign'
down_revision = '2517f9b08096'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'groups',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('grade_level', sa.String(length=32), nullable=True),
        sa.Column('section', sa.String(length=32), nullable=True),
        sa.Column('teacher_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['teacher_id'], ['users.id'], name='fk_groups_teacher', ondelete='SET NULL')
    )

    op.create_table(
        'group_students',
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id'], name='fk_gs_group', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['student_id'], ['users.id'], name='fk_gs_student', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('group_id', 'student_id', name='pk_group_students'),
        sa.UniqueConstraint('group_id', 'student_id', name='uq_group_student')
    )

    op.create_table(
        'module_assignments',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('module_id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=True),
        sa.Column('student_id', sa.Integer(), nullable=True),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.ForeignKeyConstraint(['module_id'], ['modules.id'], name='fk_ma_module', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id'], name='fk_ma_group', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['student_id'], ['users.id'], name='fk_ma_student', ondelete='CASCADE')
    )

def downgrade():
    op.drop_table('module_assignments')
    op.drop_table('group_students')
    op.drop_table('groups')
