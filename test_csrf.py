#!/usr/bin/env python
# test_csrf.py - CSRF デバッグ用テストスクリプト

from flask import Flask, render_template_string
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from wtforms import StringField, SubmitField
from dotenv import load_dotenv
import os

# .envファイルを読み込む
load_dotenv()

# テスト用のシンプルなアプリケーション
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'test-secret-key')
app.config['WTF_CSRF_ENABLED'] = True

# CSRFを初期化
csrf = CSRFProtect(app)

# テスト用のフォーム
class TestForm(FlaskForm):
    name = StringField('Name')
    submit = SubmitField('Submit')

# テストテンプレート
TEST_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>CSRF Test</title>
</head>
<body>
    <h1>CSRF Test</h1>
    <p>SECRET_KEY is set: {{ secret_key_set }}</p>
    <p>WTF_CSRF_ENABLED: {{ csrf_enabled }}</p>
    
    <form method="POST">
        {{ form.hidden_tag() }}
        {{ form.name.label }} {{ form.name() }}
        {{ form.submit() }}
    </form>
</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def index():
    form = TestForm()
    if form.validate_on_submit():
        return f'Form submitted with name: {form.name.data}'
    
    return render_template_string(TEST_TEMPLATE, 
                                form=form,
                                secret_key_set=bool(app.config.get('SECRET_KEY')),
                                csrf_enabled=app.config.get('WTF_CSRF_ENABLED', True))

@app.route('/debug')
def debug():
    """デバッグ情報を表示"""
    return {
        'SECRET_KEY': app.config.get('SECRET_KEY', 'NOT SET')[:10] + '...' if app.config.get('SECRET_KEY') else 'NOT SET',
        'WTF_CSRF_ENABLED': app.config.get('WTF_CSRF_ENABLED', True),
        'csrf_initialized': csrf is not None,
        'extensions': list(app.extensions.keys())
    }

if __name__ == '__main__':
    print("Starting CSRF test server...")
    print(f"SECRET_KEY is set: {bool(app.config.get('SECRET_KEY'))}")
    print(f"SECRET_KEY value: {app.config.get('SECRET_KEY', 'NOT SET')[:10]}...")
    print(f"WTF_CSRF_ENABLED: {app.config.get('WTF_CSRF_ENABLED', True)}")
    app.run(debug=True, port=5001)