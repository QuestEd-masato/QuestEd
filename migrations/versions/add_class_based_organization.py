"""Add class-based organization for activities and chat

Revision ID: add_class_based_org
Revises: c0587991c5a6
Create Date: 2025-01-06 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_class_based_org'
down_revision = 'c0587991c5a6'
branch_labels = None
depends_on = None


def upgrade():
    # Add class_id to chat_history
    op.add_column('chat_history', sa.Column('class_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_chat_history_class', 'chat_history', 'classes', ['class_id'], ['id'])
    
    # Add is_active to class_enrollments
    op.add_column('class_enrollments', sa.Column('is_active', sa.Boolean(), nullable=True, default=True))
    
    # Set default value for existing records
    op.execute("UPDATE class_enrollments SET is_active = TRUE WHERE is_active IS NULL")


def downgrade():
    # Remove foreign key and column from chat_history
    op.drop_constraint('fk_chat_history_class', 'chat_history', type_='foreignkey')
    op.drop_column('chat_history', 'class_id')
    
    # Remove is_active from class_enrollments
    op.drop_column('class_enrollments', 'is_active')