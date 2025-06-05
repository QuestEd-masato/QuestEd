# app/auth/password_validator.py
"""パスワード検証ユーティリティ"""
import re
import secrets
import string

def validate_password(password):
    """
    パスワードの強度を検証する
    
    Args:
        password (str): 検証するパスワード
        
    Returns:
        tuple: (is_valid: bool, errors: list)
    """
    errors = []
    
    # 最小長さチェック
    if len(password) < 12:
        errors.append("パスワードは12文字以上である必要があります")
    
    # 大文字チェック
    if not re.search(r'[A-Z]', password):
        errors.append("パスワードには大文字を含む必要があります")
    
    # 小文字チェック
    if not re.search(r'[a-z]', password):
        errors.append("パスワードには小文字を含む必要があります")
    
    # 数字チェック
    if not re.search(r'\d', password):
        errors.append("パスワードには数字を含む必要があります")
    
    # 特殊文字チェック
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("パスワードには特殊文字（!@#$%^&*など）を含む必要があります")
    
    # 一般的な弱いパスワードのチェック
    common_passwords = [
        'password123', 'admin123', 'quest123', '123456789012', 
        'password1234', 'questionnaire', 'education123',
        'password!@#', 'Password123!', 'Admin123!',
        'Questionnaire1!', 'Education123!'
    ]
    
    if password.lower() in [p.lower() for p in common_passwords]:
        errors.append("このパスワードは一般的すぎるため使用できません")
    
    # 連続する文字のチェック
    if has_sequential_chars(password):
        errors.append("連続する文字（abc、123など）は使用できません")
    
    # 反復する文字のチェック
    if has_repeated_chars(password):
        errors.append("同じ文字の連続（aaa、111など）は使用できません")
    
    return len(errors) == 0, errors

def has_sequential_chars(password, min_length=3):
    """連続する文字があるかチェック"""
    sequences = [
        'abcdefghijklmnopqrstuvwxyz',
        'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
        '0123456789',
        'qwertyuiop',  # キーボード配列
        'asdfghjkl',
        'zxcvbnm'
    ]
    
    for seq in sequences:
        for i in range(len(seq) - min_length + 1):
            if seq[i:i+min_length] in password:
                return True
            # 逆順もチェック
            if seq[i:i+min_length][::-1] in password:
                return True
    
    return False

def has_repeated_chars(password, min_length=3):
    """同じ文字の連続があるかチェック"""
    for i in range(len(password) - min_length + 1):
        if len(set(password[i:i+min_length])) == 1:
            return True
    return False

def generate_secure_password(length=16):
    """
    セキュアなパスワードを生成する
    
    Args:
        length (int): パスワードの長さ（デフォルト16文字）
        
    Returns:
        str: 生成されたパスワード
    """
    if length < 12:
        length = 12
    
    # 文字セットを定義
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    special_chars = "!@#$%^&*(),.?\":{}|<>"
    
    # 最低限必要な文字を確保
    password = [
        secrets.choice(lowercase),
        secrets.choice(uppercase),
        secrets.choice(digits),
        secrets.choice(special_chars)
    ]
    
    # 残りの文字をランダムに選択
    all_chars = lowercase + uppercase + digits + special_chars
    for _ in range(length - 4):
        password.append(secrets.choice(all_chars))
    
    # パスワードをシャッフル
    secrets.SystemRandom().shuffle(password)
    
    return ''.join(password)

def get_password_strength_score(password):
    """
    パスワードの強度スコアを計算する（0-100）
    
    Args:
        password (str): パスワード
        
    Returns:
        int: 強度スコア（0-100）
    """
    score = 0
    
    # 長さによる加点
    if len(password) >= 8:
        score += 10
    if len(password) >= 12:
        score += 15
    if len(password) >= 16:
        score += 10
    
    # 文字種による加点
    if re.search(r'[a-z]', password):
        score += 10
    if re.search(r'[A-Z]', password):
        score += 10
    if re.search(r'\d', password):
        score += 10
    if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        score += 15
    
    # 多様性による加点
    unique_chars = len(set(password))
    if unique_chars >= len(password) * 0.7:
        score += 10
    
    # 弱いパターンによる減点
    if has_sequential_chars(password):
        score -= 20
    if has_repeated_chars(password):
        score -= 20
    
    # 一般的なパスワードによる減点
    common_patterns = ['password', '123456', 'qwerty', 'admin']
    for pattern in common_patterns:
        if pattern.lower() in password.lower():
            score -= 30
            break
    
    return max(0, min(100, score))

def get_password_strength_label(score):
    """
    スコアから強度ラベルを取得
    
    Args:
        score (int): 強度スコア
        
    Returns:
        tuple: (label: str, color_class: str)
    """
    if score >= 80:
        return "非常に強い", "text-success"
    elif score >= 60:
        return "強い", "text-primary"
    elif score >= 40:
        return "普通", "text-warning"
    elif score >= 20:
        return "弱い", "text-danger"
    else:
        return "非常に弱い", "text-danger"