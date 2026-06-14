// API基础URL
const API_BASE = 'http://localhost:8000';

// DOM元素（延迟获取）
let statusIndicator, statusText, messagesContainer, userInput, sendBtn;

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
    // 初始化DOM元素
    statusIndicator = document.getElementById('status-indicator');
    statusText = document.getElementById('status-text');
    messagesContainer = document.getElementById('messages');
    userInput = document.getElementById('user-input');
    sendBtn = document.getElementById('send-btn');
    
    checkHealth();
    loadStats();
    loadModels();
    
    // 定期刷新状态
    setInterval(checkHealth, 30000);
    setInterval(loadStats, 60000);
});

// 健康检查
async function checkHealth() {
    const indicator = document.getElementById('status-indicator');
    const text = document.getElementById('status-text');
    
    if (!indicator || !text) return;
    
    try {
        const response = await fetch(`${API_BASE}/api/health`);
        const data = await response.json();
        
        indicator.classList.add('connected');
        text.textContent = `已连接 (v${data.version})`;
    } catch (error) {
        indicator.classList.remove('connected');
        text.textContent = '连接失败';
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
    if (modelList) {
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
    }
    
    // 显示提示
    const statusText = document.getElementById('status-text');
    if (statusText) {
        const originalText = statusText.textContent;
        if (modelName === 'auto') {
            statusText.textContent = '🔄 自动选择模式';
        } else {
            statusText.textContent = `✓ 已选择: ${modelName}`;
        }
        
        setTimeout(() => {
            const currentText = document.getElementById('status-text');
            if (currentText) currentText.textContent = originalText;
        }, 2000);
    }
    
    console.log('切换模型:', modelName);
}

// 发送消息
async function sendMessage() {
    const input = document.getElementById('user-input');
    const btn = document.getElementById('send-btn');
    const container = document.getElementById('messages');
    
    if (!input || !btn || !container) return;
    
    const message = input.value.trim();
    if (!message) return;
    
    // 添加用户消息
    addMessage('user', message);
    input.value = '';
    btn.disabled = true;
    
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
                container.appendChild(thinkingInfo);
            }
            
            // 使用增强的格式化
            const responseText = formatResponseEnhanced(data.response);
            
            // 添加助手消息（带反馈按钮）
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message assistant';
            
            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';
            contentDiv.innerHTML = responseText;
            
            // 添加反馈按钮
            const feedbackDiv = document.createElement('div');
            feedbackDiv.className = 'feedback-buttons';
            feedbackDiv.innerHTML = `
                <button class="feedback-btn positive" onclick="sendFeedback(1, this)" title="好评">👍</button>
                <button class="feedback-btn negative" onclick="sendFeedback(-1, this)" title="差评">👎</button>
            `;
            
            messageDiv.appendChild(contentDiv);
            messageDiv.appendChild(feedbackDiv);
            container.appendChild(messageDiv);
            
            // 添加代码复制功能
            addCopyButtons(contentDiv);
            
            container.scrollTop = container.scrollHeight;

        }
    } catch (error) {
        addMessage('system', `❌ 请求失败: ${error.message}`);
    } finally {
        btn.disabled = false;
        input.focus();
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

// 发送反馈
async function sendFeedback(score, buttonElement) {
    try {
        // 更新按钮状态
        const feedbackDiv = buttonElement.parentElement;
        const buttons = feedbackDiv.querySelectorAll('.feedback-btn');
        buttons.forEach(btn => btn.disabled = true);
        
        buttonElement.style.opacity = '1';
        buttonElement.style.transform = 'scale(1.2)';
        
        // 发送反馈到后端
        const response = await fetch(`${API_BASE}/api/feedback`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ score: score })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // 显示感谢提示
            const thankYou = document.createElement('span');
            thankYou.className = 'feedback-thank';
            thankYou.textContent = score > 0 ? ' ✓ 感谢好评！' : ' ✓ 已收到反馈';
            feedbackDiv.appendChild(thankYou);
            
            setTimeout(() => {
                thankYou.remove();
            }, 3000);
        }
        
    } catch (error) {
        console.error('反馈发送失败:', error);
        // 恢复按钮状态
        const feedbackDiv = buttonElement.parentElement;
        const buttons = feedbackDiv.querySelectorAll('.feedback-btn');
        buttons.forEach(btn => btn.disabled = false);
    }
}

// ========== 外脑配置功能 ==========

// 显示外脑配置模态框
function showExternalModelConfig() {
    document.getElementById('external-model-modal').style.display = 'block';
    loadExternalModels();
}

// 关闭外脑配置模态框
function closeExternalModelConfig() {
    document.getElementById('external-model-modal').style.display = 'none';
}

// 加载外部模型列表
async function loadExternalModels() {
    try {
        const response = await fetch(`${API_BASE}/api/external_models`);
        const data = await response.json();
        
        const listDiv = document.getElementById('external-models-list');
        listDiv.innerHTML = '';
        
        if (data.models && data.models.length > 0) {
            data.models.forEach(model => {
                const modelDiv = document.createElement('div');
                modelDiv.className = 'model-item';
                modelDiv.innerHTML = `
                    <div class="model-header">
                        <strong>${model.name}</strong>
                        <div class="model-actions">
                            <button onclick="testModel('${model.name}')" class="btn-small">测试</button>
                            <button onclick="deleteModel('${model.name}')" class="btn-small btn-danger">删除</button>
                        </div>
                    </div>
                    <div class="model-info">
                        <div>API地址: ${model.api_url}</div>
                        <div>密钥: ●●●●●●●●</div>
                        <div>配额: ${model.used_today}/${model.daily_limit} 请求/日</div>
                    </div>
                `;
                listDiv.appendChild(modelDiv);
            });
        } else {
            listDiv.innerHTML = '<p class="no-models">暂无配置的外部模型</p>';
        }
    } catch (error) {
        console.error('加载模型失败:', error);
    }
}

// 显示添加模型表单
function showAddModelForm() {
    document.getElementById('add-model-modal').style.display = 'block';
}

// 关闭添加模型表单
function closeAddModelForm() {
    document.getElementById('add-model-modal').style.display = 'none';
    document.getElementById('add-model-form').reset();
}

// 添加模型表单提交
document.getElementById('add-model-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const name = document.getElementById('model-name').value;
    const apiUrl = document.getElementById('model-api-url').value;
    const apiKey = document.getElementById('model-api-key').value;
    const dailyLimit = parseInt(document.getElementById('model-daily-limit').value);
    
    try {
        const response = await fetch(`${API_BASE}/api/external_models`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                name: name,
                api_url: apiUrl,
                api_key: apiKey,
                daily_limit: dailyLimit
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert('✓ 模型已添加');
            closeAddModelForm();
            loadExternalModels();
        } else {
            alert('✗ 添加失败: ' + data.error);
        }
    } catch (error) {
        alert('✗ 添加失败: ' + error.message);
    }
});

// 测试模型连接
async function testModel(name) {
    try {
        const response = await fetch(`${API_BASE}/api/external_models/test`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({name: name})
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert(`✓ ${name}: 连接成功`);
        } else {
            alert(`✗ ${name}: ${data.message}`);
        }
    } catch (error) {
        alert('✗ 测试失败: ' + error.message);
    }
}

// 删除模型
async function deleteModel(name) {
    if (!confirm(`确定删除模型 "${name}" 吗？`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/external_models/${name}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert('✓ 模型已删除');
            loadExternalModels();

// 文件夹学习功能
function showFolderLearn() {
    document.getElementById('folder-learn-modal').style.display = 'block';
}

function closeFolderLearn() {
    document.getElementById('folder-learn-modal').style.display = 'none';
}

async function previewFolder() {
    const folderPath = document.getElementById('folder-path').value;
    const fileTypes = document.getElementById('file-types').value;
    
    if (!folderPath) {
        alert('请输入文件夹路径');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/folder/preview`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                path: folderPath,
                file_types: fileTypes
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            const preview = document.getElementById('folder-preview');
            preview.innerHTML = `
                <p><strong>找到 ${data.files.length} 个文件:</strong></p>
                <ul style="margin: 5px 0; padding-left: 20px; max-height: 150px; overflow-y: auto;">
                    ${data.files.slice(0, 20).map(f => `<li>${f}</li>`).join('')}
                    ${data.files.length > 20 ? `<li>... 还有 ${data.files.length - 20} 个文件</li>` : ''}
                </ul>
            `;
        } else {
            alert('预览失败: ' + data.error);
        }
    } catch (error) {
        alert('预览失败: ' + error.message);
    }
}

async function startFolderLearn() {
    const folderPath = document.getElementById('folder-path').value;
    const fileTypes = document.getElementById('file-types').value;
    const learnMode = document.getElementById('learn-mode').value;
    
    if (!folderPath) {
        alert('请输入文件夹路径');
        return;
    }
    
    if (!confirm(`开始从文件夹学习？\n路径: ${folderPath}\n模式: ${learnMode}`)) {
        return;
    }
    
    closeFolderLearn();
    
    addMessageHTML('user', `<p>📁 开始从文件夹学习: ${folderPath}</p>`);
    
    try {
        const response = await fetch(`${API_BASE}/api/folder/learn`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                path: folderPath,
                file_types: fileTypes,
                mode: learnMode
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            addMessageHTML('assistant', `
                <p>✅ 学习完成!</p>
                <p>处理文件: ${data.processed} 个</p>
                <p>提取知识点: ${data.knowledge || 0} 条</p>
                ${data.summary ? `<p><strong>摘要:</strong><br>${data.summary}</p>` : ''}
            `);
        } else {
            addMessageHTML('assistant', `<p>❌ 学习失败: ${data.error}</p>`);
        }
    } catch (error) {
        addMessageHTML('assistant', `<p>❌ 学习失败: ${error.message}</p>`);
    }
        } else {
            alert('✗ 删除失败: ' + data.error);
        }
    } catch (error) {
        alert('✗ 删除失败: ' + error.message);
    }
}