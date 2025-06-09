"""Add subjects support to classes

Revision ID: add_subjects_v1
Revises: add_class_id_to_chat
Create Date: 2025-01-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = 'add_subjects_v1'
down_revision = 'add_class_id_to_chat'
branch_labels = None
depends_on = None


def upgrade():
    # 教科マスタテーブル
    op.create_table('subjects',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('code', sa.String(20), nullable=False),
        sa.Column('ai_system_prompt', sa.Text()),
        sa.Column('learning_objectives', sa.Text()),
        sa.Column('assessment_criteria', sa.Text()),
        sa.Column('grade_level', sa.String(20)),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), default=datetime.utcnow),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    
    # クラステーブルに教科ID追加
    op.add_column('classes', 
        sa.Column('subject_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_class_subject', 'classes', 'subjects',
        ['subject_id'], ['id'], ondelete='SET NULL')
    
    # チャット履歴に教科ID追加
    op.add_column('chat_history',
        sa.Column('subject_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_chat_subject', 'chat_history', 'subjects',
        ['subject_id'], ['id'], ondelete='SET NULL')
    
    # 初期データの投入
    op.execute("""
        INSERT INTO subjects (name, code, ai_system_prompt, learning_objectives, grade_level, is_active)
        VALUES 
        ('理科', 'science', '科学的思考を促進し、仮説・実験・結論のプロセスを重視してください。生徒の疑問に対して、観察や実験を通じた探究的な学習を促してください。安全性に配慮し、実験の際の注意事項も含めてください。', '科学的な見方・考え方を身に付ける。自然の事物・現象について理解を深める。観察・実験などに関する技能を身に付ける。', '中学', 1),
        ('数学', 'math', '論理的思考と段階的な問題解決を支援してください。公式の暗記ではなく、なぜその公式が成り立つのかを理解させてください。実生活での応用例を示し、数学の有用性を伝えてください。', '数学的な見方・考え方を身に付ける。数量や図形について理解を深める。問題解決の方法を身に付ける。', '中学', 1),
        ('国語', 'japanese', '読解力と表現力の向上を目指してください。文章の構造を意識させ、論理的な文章構成を指導してください。語彙を豊かにし、適切な言葉遣いができるよう支援してください。', '言語能力の向上。思考力・判断力・表現力の育成。言語文化への理解を深める。', '中学', 1),
        ('社会', 'social', '歴史的背景や地理的要因を考慮し、多角的な視点を提供してください。現代社会との関連性を示し、社会問題への関心を高めてください。批判的思考力を養い、自分の意見を持てるよう促してください。', '社会的な見方・考え方を身に付ける。社会的事象について理解を深める。資料活用の技能を身に付ける。', '中学', 1),
        ('英語', 'english', '実用的な英語表現を重視し、コミュニケーション能力を高めてください。文法は実際の使用場面と関連付けて説明してください。異文化理解を深め、グローバルな視点を養ってください。', 'コミュニケーション能力の向上。言語や文化に対する理解を深める。主体的に英語を用いる態度を養う。', '中学', 1)
    """)


def downgrade():
    # 外部キー制約の削除
    op.drop_constraint('fk_chat_subject', 'chat_history', type_='foreignkey')
    op.drop_constraint('fk_class_subject', 'classes', type_='foreignkey')
    
    # カラムの削除
    op.drop_column('chat_history', 'subject_id')
    op.drop_column('classes', 'subject_id')
    
    # テーブルの削除
    op.drop_table('subjects')