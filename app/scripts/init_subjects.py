#!/usr/bin/env python3
"""
教科機能の初期データ投入スクリプト
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app
from app.models import db
from app.models.subject import Subject

def init_subjects():
    """教科の初期データを投入"""
    app = create_app()
    with app.app_context():
        subjects_data = [
            {
                'name': '理科',
                'code': 'science',
                'ai_system_prompt': '科学的思考を促進し、実験や観察の重要性を強調してください。仮説・実験・結論のプロセスを重視し、生徒の疑問に対して探究的な学習を促してください。安全性に配慮し、実験の際の注意事項も含めてください。',
                'learning_objectives': '科学的な見方・考え方を身に付ける。自然の事物・現象について理解を深める。観察・実験などに関する技能を身に付ける。',
                'assessment_criteria': '観察・実験の技能、科学的な思考・表現、自然事象への関心・意欲・態度',
                'grade_level': '中学'
            },
            {
                'name': '数学',
                'code': 'math',
                'ai_system_prompt': '論理的思考と段階的な問題解決を支援してください。公式の暗記ではなく、なぜその公式が成り立つのかを理解させてください。実生活での応用例を示し、数学の有用性を伝えてください。',
                'learning_objectives': '数学的な見方・考え方を身に付ける。数量や図形について理解を深める。問題解決の方法を身に付ける。',
                'assessment_criteria': '数学的な技能、数学的な思考・判断・表現、数学への関心・意欲・態度',
                'grade_level': '中学'
            },
            {
                'name': '国語',
                'code': 'japanese',
                'ai_system_prompt': '読解力と表現力の向上を目指し、文章構成を意識させてください。語彙を豊かにし、適切な言葉遣いができるよう支援してください。古典作品への興味も促進してください。',
                'learning_objectives': '言語能力の向上。思考力・判断力・表現力の育成。言語文化への理解を深める。',
                'assessment_criteria': '言語についての知識・理解・技能、読むこと、書くこと、話すこと・聞くこと',
                'grade_level': '中学'
            },
            {
                'name': '社会',
                'code': 'social',
                'ai_system_prompt': '歴史的背景や地理的要因を考慮し、多角的な視点を提供してください。現代社会との関連性を示し、社会問題への関心を高めてください。批判的思考力を養い、自分の意見を持てるよう促してください。',
                'learning_objectives': '社会的な見方・考え方を身に付ける。社会的事象について理解を深める。資料活用の技能を身に付ける。',
                'assessment_criteria': '社会的な思考・判断・表現、資料活用の技能、社会的事象への関心・意欲・態度',
                'grade_level': '中学'
            },
            {
                'name': '英語',
                'code': 'english',
                'ai_system_prompt': '実用的な英語表現を重視し、コミュニケーション能力を高めてください。文法は実際の使用場面と関連付けて説明してください。異文化理解を深め、グローバルな視点を養ってください。',
                'learning_objectives': 'コミュニケーション能力の向上。言語や文化に対する理解を深める。主体的に英語を用いる態度を養う。',
                'assessment_criteria': 'コミュニケーション能力(聞く、読む、話す、書く)、言語や文化への理解、コミュニケーションへの関心・意欲・態度',
                'grade_level': '中学'
            },
            {
                'name': '総合的な学習の時間',
                'code': 'integrated',
                'ai_system_prompt': '横断的・総合的な学習を支援し、課題解決学習を重視してください。生徒の探究心を刺激し、自主的な学習を促進してください。実社会との関連を意識した指導を心がけてください。',
                'learning_objectives': '課題を見つけ、自ら学び、考え、判断し、よりよく問題を解決する資質や能力を育成する。学び方やものの考え方を身に付ける。',
                'assessment_criteria': '学習方法、問題解決能力、総合的な見方や考え方、学習への意欲・態度',
                'grade_level': '中学'
            }
        ]
        
        added_count = 0
        updated_count = 0
        
        for subject_data in subjects_data:
            existing = Subject.query.filter_by(code=subject_data['code']).first()
            if not existing:
                subject = Subject(**subject_data)
                db.session.add(subject)
                print(f"✓ Added subject: {subject_data['name']} ({subject_data['code']})")
                added_count += 1
            else:
                # 既存の教科の情報を更新
                existing.ai_system_prompt = subject_data['ai_system_prompt']
                existing.learning_objectives = subject_data['learning_objectives']
                existing.assessment_criteria = subject_data['assessment_criteria']
                print(f"- Updated existing subject: {subject_data['name']} ({subject_data['code']})")
                updated_count += 1
        
        try:
            db.session.commit()
            print(f"\n✅ Subject initialization complete!")
            print(f"   - Added: {added_count} subjects")
            print(f"   - Updated: {updated_count} subjects")
            
            # 登録された教科を確認
            all_subjects = Subject.query.all()
            print(f"\n📚 Total subjects in database: {len(all_subjects)}")
            for subject in all_subjects:
                print(f"   - {subject.name} ({subject.code})")
                
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error occurred: {str(e)}")
            return False
        
        return True

if __name__ == '__main__':
    print("🚀 Starting subject initialization...")
    success = init_subjects()
    if success:
        print("\n🎉 Subject initialization completed successfully!")
    else:
        print("\n💥 Subject initialization failed!")
        sys.exit(1)