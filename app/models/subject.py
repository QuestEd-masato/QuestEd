from datetime import datetime
from extensions import db


class Subject(db.Model):
    __tablename__ = 'subjects'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    ai_system_prompt = db.Column(db.Text)
    learning_objectives = db.Column(db.Text)
    assessment_criteria = db.Column(db.Text)
    grade_level = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # リレーション
    classes = db.relationship('Class', backref='subject', lazy='dynamic')
    chat_histories = db.relationship('ChatHistory', backref='subject', lazy='dynamic')
    
    def get_ai_prompt(self):
        """教科別のAIプロンプトを返す"""
        base_prompt = "あなたは優秀な教育AIアシスタントです。"
        if self.ai_system_prompt:
            return f"{base_prompt}\n{self.ai_system_prompt}"
        return base_prompt
    
    def to_dict(self):
        """辞書形式に変換"""
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'ai_system_prompt': self.ai_system_prompt,
            'learning_objectives': self.learning_objectives,
            'assessment_criteria': self.assessment_criteria,
            'grade_level': self.grade_level,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<Subject {self.name}>'


# 教科別プロンプトの定義
SUBJECT_PROMPTS = {
    'science': """
        科学的思考を促進し、仮説・実験・結論のプロセスを重視してください。
        生徒の疑問に対して、観察や実験を通じた探究的な学習を促してください。
        安全性に配慮し、実験の際の注意事項も含めてください。
    """,
    'math': """
        論理的思考と段階的な問題解決を支援してください。
        公式の暗記ではなく、なぜその公式が成り立つのかを理解させてください。
        実生活での応用例を示し、数学の有用性を伝えてください。
    """,
    'japanese': """
        読解力と表現力の向上を目指してください。
        文章の構造を意識させ、論理的な文章構成を指導してください。
        語彙を豊かにし、適切な言葉遣いができるよう支援してください。
    """,
    'social': """
        歴史的背景や地理的要因を考慮し、多角的な視点を提供してください。
        現代社会との関連性を示し、社会問題への関心を高めてください。
        批判的思考力を養い、自分の意見を持てるよう促してください。
    """,
    'english': """
        実用的な英語表現を重視し、コミュニケーション能力を高めてください。
        文法は実際の使用場面と関連付けて説明してください。
        異文化理解を深め、グローバルな視点を養ってください。
    """
}