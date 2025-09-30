"""add groups, group_members, module_assignments

Revision ID: e6ae94293a9b
Revises: t_groups_assign
Create Date: 2025-09-04 01:40:38.153909

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e6ae94293a9b'
down_revision = 't_groups_assign'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing = set(insp.get_table_names())

    if 'groups' not in existing:
        op.create_table(
            'groups',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('name', sa.String(length=160), nullable=False),
            sa.Column('teacher_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE')),
            sa.Column('grade', sa.String(length=20))
        )

    if 'group_members' not in existing:
        op.create_table(
            'group_members',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('group_id', sa.Integer(), sa.ForeignKey('groups.id', ondelete='CASCADE')),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE')),
            sa.Column('created_at', sa.DateTime())
        )

    if 'module_assignments' not in existing:
        op.create_table(
            'module_assignments',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('group_id', sa.Integer(), sa.ForeignKey('groups.id', ondelete='CASCADE')),
            sa.Column('module_id', sa.Integer(), sa.ForeignKey('modules.id', ondelete='CASCADE')),
            sa.Column('due_date', sa.DateTime())
        )

def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing = set(insp.get_table_names())

    if 'module_assignments' in existing:
        op.drop_table('module_assignments')
    if 'group_members' in existing:
        op.drop_table('group_members')
    if 'groups' in existing:
        op.drop_table('groups')