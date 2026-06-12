// Markdown简单渲染（不依赖外部库）
function renderMarkdown(text) {
    if (!text) return text;
    
    // 转义HTML
    text = text.replace(/</g, '&lt;').replace(/>/g, '&gt;');
    
    // 代码块 ```code```
    text = text.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
        return `<pre><code class="language-${lang || 'text'}">${code.trim()}</code></pre>`;
    });
    
    // 行内代码 `code`
    text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
    
    // 粗体 **text**
    text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    
    // 斜体 *text*
    text = text.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    
    // 链接 [text](url)
    text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');
    
    // 标题
    text = text.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    text = text.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    text = text.replace(/^# (.+)$/gm, '<h1>$1</h1>');
    
    // 列表
    text = text.replace(/^- (.+)$/gm, '<li>$1</li>');
    text = text.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');
    
    // 换行
    text = text.replace(/\n/g, '<br>');
    
    return text;
}

// 格式化响应（增强版）
function formatResponseEnhanced(response) {
    if (typeof response === 'string') {
        return renderMarkdown(response);
    }
    
    if (response && response.result) {
        return renderMarkdown(response.result);
    }
    
    // 格式化JSON
    try {
        return `<pre><code>${JSON.stringify(response, null, 2)}</code></pre>`;
    } catch {
        return String(response);
    }
}

// 添加加载动画
function showLoading() {
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message assistant loading';
    loadingDiv.id = 'loading-message';
    loadingDiv.innerHTML = `
        <div class="message-content">
            <div class="loading-dots">
                <span></span><span></span><span></span>
            </div>
            <p>思考中...</p>
        </div>
    `;
    messagesContainer.appendChild(loadingDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function hideLoading() {
    const loading = document.getElementById('loading-message');
    if (loading) loading.remove();
}

// 增强的发送消息函数
async function sendMessageEnhanced() {
    const message = userInput.value.trim();
    if (!message) return;
    
    // 添加用户消息
    addMessage('user', message);
    userInput.value = '';
    sendBtn.disabled = true;
    
    // 显示加载动画
    showLoading();
    
    try {
        const response = await fetch(`${API_BASE}/api/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message })
        });
        
        const data = await response.json();
        
        // 隐藏加载动画
        hideLoading();
        
        if (data.error) {
            addMessage('system', `❌ 错误: ${data.error}`);
        } else {
            // 使用增强的格式化
            const responseText = formatResponseEnhanced(data.response);
            addMessageHTML('assistant', responseText);
        }
    } catch (error) {
        hideLoading();
        addMessage('system', `❌ 请求失败: ${error.message}`);
    } finally {
        sendBtn.disabled = false;
        userInput.focus();
    }
}

// 添加HTML消息（支持富文本）
function addMessageHTML(role, htmlContent) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = htmlContent;
    
    messageDiv.appendChild(contentDiv);
    messagesContainer.appendChild(messageDiv);
    
    // 滚动到底部
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    // 高亮代码块
    highlightCodeBlocks(contentDiv);
}

// 简单的代码高亮
function highlightCodeBlocks(container) {
    const codeBlocks = container.querySelectorAll('pre code');
    codeBlocks.forEach(block => {
        // 添加行号
        const lines = block.textContent.split('\n');
        if (lines.length > 3) {
            block.classList.add('with-line-numbers');
        }
    });
}

console.log('增强功能已加载: Markdown渲染, 加载动画, 代码高亮');