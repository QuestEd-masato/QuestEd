document.addEventListener('DOMContentLoaded', function() {
    // チャットコンテナの参照を取得 - chat-messagesではなくchat-containerに修正
    const chatContainer = document.getElementById('chat-container');
    // メッセージ入力フィールドの参照を取得
    const messageInput = document.getElementById('message-input');
    // 選択された学習ステップの隠しフィールド
    const selectedStepField = document.getElementById('selected-step');
    // 選択された教師機能の隠しフィールド
    const selectedFunctionField = document.getElementById('selected-function');
    // 現在選択されているステップまたは機能を表示するバッジ
    const currentStepBadge = document.getElementById('current-step');
    
    // CSRFトークンを取得
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    
    // 学習ステップボタンのイベントリスナー（学生用）
    const stepButtons = document.querySelectorAll('.step-select');
    stepButtons.forEach(button => {
        button.addEventListener('click', function() {
            // 以前の選択を解除
            stepButtons.forEach(btn => btn.classList.remove('active'));
            // 新しい選択をハイライト
            this.classList.add('active');
            // 選択されたステップを隠しフィールドに設定
            const stepId = this.getAttribute('data-step');
            selectedStepField.value = stepId;
            // 機能の選択をクリア（学生用）
            selectedFunctionField.value = '';
            // 現在選択されているステップを更新
            currentStepBadge.textContent = this.textContent.trim();
        });
    });
    
    // 教師機能ボタンのイベントリスナー（教師用）
    const functionButtons = document.querySelectorAll('.function-select');
    functionButtons.forEach(button => {
        button.addEventListener('click', function() {
            // 以前の選択を解除
            functionButtons.forEach(btn => btn.classList.remove('active'));
            // 新しい選択をハイライト
            this.classList.add('active');
            // 選択された機能を隠しフィールドに設定
            const functionId = this.getAttribute('data-function');
            selectedFunctionField.value = functionId;
            // ステップの選択をクリア（教師用）
            selectedStepField.value = '';
            // 現在選択されている機能を更新
            currentStepBadge.textContent = this.textContent.trim();
            
            // 新機能: 教師向け機能が選択された場合、入力フィールドにプロンプトを表示
            const functionPrompts = {
                'activity_summary': '要約したい活動記録を入力または貼り付けてください...',
                'evaluation': '評価文を生成したい生徒の活動内容を入力してください...',
                'curriculum': 'カリキュラム作成に必要な情報（対象学年、期間、テーマなど）を入力してください...',
                'practice_case': '実践事例として作成したい活動内容を入力してください...',
                'next_activity': 'これまでの活動内容を簡潔に説明してください...'
            };
            
            if (functionPrompts[functionId]) {
                messageInput.placeholder = functionPrompts[functionId];
            }
        });
    });
    
    // チャットフォームの送信イベント
    const chatForm = document.getElementById('chat-form');
    chatForm.addEventListener('submit', function(e) {
        e.preventDefault(); // フォームのデフォルト送信を防止
        
        const message = messageInput.value.trim();
        if (!message) return;
        
        // ユーザーメッセージを表示
        addMessage(message, true);
        
        // ローディングインジケータを表示
        const loadingId = addLoadingMessage();
        
        // APIリクエストを送信
        fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest', // AJAXリクエストであることを明示
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                message: message,
                step: selectedStepField.value,
                function: selectedFunctionField.value
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // ローディングメッセージを削除
            removeLoadingMessage(loadingId);
            
            // AIの応答を表示
            if (data.response) {
                addMessage(data.response, false);
            } else if (data.error) {
                addMessage('エラーが発生しました: ' + data.error, false, true);
            }
        })
        .catch(error => {
            // ローディングメッセージを削除
            removeLoadingMessage(loadingId);
            
            // エラーメッセージを表示
            addMessage('通信エラーが発生しました。再度お試しください。', false, true);
            console.error('Error:', error);
        });
        
        // 入力フィールドをクリア
        messageInput.value = '';
    });
    
    // メッセージをチャット領域に追加する関数
    function addMessage(content, isUser, isError = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${isUser ? 'user-message' : 'ai-message'}`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        if (isError) {
            contentDiv.style.backgroundColor = '#f8d7da';
            contentDiv.style.color = '#721c24';
        }
        
        // 改行を保持
        contentDiv.innerHTML = content.replace(/\n/g, '<br>');
        
        const timeDiv = document.createElement('div');
        timeDiv.innerHTML = `<small class="text-muted">${getCurrentTime()}</small>`;
        
        messageDiv.appendChild(contentDiv);
        messageDiv.appendChild(timeDiv);
        
        chatContainer.appendChild(messageDiv);
        
        // 自動スクロール
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
    
    // ローディングメッセージを追加する関数
    function addLoadingMessage() {
        const id = 'loading-' + Date.now();
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'chat-message ai-message loading-message';
        loadingDiv.id = id;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.innerHTML = '処理中...';
        
        loadingDiv.appendChild(contentDiv);
        chatContainer.appendChild(loadingDiv);
        
        // 自動スクロール
        chatContainer.scrollTop = chatContainer.scrollHeight;
        
        return id;
    }
    
    // ローディングメッセージを削除する関数
    function removeLoadingMessage(id) {
        const loadingElement = document.getElementById(id);
        if (loadingElement) {
            loadingElement.remove();
        }
    }
    
    // 現在時刻を取得する関数
    function getCurrentTime() {
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const day = String(now.getDate()).padStart(2, '0');
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        
        return `${year}-${month}-${day} ${hours}:${minutes}`;
    }
    
    // 初期状態で「自由質問」を選択状態にする
    const freeQuestionButton = document.querySelector('.step-select[data-step="free"]');
    if (freeQuestionButton) {
        freeQuestionButton.classList.add('active');
        selectedStepField.value = 'free';
    }
});