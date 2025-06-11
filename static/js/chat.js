// グローバル変数
let autoRefreshInterval = null;
let isLoading = false;
let lastMessageCount = 0;
let messageCount = 0;
let hasReloaded = false;
let reloadCount = 0;
const MAX_RELOADS = 2;

document.addEventListener('DOMContentLoaded', function() {
    // チャットコンテナの参照を取得
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
    
    // ユーザーロールを取得（data属性から）
    const userRole = document.querySelector('.container').getAttribute('data-user-role') || '';
    const isTeacher = userRole === 'teacher';
    
    // 学習ステップボタンのイベントリスナー（学生用）
    if (!isTeacher) {
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
    }
    
    // 教師機能ボタンのイベントリスナー（教師向け機能を非表示にするため、この部分は削除または無効化）
    // 以下のコードはコメントアウトまたは削除する
    /*
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
    */
    
    // 教師の場合は常に自由記述モードに設定
    if (isTeacher) {
        selectedStepField.value = 'teacher_free';
        selectedFunctionField.value = '';
        if (currentStepBadge) {
            currentStepBadge.textContent = '教師サポート';
        }
    }
    
    // チャットフォームの送信イベント
    const chatForm = document.getElementById('chat-form');
    chatForm.addEventListener('submit', function(e) {
        e.preventDefault(); // フォームのデフォルト送信を防止
        
        const message = messageInput.value.trim();
        if (!message) return;
        
        // 教師の場合は常に自由記述モードを使用
        if (isTeacher) {
            selectedStepField.value = 'teacher_free';
            selectedFunctionField.value = '';
        }
        
        // ユーザーメッセージを表示
        addMessage(message, true);
        
        // ローディングインジケータを表示
        const loadingId = addLoadingMessage();
        
        // URLからclass_idを取得
        const urlParams = new URLSearchParams(window.location.search);
        const classId = urlParams.get('class_id');
        
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
                function: selectedFunctionField.value,
                class_id: classId ? parseInt(classId) : null
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
                handleMessageSent(); // メッセージ送信後の処理
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
    function addMessage(content, isUser, isError = false, autoScroll = true) {
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
        
        // 自動スクロール（オプション）
        if (autoScroll) {
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
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
    
    // 自動更新機能（無効化）
    function startAutoRefresh() {
        // 自動更新を無効化
        return;
        // autoRefreshInterval = setInterval(() => {
        //     if (!isLoading) {
        //         loadMessages();
        //     }
        // }, 3000); // 3秒ごとに更新
    }

    // ローディング表示
    function showLoading() {
        const loadingIndicator = document.getElementById('loading-indicator');
        if (loadingIndicator) {
            loadingIndicator.style.display = 'block';
        }
        isLoading = true;
    }

    function hideLoading() {
        const loadingIndicator = document.getElementById('loading-indicator');
        if (loadingIndicator) {
            loadingIndicator.style.display = 'none';
        }
        isLoading = false;
    }

    // メッセージを読み込む関数
    function loadMessages() {
        showLoading();
        
        // URLからclass_idを取得
        const urlParams = new URLSearchParams(window.location.search);
        const classId = urlParams.get('class_id');
        
        fetch('/api/chat/messages' + (classId ? `?class_id=${classId}` : ''), {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrfToken
            }
        })
        .then(response => response.json())
        .then(data => {
            hideLoading();
            if (data.messages && data.messages.length !== lastMessageCount) {
                updateChatDisplay(data.messages);
                lastMessageCount = data.messages.length;
            }
        })
        .catch(error => {
            hideLoading();
            console.error('Error loading messages:', error);
        });
    }

    // チャット表示を更新する関数
    function updateChatDisplay(messages) {
        chatContainer.innerHTML = ''; // クリア
        messages.forEach(message => {
            addMessage(message.content, message.is_user, false, false);
        });
    }


    // 初期状態の設定
    if (isTeacher) {
        // 教師の場合は常に教師サポートモードに設定
        selectedStepField.value = 'teacher_free';
        selectedFunctionField.value = '';
        if (currentStepBadge) {
            currentStepBadge.textContent = '教師サポート';
        }
    } else {
        // 学生の場合は自由質問を初期選択
        const freeQuestionButton = document.querySelector('.step-select[data-step="free"]');
        if (freeQuestionButton) {
            freeQuestionButton.classList.add('active');
            selectedStepField.value = 'free';
        }
    }

    // ページ読み込み時に自動更新開始
    startAutoRefresh();
    
    // 初期メッセージ数を設定
    lastMessageCount = chatContainer.children.length;
    
    // ページロード時に最下部へスクロール
    scrollToBottom();
});

// 新しいメッセージ送信後の処理
function handleMessageSent() {
    messageCount++;
    
    // 2回までリロード
    if (reloadCount < MAX_RELOADS) {
        reloadCount++;
        setTimeout(() => {
            // 最下部にスクロールしてからリロード
            scrollToBottom();
            location.reload();
        }, 3000); // 3秒後にリロード
    }
}

// 最下部へのスクロール関数
function scrollToBottom() {
    const chatContainer = document.getElementById('chat-messages') || 
                         document.querySelector('.chat-container');
    if (chatContainer) {
        chatContainer.scrollTop = chatContainer.scrollHeight;
        
        // 最新メッセージを表示
        const messages = chatContainer.querySelectorAll('.message');
        if (messages.length > 0) {
            messages[messages.length - 1].scrollIntoView({ 
                behavior: 'smooth', 
                block: 'end' 
            });
        }
    }
}

// 既存の自動更新を無効化
if (typeof autoRefreshInterval !== 'undefined') {
    clearInterval(autoRefreshInterval);
}