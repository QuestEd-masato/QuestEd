"""Add review_date to proficiency_records

Revision ID: 2252038bf4ac
Revises: 0340c345d9bc
Create Date: 2025-03-26 04:24:02.704198

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '2252038bf4ac'
down_revision = '0340c345d9bc'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    # 既存のカラム削除や外部キー制約削除は行わず、新しいカラムを追加するだけ
    with op.batch_alter_table('proficiency_records', schema=None) as batch_op:
        batch_op.add_column(sa.Column('review_date', sa.Date(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    # 追加したカラムだけを削除
    with op.batch_alter_table('proficiency_records', schema=None) as batch_op:
        batch_op.drop_column('review_date')
    # ### end Alembic commands ###