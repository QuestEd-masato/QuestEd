/**
 * QuestEd Admin Sidebar Killer
 * 管理画面のサイドバーを確実に削除するJavaScript
 */

(function() {
    'use strict';
    
    console.log('🔧 QuestEd Admin Sidebar Killer initialized');
    
    // サイドバー削除対象のセレクタ
    const SIDEBAR_SELECTORS = [
        '[class*="sidebar"]',
        '[id*="sidebar"]',
        '[class*="side-bar"]',
        '[id*="side-bar"]',
        '[class*="sidenav"]',
        '[id*="sidenav"]',
        'aside',
        'nav[class*="side"]',
        'nav[id*="side"]',
        '.admin-menu',
        '.admin-nav',
        '.admin-sidebar',
        '.left-panel',
        '.left-menu',
        '.side-panel',
        '.side-menu',
        '.navigation-panel',
        '.nav-panel',
        '.flask-admin-sidebar',
        '.nav-sidebar',
        '.sidebar-nav',
        '.main-sidebar',
        '.control-sidebar',
        '.admin-nav-link',
        '.admin-nav-menu',
        '.nav-admin'
    ];
    
    // CSS注入用のスタイル
    const KILLER_CSS = `
        ${SIDEBAR_SELECTORS.join(', ')} {
            display: none !important;
            visibility: hidden !important;
            width: 0 !important;
            height: 0 !important;
            max-width: 0 !important;
            max-height: 0 !important;
            min-width: 0 !important;
            min-height: 0 !important;
            overflow: hidden !important;
            opacity: 0 !important;
            pointer-events: none !important;
            position: absolute !important;
            left: -10000px !important;
            top: -10000px !important;
            z-index: -9999 !important;
            transform: translateX(-200%) scale(0) !important;
            margin: 0 !important;
            padding: 0 !important;
            border: none !important;
        }
        
        body, html {
            margin-left: 0 !important;
            padding-left: 0 !important;
            width: 100% !important;
        }
        
        .container, .container-fluid, main, .main, .content, .admin-content {
            margin-left: 0 !important;
            width: 100% !important;
            max-width: 100% !important;
        }
    `;
    
    /**
     * 緊急CSS注入
     */
    function injectKillerCSS() {
        const style = document.createElement('style');
        style.type = 'text/css';
        style.innerHTML = KILLER_CSS;
        style.setAttribute('data-sidebar-killer', 'true');
        
        // ヘッダーの最初に挿入（他のCSSより優先）
        if (document.head) {
            document.head.insertBefore(style, document.head.firstChild);
        } else {
            // ヘッダーがまだない場合
            if (document.documentElement) {
                document.documentElement.appendChild(style);
            }
        }
        
        console.log('💉 Killer CSS injected');
    }
    
    /**
     * サイドバー要素を物理的に削除
     */
    function destroySidebarElements() {
        let destroyedCount = 0;
        
        SIDEBAR_SELECTORS.forEach(selector => {
            try {
                const elements = document.querySelectorAll(selector);
                elements.forEach(element => {
                    if (element && element.parentNode) {
                        // 削除前にログ出力
                        console.log(`🗑️ Destroying sidebar element: ${element.tagName}.${element.className}`);
                        
                        // 要素を完全に削除
                        element.parentNode.removeChild(element);
                        destroyedCount++;
                    }
                });
            } catch (error) {
                console.warn(`⚠️ Error destroying ${selector}:`, error);
            }
        });
        
        if (destroyedCount > 0) {
            console.log(`🔥 Destroyed ${destroyedCount} sidebar elements`);
        }
        
        return destroyedCount;
    }
    
    /**
     * メインコンテンツの幅を調整
     */
    function adjustMainContent() {
        const mainSelectors = [
            'main',
            '.main',
            '.content',
            '.admin-content',
            '.container',
            '.container-fluid',
            '.content-wrapper',
            '.page-content'
        ];
        
        mainSelectors.forEach(selector => {
            const elements = document.querySelectorAll(selector);
            elements.forEach(element => {
                if (element && element.style) {
                    element.style.marginLeft = '0';
                    element.style.paddingLeft = '15px';
                    element.style.width = '100%';
                    element.style.maxWidth = '100%';
                }
            });
        });
        
        console.log('📐 Main content width adjusted');
    }
    
    /**
     * MutationObserverでサイドバーの動的生成を監視
     */
    function setupMutationObserver() {
        const observer = new MutationObserver(function(mutations) {
            let foundSidebar = false;
            
            mutations.forEach(function(mutation) {
                // 新しく追加されたノードをチェック
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        // 追加されたノード自体がサイドバーかチェック
                        SIDEBAR_SELECTORS.forEach(selector => {
                            try {
                                if (node.matches && node.matches(selector)) {
                                    console.log(`🚨 New sidebar detected: ${selector}`);
                                    foundSidebar = true;
                                }
                                
                                // 子要素にサイドバーがないかチェック
                                if (node.querySelectorAll) {
                                    const childSidebars = node.querySelectorAll(selector);
                                    if (childSidebars.length > 0) {
                                        console.log(`🚨 Child sidebars detected: ${childSidebars.length}`);
                                        foundSidebar = true;
                                    }
                                }
                            } catch (error) {
                                // セレクタエラーを無視
                            }
                        });
                    }
                });
                
                // 属性変更もチェック
                if (mutation.type === 'attributes') {
                    const target = mutation.target;
                    if (target && (mutation.attributeName === 'class' || mutation.attributeName === 'id')) {
                        SIDEBAR_SELECTORS.forEach(selector => {
                            try {
                                if (target.matches && target.matches(selector)) {
                                    console.log(`🚨 Sidebar attribute change detected`);
                                    foundSidebar = true;
                                }
                            } catch (error) {
                                // エラーを無視
                            }
                        });
                    }
                }
            });
            
            // サイドバーが検出されたら即座に削除
            if (foundSidebar) {
                console.log('🔄 Re-running sidebar destruction');
                setTimeout(function() {
                    destroySidebarElements();
                    adjustMainContent();
                }, 10);
            }
        });
        
        // 監視開始
        if (document.documentElement) {
            observer.observe(document.documentElement, {
                childList: true,
                subtree: true,
                attributes: true,
                attributeFilter: ['class', 'id', 'style']
            });
            
            console.log('👁️ MutationObserver started');
        }
        
        return observer;
    }
    
    /**
     * 定期的なサイドバーチェック
     */
    function setupPeriodicCheck() {
        const intervals = [100, 500, 1000, 2000, 5000]; // ミリ秒
        
        intervals.forEach(interval => {
            setTimeout(function() {
                const destroyed = destroySidebarElements();
                if (destroyed > 0) {
                    console.log(`⏰ Periodic check (${interval}ms): destroyed ${destroyed} elements`);
                    adjustMainContent();
                }
            }, interval);
        });
        
        // 長期間の定期チェック
        setInterval(function() {
            const destroyed = destroySidebarElements();
            if (destroyed > 0) {
                console.log(`🔄 Long-term check: destroyed ${destroyed} elements`);
                adjustMainContent();
            }
        }, 30000); // 30秒ごと
    }
    
    /**
     * 初期化処理
     */
    function initialize() {
        console.log('🚀 Initializing Sidebar Killer');
        
        // 1. 緊急CSS注入
        injectKillerCSS();
        
        // 2. 初期サイドバー削除
        destroySidebarElements();
        
        // 3. メインコンテンツ調整
        adjustMainContent();
        
        // 4. 監視システムセットアップ
        setupMutationObserver();
        
        // 5. 定期チェックセットアップ
        setupPeriodicCheck();
        
        console.log('✅ Sidebar Killer fully activated');
    }
    
    /**
     * DOMの状態に応じて初期化
     */
    if (document.readyState === 'loading') {
        // まだローディング中
        document.addEventListener('DOMContentLoaded', initialize);
    } else {
        // 既にDOMが読み込まれている
        initialize();
    }
    
    // ページロード完了時にも実行
    window.addEventListener('load', function() {
        setTimeout(initialize, 100);
    });
    
    // ページ離脱前にもう一度チェック
    window.addEventListener('beforeunload', function() {
        destroySidebarElements();
    });
    
    // グローバルに関数を公開（デバッグ用）
    window.QuestEdSidebarKiller = {
        destroy: destroySidebarElements,
        adjust: adjustMainContent,
        reinit: initialize,
        status: function() {
            console.log('🔍 Sidebar Killer Status Check');
            const remainingSidebars = document.querySelectorAll(SIDEBAR_SELECTORS.join(', '));
            console.log(`Remaining sidebars: ${remainingSidebars.length}`);
            remainingSidebars.forEach((el, index) => {
                console.log(`${index + 1}. ${el.tagName}.${el.className}`);
            });
            return remainingSidebars.length === 0;
        }
    };
    
})();