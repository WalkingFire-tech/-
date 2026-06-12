// API基础URL
const API_BASE = 'http://localhost:8000';

// DOM元素
const statusIndicator = document.getElementById('status-indicator');
const statusText = document.getElementById('status-text');
const messagesContainer = document.getElementById('messages');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');

// Markdown简单渲染
function renderMarkdown(text) {
    if (!text) return text;
    
    text = text.replace(/</g, '&lt;').replace(/>/g, '&gt;');
    text = text.replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
    text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
    text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    text = text.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    text = text.replace(/\n/g, '<br>');
    
    return text;
}

// 增强的格式化响应
function formatResponseEnhanced(response) {
    if (typeof response === 'string') {
        return renderMarkdown(response);
    }
    
    if (response && response.result) {
        return renderMarkdown(response.result);
    }
    
    try {
        return `<pre><code>${JSON.stringify(response, null, 2)}</code></pre>`;
    } catch {
        return String(response);
    }
}

// 添加HTML消息
function addMessageHTML(role, htmlContent) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = htmlContent;
    
    messageDiv.appendChild(contentDiv);
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    // 添加代码复制功能
    addCopyButtons(contentDiv);
}

// 添加代码复制按钮功能
function addCopyButtons(container) {
    const codeBlocks = container.querySelectorAll('pre');
    codeBlocks.forEach((pre, index) => {
        pre.addEventListener('click', (e) => {
            if (e.target === pre || e.target === pre.querySelector('code')) {
                const code = pre.querySelector('code').textContent;
                copyToClipboard(code, pre);
            }
        });
    });
}

// 复制到剪贴板
async function copyToClipboard(text, element) {
    try {
        await navigator.clipboard.writeText(text);
        
        // 显示复制成功提示
        const originalBefore = element.style.getPropertyValue('--before-content');
        element.style.cssText = element.style.cssText.replace('📋 复制', '✅ 已复制');
        
        setTimeout(() => {
            element.style.cssText = element.style.cssText.replace('✅ 已复制', '📋 复制');
        }, 2000);
    } catch (err) {
        console.error('复制失败:', err);
    }
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    checkHealth();
    loadStats();
    loadModels();
    
    // 定期刷新状态
    setInterval(checkHealth, 30000);
    setInterval(loadStats, 60000);
});

// 健康检查
async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE}/api/health`);
        const data = await response.json();
        
        statusIndicator.classList.add('connected');
        statusText.textContent = `已连接 (v${data.version})`;
    } catch (error) {
        statusIndicator.classList.remove('connected');
        statusText.textContent = '连接失败';
        console.error('健康检查失败:', error);
    }
}

// 加载统计信息
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/api/stats`);
        const data = await response.json();
        
        document.getElementById('stat-experiences').textContent = data.experiences || 0;
        document.getElementById('stat-active-rules').textContent = data.active_rules || 0;
        document.getElementById('stat-pending-rules').textContent = data.pending_rules || 0;
        document.getElementById('stat-models').textContent = data.models || 0;
    } catch (error) {
        console.error('加载统计失败:', error);
    }
}

// 加载模型列表
async function loadModels() {
    try {
        const response = await fetch(`${API_BASE}/api/models`);
        const data = await response.json();
        
        const modelList = document.getElementById('model-list');
        modelList.innerHTML = '';
        
        const modelSelect = document.getElementById('model-select');
        modelSelect.innerHTML = '<option value="auto">🔄 自动选择</option>';
        
        data.models.forEach(model => {
            // 添加到列表
            const li = document.createElement('li');
            li.textContent = `${model.name} (${model.type})`;
            li.dataset.model = model.name;
            li.style.cursor = 'pointer';
            li.onclick = () => {
                modelSelect.value = model.name;
                switchModel(model.name);
            };
            modelList.appendChild(li);
            
            // 添加到选择器
            const option = document.createElement('option');
            option.value = model.name;
            option.textContent = `🤖 ${model.name}`;
            modelSelect.appendChild(option);
        });
    } catch (error) {
        console.error('加载模型失败:', error);
    }
}

// 当前选择的模型
let selectedModel = 'auto';

