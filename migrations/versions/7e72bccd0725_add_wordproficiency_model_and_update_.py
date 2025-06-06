"""Add WordProficiency model and update proficiency system

Revision ID: 7e72bccd0725
Revises: 1fcac5b12033
Create Date: 2025-03-28 10:46:29.103454

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7e72bccd0725'
down_revision = '1fcac5b12033'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('word_proficiency_records',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('student_id', sa.Integer(), nullable=False),
    sa.Column('problem_id', sa.Integer(), nullable=False),
    sa.Column('level', sa.Integer(), nullable=True),
    sa.Column('last_updated', sa.DateTime(), nullable=True),
    sa.Column('review_date', sa.Date(), nullable=True),
    sa.ForeignKeyConstraint(['problem_id'], ['basic_knowledge_items.id'], ),
    sa.ForeignKeyConstraint(['student_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('student_id', 'problem_id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('word_proficiency_records')
    # ### end Alembic commands ###
