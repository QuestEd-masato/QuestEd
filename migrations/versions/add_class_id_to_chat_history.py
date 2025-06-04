"""add class_id to chat_history

Revision ID: add_class_id_to_chat
Revises: c0587991c5a6
Create Date: 2025-01-06 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_class_id_to_chat'
down_revision = 'c0587991c5a6'
branch_labels = None
depends_on = None


def upgrade():
    # Add class_id column to chat_history table
    op.add_column('chat_history', sa.Column('class_id', sa.Integer(), nullable=True))
    
    # Add foreign key constraint
    op.create_foreign_key('fk_chat_history_class', 'chat_history', 'classes', ['class_id'], ['id'])


def downgrade():
    # Drop foreign key constraint
    op.drop_constraint('fk_chat_history_class', 'chat_history', type_='foreignkey')
    
    # Drop class_id column
    op.drop_column('chat_history', 'class_id')