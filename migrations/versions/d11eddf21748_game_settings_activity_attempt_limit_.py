"""game settings + activity attempt_limit/default_xp"""

from alembic import op
import sqlalchemy as sa

# --- IDENTIFICADORES DE ALEMBIC ---
revision = "d11eddf21748"         # <-- usa la parte antes del '_' en el nombre del archivo
down_revision = "e6ae94293a9b"    # <-- tu head anterior (el que ya tenías funcionando)
branch_labels = None
depends_on = None


def upgrade():
    # 1) columnas nuevas en activities
    with op.batch_alter_table("activities") as b:
        b.add_column(sa.Column("attempt_limit", sa.Integer()))
        b.add_column(sa.Column("default_xp", sa.Integer()))

    # 2) tabla game_settings
    op.create_table(
        "game_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("xp_base", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("xp_growth", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("max_attempts_default", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )

    # 3) fila por defecto
    conn = op.get_bind()
    conn.execute(sa.text(
        "INSERT INTO game_settings (id, xp_base, xp_growth, max_attempts_default, created_at, updated_at) "
        "VALUES (1, 100, 50, 3, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
    ))


def downgrade():
    with op.batch_alter_table("activities") as b:
        b.drop_column("default_xp")
        b.drop_column("attempt_limit")
    op.drop_table("game_settings")
