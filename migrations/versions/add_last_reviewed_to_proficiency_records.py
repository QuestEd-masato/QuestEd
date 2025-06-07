"""Add last_reviewed column to proficiency_records for time decay

Revision ID: add_last_reviewed_column
Revises: add_cascade_delete_to_user_relationships
Create Date: 2024-06-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'add_last_reviewed_column'
down_revision = 'add_cascade_delete_to_user_relationships'
branch_labels = None
depends_on = None

def upgrade():
    # Add last_reviewed column to proficiency_records table
    with op.batch_alter_table('proficiency_records', schema=None) as batch_op:
        batch_op.add_column(sa.Column('last_reviewed', sa.DateTime(), nullable=True))
    
    # Initialize last_reviewed with current timestamp for existing records
    op.execute("UPDATE proficiency_records SET last_reviewed = last_updated WHERE last_reviewed IS NULL")

def downgrade():
    # Remove last_reviewed column from proficiency_records table
    with op.batch_alter_table('proficiency_records', schema=None) as batch_op:
        batch_op.drop_column('last_reviewed')