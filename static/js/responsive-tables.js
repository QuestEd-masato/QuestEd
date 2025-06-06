// レスポンシブテーブルの処理
document.addEventListener('DOMContentLoaded', function() {
    // 画面サイズに応じてテーブルをカード形式に変換
    function handleResponsiveTables() {
        const tables = document.querySelectorAll('.table-responsive table');
        const isMobile = window.innerWidth < 768;
        
        tables.forEach(table => {
            if (isMobile && !table.classList.contains('mobile-cards')) {
                // モバイル表示の処理
                table.classList.add('mobile-cards');
                convertTableToCards(table);
            } else if (!isMobile && table.classList.contains('mobile-cards')) {
                table.classList.remove('mobile-cards');
                restoreOriginalTable(table);
            }
        });
    }
    
    // テーブルをカード形式に変換
    function convertTableToCards(table) {
        const headers = Array.from(table.querySelectorAll('thead th')).map(th => th.textContent.trim());
        const rows = table.querySelectorAll('tbody tr');
        
        // 元のテーブルを保存
        if (!table.dataset.originalTable) {
            table.dataset.originalTable = table.innerHTML;
        }
        
        // カード形式のHTML生成
        let cardHTML = '<div class="mobile-table-cards">';
        
        rows.forEach(row => {
            const cells = row.querySelectorAll('td');
            cardHTML += '<div class="mobile-table-card">';
            
            cells.forEach((cell, index) => {
                if (headers[index] && cell.textContent.trim()) {
                    cardHTML += `
                        <div class="mobile-table-row">
                            <span class="mobile-table-label">${headers[index]}:</span>
                            <span class="mobile-table-value">${cell.innerHTML}</span>
                        </div>
                    `;
                }
            });
            
            cardHTML += '</div>';
        });
        
        cardHTML += '</div>';
        table.innerHTML = cardHTML;
    }
    
    // 元のテーブル形式に戻す
    function restoreOriginalTable(table) {
        if (table.dataset.originalTable) {
            table.innerHTML = table.dataset.originalTable;
        }
    }
    
    // 初期実行とリサイズイベント
    handleResponsiveTables();
    window.addEventListener('resize', debounce(handleResponsiveTables, 250));
    
    // スムーズスクロール
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    // カードホバーエフェクト
    function addCardHoverEffects() {
        const cards = document.querySelectorAll('.card');
        cards.forEach(card => {
            card.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-2px)';
                this.style.boxShadow = '0 4px 8px rgba(0,0,0,0.12)';
            });
            
            card.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0)';
                this.style.boxShadow = '';
            });
        });
    }
    
    // ボタンリップルエフェクト
    function addButtonRippleEffect() {
        document.querySelectorAll('.btn').forEach(button => {
            button.addEventListener('click', function(e) {
                const ripple = document.createElement('span');
                const rect = this.getBoundingClientRect();
                const size = Math.max(rect.width, rect.height);
                const x = e.clientX - rect.left - size / 2;
                const y = e.clientY - rect.top - size / 2;
                
                ripple.style.width = ripple.style.height = size + 'px';
                ripple.style.left = x + 'px';
                ripple.style.top = y + 'px';
                ripple.classList.add('ripple');
                
                this.appendChild(ripple);
                
                setTimeout(() => {
                    ripple.remove();
                }, 600);
            });
        });
    }
    
    // レスポンシブな画像とメディア
    function handleResponsiveMedia() {
        const images = document.querySelectorAll('img');
        images.forEach(img => {
            if (!img.style.maxWidth) {
                img.style.maxWidth = '100%';
                img.style.height = 'auto';
            }
        });
    }
    
    // フォームの改善
    function enhanceForms() {
        // フォーカス時のラベルアニメーション
        document.querySelectorAll('.form-control').forEach(input => {
            input.addEventListener('focus', function() {
                const label = this.previousElementSibling;
                if (label && label.tagName === 'LABEL') {
                    label.style.color = 'var(--btn-primary-text)';
                    label.style.fontSize = '0.875rem';
                }
            });
            
            input.addEventListener('blur', function() {
                const label = this.previousElementSibling;
                if (label && label.tagName === 'LABEL') {
                    label.style.color = '';
                    label.style.fontSize = '';
                }
            });
        });
    }
    
    // パフォーマンス最適化のためのデバウンス関数
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    // 遅延読み込み画像
    function lazyLoadImages() {
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        img.src = img.dataset.src;
                        img.classList.remove('lazy');
                        observer.unobserve(img);
                    }
                });
            });
            
            document.querySelectorAll('img[data-src]').forEach(img => {
                imageObserver.observe(img);
            });
        }
    }
    
    // アクセシビリティの改善
    function improveAccessibility() {
        // キーボードナビゲーション
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Tab') {
                document.body.classList.add('keyboard-navigation');
            }
        });
        
        document.addEventListener('mousedown', function() {
            document.body.classList.remove('keyboard-navigation');
        });
        
        // ARIAラベルの自動追加
        document.querySelectorAll('button:not([aria-label])').forEach(button => {
            if (!button.textContent.trim() && button.querySelector('i')) {
                const icon = button.querySelector('i');
                const iconClass = icon.className;
                if (iconClass.includes('fa-edit')) {
                    button.setAttribute('aria-label', '編集');
                } else if (iconClass.includes('fa-trash')) {
                    button.setAttribute('aria-label', '削除');
                } else if (iconClass.includes('fa-plus')) {
                    button.setAttribute('aria-label', '追加');
                }
            }
        });
    }
    
    // アニメーションの初期化
    function initAnimations() {
        // フェードインアニメーション
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };
        
        const fadeInObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }
            });
        }, observerOptions);
        
        document.querySelectorAll('.fade-in').forEach(el => {
            el.style.opacity = '0';
            el.style.transform = 'translateY(20px)';
            el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
            fadeInObserver.observe(el);
        });
    }
    
    // すべての機能を初期化
    addCardHoverEffects();
    addButtonRippleEffect();
    handleResponsiveMedia();
    enhanceForms();
    lazyLoadImages();
    improveAccessibility();
    initAnimations();
    
    // プログレスバーのアニメーション
    function animateProgressBars() {
        document.querySelectorAll('.progress-bar').forEach(bar => {
            const width = bar.style.width || bar.getAttribute('aria-valuenow') + '%';
            bar.style.width = '0%';
            setTimeout(() => {
                bar.style.width = width;
            }, 100);
        });
    }
    
    // ページ読み込み完了後にプログレスバーをアニメーション
    window.addEventListener('load', animateProgressBars);
    
    // 統計数値のカウントアップアニメーション
    function animateCounters() {
        document.querySelectorAll('.stat-number, .h2').forEach(counter => {
            const target = parseInt(counter.textContent);
            if (!isNaN(target) && target < 10000) {
                let current = 0;
                const increment = target / 30;
                const timer = setInterval(() => {
                    current += increment;
                    if (current >= target) {
                        counter.textContent = target;
                        clearInterval(timer);
                    } else {
                        counter.textContent = Math.floor(current);
                    }
                }, 50);
            }
        });
    }
    
    // ダッシュボードの統計数値をアニメーション
    if (document.querySelector('.dashboard-card')) {
        setTimeout(animateCounters, 500);
    }
});