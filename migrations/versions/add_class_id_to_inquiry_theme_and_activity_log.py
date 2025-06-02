"""Add class_id to InquiryTheme and ActivityLog

Revision ID: add_class_id_fields
Revises: fca5ede8dd9f
Create Date: 2025-01-06

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_class_id_fields'
down_revision = 'fca5ede8dd9f'
branch_labels = None
depends_on = None


def upgrade():
    # InquiryThemeテーブルにclass_idを追加
    op.add_column('inquiry_themes', sa.Column('class_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_inquiry_themes_class_id', 'inquiry_themes', 'classes', ['class_id'], ['id'])
    
    # ActivityLogテーブルにclass_idを追加
    op.add_column('activity_logs', sa.Column('class_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_activity_logs_class_id', 'activity_logs', 'classes', ['class_id'], ['id'])
    
    # 既存データの更新（main_theme経由でclass_idを設定）
    op.execute("""
        UPDATE inquiry_themes it
        JOIN main_themes mt ON it.main_theme_id = mt.id
        SET it.class_id = mt.class_id
        WHERE it.main_theme_id IS NOT NULL
    """)


def downgrade():
    # 外部キー制約を削除
    op.drop_constraint('fk_activity_logs_class_id', 'activity_logs', type_='foreignkey')
    op.drop_constraint('fk_inquiry_themes_class_id', 'inquiry_themes', type_='foreignkey')
    
    # カラムを削除
    op.drop_column('activity_logs', 'class_id')
    op.drop_column('inquiry_themes', 'class_id')