// 切换模型
function switchModel(modelName) {
    selectedModel = modelName;
    
    // 更新UI提示
    const modelList = document.getElementById('model-list');
    const items = modelList.querySelectorAll('li');
    items.forEach(item => {
        if (item.dataset.model === modelName) {
            item.style.background = 'rgba(125, 211, 252, 0.3)';
            item.style.borderLeftColor = 'var(--primary-sky-deep)';
        } else {
            item.style.background = 'rgba(196, 181, 253, 0.1)';
            item.style.borderLeftColor = 'var(--accent-lavender)';
        }
    });
    
    // 显示提示
    const statusText = document.getElementById('status-text');
    const originalText = statusText.textContent;
    if (modelName === 'auto') {
        statusText.textContent = '🔄 自动选择模式';
    } else {
        statusText.textContent = `✓ 已选择: ${modelName}`;
    }
    
    setTimeout(() => {
        statusText.textContent = originalText;
    }, 2000);
    
    console.log('切换模型:', modelName);
}

// 发送消息
async function sendMessage() {
    const message = userInput.value.trim();
    if (!message) return;
    
    // 添加用户消息
    addMessage('user', message);
    userInput.value = '';
    sendBtn.disabled = true;
    
    try {
        // 构建请求体，包含选择的模型
        const requestBody = { message };
        if (selectedModel !== 'auto') {
            requestBody.model = selectedModel;
        }
        
        const response = await fetch(`${API_BASE}/api/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody)
        });
        
        const data = await response.json();
        
        if (data.error) {
            addMessage('system', `❌ 错误: ${data.error}`);
        } else {
            // 显示思考过程（透明度信息）
            if (data.intent) {
                const thinkingInfo = document.createElement('div');
                thinkingInfo.className = 'thinking-info';
                
                let modelInfo = selectedModel === 'auto' ? '自动选择' : selectedModel;
                
                thinkingInfo.innerHTML = `
                    <span class="thinking-label">💭 思考过程</span>
                    <span class="thinking-detail">
                        识别意图: <strong>${data.intent}</strong>
                        ${selectedModel !== 'auto' ? `| 指定模型: <strong>${selectedModel}</strong>` : ''}
                    </span>
                `;
                messagesContainer.appendChild(thinkingInfo);
            }
            
            // 使用增强的格式化
            const responseText = formatResponseEnhanced(data.response);
            addMessageHTML('assistant', responseText);
        }
    } catch (error) {
        addMessage('system', `❌ 请求失败: ${error.message}`);
    } finally {
        sendBtn.disabled = false;
        userInput.focus();
    }
}

// 格式化响应
function formatResponse(response) {
    if (typeof response === 'string') {
        return response;
    }
    
    if (response && response.result) {
        return response.result;
    }
    
    return JSON.stringify(response, null, 2);
}

// 添加消息到界面
function addMessage(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    // 处理多行文本
    const lines = content.split('\n');
    lines.forEach(line => {
        const p = document.createElement('p');
        p.textContent = line;
        contentDiv.appendChild(p);
    });
    
    messageDiv.appendChild(contentDiv);
    messagesContainer.appendChild(messageDiv);
    
    // 滚动到底部
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// 清空消息
function clearMessages() {
    messagesContainer.innerHTML = '';
    addMessage('system', '👋 消息已清空，继续对话吧！');
}

// 运行优化
async function runOptimize() {
    addMessage('system', '🎯 开始运行贝叶斯优化...');
    
    try {
        const response = await fetch(`${API_BASE}/api/optimize`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ iterations: 20 })
        });
        
        const data = await response.json();
        
        if (data.success) {
            addMessage('assistant', `✅ 优化完成: ${data.result}`);
        } else {
            addMessage('system', `❌ 优化失败: ${data.error}`);
        }
        
        loadStats();
    } catch (error) {
        addMessage('system', `❌ 优化请求失败: ${error.message}`);
    }
}

// 运行归纳
async function runInduction() {
    addMessage('system', '📚 开始运行归纳总结...');
    
    try {
        const response = await fetch(`${API_BASE}/api/induction`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ days: 7 })
        });
        
        const data = await response.json();
        
        if (data.success) {
            addMessage('assistant', 
                `✅ 归纳完成:\n` +
                `- 发现模式: ${data.patterns}个\n` +
                `- 生成规则: ${data.rules}条\n` +
                `- ${data.message}`
            );
        } else {
            addMessage('system', `❌ 归纳失败: ${data.error}`);
        }
        
        loadStats();
    } catch (error) {
        addMessage('system', `❌ 归纳请求失败: ${error.message}`);
    }
}

// 处理键盘事件
function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}