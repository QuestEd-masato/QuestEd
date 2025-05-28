document.addEventListener('DOMContentLoaded', function() {
    // フラッシュメッセージの自動非表示
    const flashMessages = document.querySelectorAll('.flash-messages .message');
    
    flashMessages.forEach(message => {
        setTimeout(() => {
            message.style.opacity = '0';
            message.style.transition = 'opacity 0.5s ease-in-out';
            setTimeout(() => {
                message.style.display = 'none';
            }, 500);
        }, 3000);
    });
    
    // フォームバリデーション
    const forms = document.querySelectorAll('form[data-validate="true"]');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            let isValid = true;
            
            // 必須フィールドのチェック
            const requiredFields = form.querySelectorAll('[required]');
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    isValid = false;
                    field.classList.add('is-invalid');
                    
                    // エラーメッセージがなければ追加
                    let errorMsg = field.nextElementSibling;
                    if (!errorMsg || !errorMsg.classList.contains('error-message')) {
                        errorMsg = document.createElement('div');
                        errorMsg.classList.add('error-message');
                        errorMsg.textContent = 'このフィールドは必須です';
                        field.parentNode.insertBefore(errorMsg, field.nextSibling);
                    }
                } else {
                    field.classList.remove('is-invalid');
                    
                    // エラーメッセージがあれば削除
                    const errorMsg = field.nextElementSibling;
                    if (errorMsg && errorMsg.classList.contains('error-message')) {
                        errorMsg.remove();
                    }
                }
            });
            
            // パスワード確認のチェック
            const password = form.querySelector('input[name="password"]');
            const confirmPassword = form.querySelector('input[name="confirm_password"]');
            
            if (password && confirmPassword && password.value !== confirmPassword.value) {
                isValid = false;
                confirmPassword.classList.add('is-invalid');
                
                // エラーメッセージがなければ追加
                let errorMsg = confirmPassword.nextElementSibling;
                if (!errorMsg || !errorMsg.classList.contains('error-message')) {
                    errorMsg = document.createElement('div');
                    errorMsg.classList.add('error-message');
                    errorMsg.textContent = 'パスワードが一致しません';
                    confirmPassword.parentNode.insertBefore(errorMsg, confirmPassword.nextSibling);
                }
            }
            
            if (!isValid) {
                e.preventDefault();
            }
        });
    });
    
    // 確認ダイアログ付きボタン
    const confirmButtons = document.querySelectorAll('[data-confirm]');
    
    confirmButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const message = this.getAttribute('data-confirm');
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });
    
    // ファイル選択時のプレビュー表示
    const fileInputs = document.querySelectorAll('input[type="file"][data-preview]');
    
    fileInputs.forEach(input => {
        const previewId = input.getAttribute('data-preview');
        const previewElement = document.getElementById(previewId);
        
        if (previewElement) {
            input.addEventListener('change', function() {
                if (this.files && this.files[0]) {
                    const reader = new FileReader();
                    
                    reader.onload = function(e) {
                        previewElement.src = e.target.result;
                        previewElement.style.display = 'block';
                    };
                    
                    reader.readAsDataURL(this.files[0]);
                }
            });
        }
    });
    
    // タブ切り替え機能
    const tabButtons = document.querySelectorAll('.tab-btn');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            const tabId = this.getAttribute('data-tab');
            
            if (tabId) {
                // タブコンテンツを全て非表示
                document.querySelectorAll('.tab-content').forEach(tab => {
                    tab.classList.remove('active');
                });
                
                // タブボタンの選択状態をリセット
                document.querySelectorAll('.tab-btn').forEach(btn => {
                    btn.classList.remove('active');
                });
                
                // 選択したタブとそのコンテンツをアクティブに
                document.getElementById(tabId).classList.add('active');
                this.classList.add('active');
            }
        });
    });
});

// 日付フォーマット用ヘルパー関数
function formatDate(date) {
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    return new Date(date).toLocaleDateString('ja-JP', options);
}

// テキストの省略表示用関数
function truncateText(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substr(0, maxLength) + '...';
}

// nl2brのJavaScript版（テンプレートでnl2brフィルタが使えない場合に使用）
function nl2br(str) {
    if (typeof str !== 'string') return str;
    return str.replace(/\n/g, '<br>');
}