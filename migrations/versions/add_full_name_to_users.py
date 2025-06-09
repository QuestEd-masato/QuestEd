"""Add full_name to users table

Revision ID: add_full_name_v1
Revises: add_subjects_v1
Create Date: 2025-01-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_full_name_v1'
down_revision = 'add_subjects_v1'
branch_labels = None
depends_on = None


def upgrade():
    # full_nameカラムを追加（nullable=Trueで既存データに影響しない）
    op.add_column('users', sa.Column('full_name', sa.String(100), nullable=True))
    
    # 既存データの移行: usernameをfull_nameにコピー（暫定的）
    op.execute("""
        UPDATE users 
        SET full_name = username 
        WHERE full_name IS NULL
    """)


def downgrade():
    # full_nameカラムを削除
    op.drop_column('users', 'full_name')