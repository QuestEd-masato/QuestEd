"""merge_all_heads

Revision ID: be00c907d1fb
Revises: 8819eb8cd4ce, add_class_based_org, add_class_id_to_chat, add_last_reviewed_column, make_school_code_nullable
Create Date: 2025-06-07 06:41:35.343250

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'be00c907d1fb'
down_revision = ('8819eb8cd4ce', 'add_class_based_org', 'add_class_id_to_chat', 'add_last_reviewed_column', 'make_school_code_nullable')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass