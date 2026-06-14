// ==================== 全局配置 ====================
const API_BASE = 'http://localhost:8000';

// ==================== 全局变量 ====================
let selectedModel = 'auto';

// ==================== 工具函数 ====================
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

function formatResponseEnhanced(response) {
    if (typeof response === 'string') return renderMarkdown(response);
    if (response && response.result) return renderMarkdown(response.result);
    try {
        return `<pre><code>${JSON.stringify(response, null, 2)}</code></pre>`;
    } catch {
        return String(response);
    }
}

function addCopyButtons(container) {
    const codeBlocks = container.querySelectorAll('pre');
    codeBlocks.forEach(pre => {
        pre.addEventListener('click', (e) => {
            if (e.target === pre || e.target === pre.querySelector('code')) {
                const code = pre.querySelector('code').textContent;
                copyToClipboard(code, pre);
            }
        });
    });
}

async function copyToClipboard(text, element) {
    try {
        await navigator.clipboard.writeText(text);
        const originalStyle = element.style.cssText;
        element.style.backgroundColor = '#e8f5e9';
        setTimeout(() => element.style.cssText = originalStyle, 1000);
    } catch (err) {
        console.error('复制失败:', err);
    }
}

// ==================== 消息界面操作 ====================
function addMessage(role, content) {
    const messagesDiv = document.getElementById('messages');
    if (!messagesDiv) return;
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerText = content;
    messageDiv.appendChild(contentDiv);
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function addMessageHTML(role, htmlContent) {
    const messagesDiv = document.getElementById('messages');
    if (!messagesDiv) return;
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = htmlContent;
    messageDiv.appendChild(contentDiv);
    messagesDiv.appendChild(messageDiv);
    addCopyButtons(contentDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// ==================== 发送消息（全局函数） ====================
async function sendMessage() {
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const message = userInput.value.trim();
    if (!message) return;

    addMessage('user', message);
    userInput.value = '';
    sendBtn.disabled = true;

    try {
        const requestBody = { message };
        if (selectedModel !== 'auto') requestBody.model = selectedModel;

        const response = await fetch(`${API_BASE}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });
        const data = await response.json();

        if (data.error) {
            addMessage('system', `❌ 错误: ${data.error}`);
        } else {
            // 显示思考过程
            if (data.intent) {
                const thinkingDiv = document.createElement('div');
                thinkingDiv.className = 'thinking-info';
                thinkingDiv.innerHTML = `<span class="thinking-label">💭 思考过程</span> <span class="thinking-detail">识别意图: <strong>${data.intent}</strong></span>`;
                document.getElementById('messages').appendChild(thinkingDiv);
            }
            const responseHtml = formatResponseEnhanced(data.response);
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message assistant';
            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';
            contentDiv.innerHTML = responseHtml;
            const feedbackDiv = document.createElement('div');
            feedbackDiv.className = 'feedback-buttons';
            feedbackDiv.innerHTML = `
                <button class="feedback-btn positive" onclick="sendFeedback(1, this)">👍</button>
                <button class="feedback-btn negative" onclick="sendFeedback(-1, this)">👎</button>
            `;
            messageDiv.appendChild(contentDiv);
            messageDiv.appendChild(feedbackDiv);
            document.getElementById('messages').appendChild(messageDiv);
            addCopyButtons(contentDiv);
            document.getElementById('messages').scrollTop = document.getElementById('messages').scrollHeight;
        }
    } catch (error) {
        addMessage('system', `❌ 请求失败: ${error.message}`);
    } finally {
        sendBtn.disabled = false;
        userInput.focus();
    }
}

function clearMessages() {
    const messagesDiv = document.getElementById('messages');
    if (messagesDiv) {
        messagesDiv.innerHTML = '';
        addMessage('system', '👋 消息已清空，继续对话吧！');
    }
}

function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

// ==================== 反馈（全局） ====================
async function sendFeedback(score, buttonElement) {
    try {
        const feedbackDiv = buttonElement.parentElement;
        const buttons = feedbackDiv.querySelectorAll('.feedback-btn');
        buttons.forEach(btn => btn.disabled = true);
        buttonElement.style.opacity = '1';
        buttonElement.style.transform = 'scale(1.1)';

        const response = await fetch(`${API_BASE}/api/feedback`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ score })
        });
        const data = await response.json();
        if (data.success) {
            const thankSpan = document.createElement('span');
            thankSpan.className = 'feedback-thank';
            thankSpan.textContent = score > 0 ? ' ✓ 感谢好评！' : ' ✓ 已收到反馈';
            feedbackDiv.appendChild(thankSpan);
            setTimeout(() => thankSpan.remove(), 3000);
        }
    } catch (error) {
        console.error('反馈失败:', error);
        const feedbackDiv = buttonElement.parentElement;
        const buttons = feedbackDiv.querySelectorAll('.feedback-btn');
        buttons.forEach(btn => btn.disabled = false);
    }
}

// ==================== 模型切换 ====================
function switchModel(modelName) {
    selectedModel = modelName;
    const modelList = document.getElementById('model-list');
    if (modelList) {
        const items = modelList.querySelectorAll('li');
        items.forEach(item => {
            if (item.dataset.model === modelName) {
                item.style.background = 'rgba(125, 211, 252, 0.3)';
                item.style.borderLeftColor = '#3b82f6';
            } else {
                item.style.background = 'rgba(196, 181, 253, 0.1)';
                item.style.borderLeftColor = '#a78bfa';
            }
        });
    }
    const statusText = document.getElementById('status-text');
    if (statusText) {
        const originalText = statusText.textContent;
        statusText.textContent = modelName === 'auto' ? '🔄 自动选择模式' : `✓ 已选择: ${modelName}`;
        setTimeout(() => { statusText.textContent = originalText; }, 2000);
    }
    console.log('切换模型:', modelName);
}

// ==================== 后端交互（全局） ====================
async function runOptimize() {
    addMessage('system', '🎯 开始运行贝叶斯优化...');
    try {
        const response = await fetch(`${API_BASE}/api/optimize`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
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

async function runInduction() {
    addMessage('system', '📚 开始运行归纳总结...');
    try {
        const response = await fetch(`${API_BASE}/api/induction`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ days: 7 })
        });
        const data = await response.json();
        if (data.success) {
            addMessage('assistant', `✅ 归纳完成:\n- 发现模式: ${data.patterns}个\n- 生成规则: ${data.rules}条\n- ${data.message}`);
        } else {
            addMessage('system', `❌ 归纳失败: ${data.error}`);
        }
        loadStats();
    } catch (error) {
        addMessage('system', `❌ 归纳请求失败: ${error.message}`);
    }
}

// 健康检查和统计
async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE}/api/health`);
        const data = await response.json();
        const indicator = document.getElementById('status-indicator');
        const statusText = document.getElementById('status-text');
        if (indicator) indicator.classList.add('connected');
        if (statusText) statusText.textContent = `已连接 (v${data.version})`;
    } catch (error) {
        const indicator = document.getElementById('status-indicator');
        const statusText = document.getElementById('status-text');
        if (indicator) indicator.classList.remove('connected');
        if (statusText) statusText.textContent = '连接失败';
        console.error('健康检查失败:', error);
    }
}

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

async function loadModels() {
    try {
        const response = await fetch(`${API_BASE}/api/models`);
        const data = await response.json();
        const modelList = document.getElementById('model-list');
        const modelSelect = document.getElementById('model-select');
        if (modelList) modelList.innerHTML = '';
        if (modelSelect) {
            modelSelect.innerHTML = '<option value="auto">🔄 自动选择</option>';
        }
        data.models.forEach(model => {
            if (modelList) {
                const li = document.createElement('li');
                li.textContent = `${model.name} (${model.type})`;
                li.dataset.model = model.name;
                li.style.cursor = 'pointer';
                li.onclick = () => switchModel(model.name);
                modelList.appendChild(li);
            }
            if (modelSelect) {
                const option = document.createElement('option');
                option.value = model.name;
                option.textContent = `🤖 ${model.name}`;
                modelSelect.appendChild(option);
            }
        });
    } catch (error) {
        console.error('加载模型失败:', error);
    }
}

// ==================== 外脑配置（全局） ====================
function showExternalModelConfig() {
    const modal = document.getElementById('external-model-modal');
    if (modal) modal.style.display = 'block';
    loadExternalModels();
}
function closeExternalModelConfig() {
    const modal = document.getElementById('external-model-modal');
    if (modal) modal.style.display = 'none';
}
async function loadExternalModels() {
    try {
        const response = await fetch(`${API_BASE}/api/external_models`);
        const data = await response.json();
        const container = document.getElementById('external-models-list');
        if (!container) return;
        container.innerHTML = '';
        if (data.models && data.models.length > 0) {
            data.models.forEach(model => {
                const div = document.createElement('div');
                div.className = 'model-item';
                div.innerHTML = `
                    <div class="model-header">
                        <strong>${escapeHtml(model.name)}</strong>
                        <div class="model-actions">
                            <button onclick="testModel('${escapeHtml(model.name)}')" class="btn-small">测试</button>
                            <button onclick="deleteModel('${escapeHtml(model.name)}')" class="btn-small btn-danger">删除</button>
                        </div>
                    </div>
                    <div class="model-info">
                        <div>API地址: ${escapeHtml(model.api_url)}</div>
                        <div>密钥: ●●●●●●●●</div>
                        <div>配额: ${model.used_today}/${model.daily_limit} 请求/日</div>
                    </div>
                `;
                container.appendChild(div);
            });
        } else {
            container.innerHTML = '<p class="no-models">暂无配置的外部模型</p>';
        }
    } catch (error) {
        console.error('加载外部模型失败:', error);
    }
}
function showAddModelForm() {
    const modal = document.getElementById('add-model-modal');
    if (modal) modal.style.display = 'block';
}
function closeAddModelForm() {
    const modal = document.getElementById('add-model-modal');
    if (modal) modal.style.display = 'none';
    const form = document.getElementById('add-model-form');
    if (form) form.reset();
}
async function testModel(name) {
    try {
        const response = await fetch(`${API_BASE}/api/external_models/test`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });
        const data = await response.json();
        alert(data.success ? `✓ ${name}: 连接成功` : `✗ ${name}: ${data.message}`);
    } catch (error) {
        alert(`✗ 测试失败: ${error.message}`);
    }
}
async function deleteModel(name) {
    if (!confirm(`确定删除模型 "${name}" 吗？`)) return;
    try {
        const response = await fetch(`${API_BASE}/api/external_models/${name}`, { method: 'DELETE' });
        const data = await response.json();
        if (data.success) {
            alert('✓ 模型已删除');
            loadExternalModels();
        } else {
            alert('✗ 删除失败: ' + data.error);
        }
    } catch (error) {
        alert('✗ 删除失败: ' + error.message);
    }
}
// 添加模型表单提交处理（需要绑定事件，在初始化时完成，这里提供全局函数供onclick使用）
async function addModelSubmit(event) {
    event.preventDefault();
    const name = document.getElementById('model-name').value;
    const apiUrl = document.getElementById('model-api-url').value;
    const apiKey = document.getElementById('model-api-key').value;
    const dailyLimit = parseInt(document.getElementById('model-daily-limit').value);
    try {
        const response = await fetch(`${API_BASE}/api/external_models`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, api_url: apiUrl, api_key: apiKey, daily_limit: dailyLimit })
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
}

// ==================== 文件夹学习（全局） ====================
function showFolderLearn() {
    const modal = document.getElementById('folder-learn-modal');
    if (modal) modal.style.display = 'block';
}
function closeFolderLearn() {
    const modal = document.getElementById('folder-learn-modal');
    if (modal) modal.style.display = 'none';
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
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: folderPath, file_types: fileTypes })
        });
        const data = await response.json();
        const previewDiv = document.getElementById('folder-preview');
        if (data.success) {
            previewDiv.innerHTML = `<p><strong>找到 ${data.files.length} 个文件:</strong></p>
                <ul style="margin:5px 0; padding-left:20px; max-height:150px; overflow-y:auto;">
                ${data.files.slice(0, 20).map(f => `<li>${escapeHtml(f)}</li>`).join('')}
                ${data.files.length > 20 ? `<li>... 还有 ${data.files.length - 20} 个文件</li>` : ''}
                </ul>`;
        } else {
            previewDiv.innerHTML = `<p class="error">预览失败: ${escapeHtml(data.error)}</p>`;
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
    if (!confirm(`开始从文件夹学习？\n路径: ${folderPath}\n模式: ${learnMode}`)) return;
    closeFolderLearn();
    addMessageHTML('user', `<p>📁 开始从文件夹学习: ${escapeHtml(folderPath)}</p>`);
    try {
        const response = await fetch(`${API_BASE}/api/folder/learn`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: folderPath, file_types: fileTypes, mode: learnMode })
        });
        const data = await response.json();
        if (data.success) {
            addMessageHTML('assistant', `
                <p>✅ 学习完成!</p>
                <p>处理文件: ${data.processed} 个</p>
                <p>提取知识点: ${data.knowledge || 0} 条</p>
                ${data.summary ? `<p><strong>摘要:</strong><br>${escapeHtml(data.summary)}</p>` : ''}
            `);
        } else {
            addMessageHTML('assistant', `<p>❌ 学习失败: ${escapeHtml(data.error)}</p>`);
        }
    } catch (error) {
        addMessageHTML('assistant', `<p>❌ 学习失败: ${error.message}</p>`);
    }
}

// ==================== 辅助函数 ====================
function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>]/g, function(m) {
        if (m === '&') return '&amp;';
        if (m === '<') return '&lt;';
        if (m === '>') return '&gt;';
        return m;
    });
}

// ==================== 文件浏览器（全局） ====================
let selectedFiles = [];

function openFileBrowser() {
    const modal = document.getElementById('file-browser-modal');
    if (modal) modal.style.display = 'block';
    
    // 默认浏览项目根目录
    const pathInput = document.getElementById('browser-path');
    if (pathInput && !pathInput.value) {
        pathInput.value = '.';
        browsePath();
    }
}

function closeFileBrowser() {
    const modal = document.getElementById('file-browser-modal');
    if (modal) modal.style.display = 'none';
}

function setBrowserPath(path) {
    const pathInput = document.getElementById('browser-path');
    if (pathInput) {
        pathInput.value = path;
        browsePath();
    }
}

async function browsePath() {
    const pathInput = document.getElementById('browser-path');
    const fileList = document.getElementById('file-list');
    
    if (!pathInput || !fileList) return;
    
    const path = pathInput.value;
    if (!path) {
        fileList.innerHTML = '<p style="color: red;">请输入路径</p>';
        return;
    }
    
    fileList.innerHTML = '<p style="color: #666;">加载中...</p>';
    
    try {
        const response = await fetch(`${API_BASE}/api/folder/browse`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path })
        });
        
        const data = await response.json();
        
        if (data.success) {
            renderFileList(data.items, path);
        } else {
            fileList.innerHTML = `<p style="color: red;">❌ ${escapeHtml(data.error)}</p>`;
        }
    } catch (error) {
        fileList.innerHTML = `<p style="color: red;">❌ 请求失败: ${error.message}</p>`;
    }
}

function renderFileList(items, currentPath) {
    const fileList = document.getElementById('file-list');
    if (!fileList) return;
    
    if (!items || items.length === 0) {
        fileList.innerHTML = '<p style="color: #666;">文件夹为空</p>';
        return;
    }
    
    let html = '<table style="width: 100%; border-collapse: collapse;">';
    html += '<tr style="background: #e0e0e0;"><th style="padding: 8px; text-align: left;">类型</th><th style="padding: 8px; text-align: left;">名称</th><th style="padding: 8px; text-align: right;">大小</th><th style="padding: 8px;">操作</th></tr>';
    
    items.forEach((item, index) => {
        const icon = item.is_dir ? '📁' : '📄';
        const size = item.is_dir ? '-' : formatFileSize(item.size);
        const bgColor = item.is_dir ? '#fff9e6' : '#ffffff';
        
        // 使用data属性存储路径，避免转义问题
        const pathAttr = `data-path="${item.path.replace(/"/g, '&quot;')}"`;
        
        html += `<tr style="background: ${bgColor}; border-bottom: 1px solid #eee;">`;
        html += `<td style="padding: 8px;">${icon}</td>`;
        html += `<td style="padding: 8px;">${escapeHtml(item.name)}</td>`;
        html += `<td style="padding: 8px; text-align: right; color: #666;">${size}</td>`;
        html += `<td style="padding: 8px;">`;
        
        if (item.is_dir) {
            html += `<button onclick="enterDirectory(this.getAttribute('data-path'))" ${pathAttr} class="btn btn-secondary" style="font-size: 12px; padding: 4px 8px;">进入</button> `;
        } else {
            html += `<button onclick="toggleSelectFile(this.getAttribute('data-path'), this)" ${pathAttr} class="btn btn-secondary" style="font-size: 12px; padding: 4px 8px;">选择</button> `;
            html += `<button onclick="previewFile(this.getAttribute('data-path'))" ${pathAttr} class="btn btn-secondary" style="font-size: 12px; padding: 4px 8px;">预览</button>`;
        }
        
        html += `</td></tr>`;
    });
    
    html += '</table>';
    fileList.innerHTML = html;
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB';
}

function enterDirectory(path) {
    const pathInput = document.getElementById('browser-path');
    if (pathInput) {
        pathInput.value = path;
        browsePath();
    }
}

function goToParent() {
    const pathInput = document.getElementById('browser-path');
    if (!pathInput) return;
    
    const currentPath = pathInput.value;
    const parts = currentPath.replace(/\\/g, '/').split('/');
    parts.pop();
    const parentPath = parts.join('/') || '/';
    
    pathInput.value = parentPath;
    browsePath();
}

function toggleSelectFile(filePath, button) {
    const index = selectedFiles.indexOf(filePath);
    
    if (index === -1) {
        selectedFiles.push(filePath);
        button.textContent = '取消';
        button.style.background = '#4caf50';
        button.style.color = 'white';
    } else {
        selectedFiles.splice(index, 1);
        button.textContent = '选择';
        button.style.background = '';
        button.style.color = '';
    }
    
    updateSelectedFilesDisplay();
}

function updateSelectedFilesDisplay() {
    const container = document.getElementById('selected-files');
    const list = document.getElementById('selected-files-list');
    
    if (!container || !list) return;
    
    if (selectedFiles.length === 0) {
        container.style.display = 'none';
        return;
    }
    
    container.style.display = 'block';
    list.innerHTML = selectedFiles.map(f => `<div style="margin: 5px 0;">📄 ${escapeHtml(f)}</div>`).join('');
}

function clearSelectedFiles() {
    selectedFiles = [];
    updateSelectedFilesDisplay();
    
    // 重置所有选择按钮
    const buttons = document.querySelectorAll('button[onclick^="toggleSelectFile"]');
    buttons.forEach(btn => {
        btn.textContent = '选择';
        btn.style.background = '';
        btn.style.color = '';
    });
}

async function previewFile(filePath) {
    try {
        const response = await fetch(`${API_BASE}/api/file/preview`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: filePath })
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert(`文件内容预览:\n\n${data.content.substring(0, 500)}${data.content.length > 500 ? '...' : ''}`);
        } else {
            alert(`预览失败: ${data.error}`);
        }
    } catch (error) {
        alert(`预览失败: ${error.message}`);
    }
}

async function analyzeSelectedFiles() {
    if (selectedFiles.length === 0) {
        alert('请先选择文件');
        return;
    }
    
    closeFileBrowser();
    addMessage('user', `分析以下文件:\n${selectedFiles.map(f => `• ${f}`).join('\n')}`);
    
    try {
        const response = await fetch(`${API_BASE}/api/files/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ files: selectedFiles })
        });
        
        const data = await response.json();
        
        if (data.success) {
            addMessage('assistant', `✅ 分析完成:\n\n${data.summary}`);
        } else {
            addMessage('assistant', `❌ 分析失败: ${data.error}`);
        }
    } catch (error) {
        addMessage('assistant', `❌ 分析失败: ${error.message}`);
    }
    
    selectedFiles = [];
}

// ==================== 初始化（DOMContentLoaded） ====================
document.addEventListener('DOMContentLoaded', () => {
    // 绑定添加模型表单提交事件
    const addForm = document.getElementById('add-model-form');
    if (addForm) {
        addForm.addEventListener('submit', addModelSubmit);
    }
    // 其他按钮的事件已在HTML中通过onclick绑定，无需额外绑定
    // 加载初始数据
    checkHealth();
    loadStats();
    loadModels();
    // 定时刷新
    setInterval(checkHealth, 30000);
    setInterval(loadStats, 60000);
});
