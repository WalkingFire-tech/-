// ==================== 版本信息 ====================
// Version: 3.1.2
// Last Update: 2026-06-19
// ==================== 全局配置 ====================
const API_BASE = 'http://localhost:8000';
const APP_VERSION = '3.1.2';

// ==================== 全局变量 ====================
let selectedModel = 'auto';

// ==================== 工具函数 ====================
function renderMarkdown(text) {
    if (!text) return text;
    text = text.replace(/</g, '&lt;').replace(/>/g, '&gt;');
    text = text.replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre style="overflow-x: auto; white-space: pre-wrap; word-wrap: break-word;"><code>$2</code></pre>');
    text = text.replace(/`([^`]+)`/g, '<code style="overflow-x: auto;">$1</code>');
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
    
    // 显示加载状态
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message system';
    loadingDiv.innerHTML = `
        <div class="message-content">
            <div style="background: #e3f2fd; padding: 10px; border-radius: 8px;">
                <div style="font-weight: bold; margin-bottom: 8px;">🧠 思考过程</div>
                <div id="thinking-steps" style="font-size: 13px; line-height: 1.6;">
                    <div id="step-1">⏳ 分析问题中...</div>
                </div>
            </div>
        </div>
    `;
    document.getElementById('messages').appendChild(loadingDiv);
    
    const thinkingSteps = document.getElementById('thinking-steps');
    let stepCount = 1;
    
    function addStep(message) {
        stepCount++;
        const step = document.createElement('div');
        step.id = `step-${stepCount}`;
        step.innerHTML = `⏳ ${message}`;
        thinkingSteps.appendChild(step);
        return step;
    }
    
    function updateStep(stepId, message) {
        const step = document.getElementById(stepId);
        if (step) step.innerHTML = `✅ ${message}`;
    }
    
    const startTime = Date.now();
    
    // 模拟思考步骤（让用户看到进度）
    setTimeout(() => updateStep('step-1', '问题分析完成'), 300);
    const step2 = addStep('检索知识库...');
    setTimeout(() => updateStep('step-2', '知识检索完成'), 800);
    const step3 = addStep('准备调用模型...');

    try {
        const requestBody = { message };
        if (selectedModel !== 'auto') requestBody.model = selectedModel;

        // 添加30秒超时
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 30000);
        
        const response = await fetch(`${API_BASE}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody),
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        // 更新模型调用步骤
        const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
        updateStep('step-3', `模型响应完成 (${elapsed}秒)`);
        
        // 添加总耗时
        const finalStep = addStep(`✨ 总耗时: ${elapsed}秒`);
        
        // 3秒后折叠思考过程
        setTimeout(() => {
            loadingDiv.innerHTML = `
                <div class="message-content">
                    <details style="background: #f5f5f5; padding: 8px; border-radius: 5px;">
                        <summary style="cursor: pointer; font-weight: bold;">💭 思考过程 (${elapsed}秒)</summary>
                        <div style="font-size: 13px; margin-top: 8px; line-height: 1.6;">${thinkingSteps.innerHTML}</div>
                    </details>
                </div>
            `;
        }, 3000);
        
        const data = await response.json();

        if (data.error) {
            addMessage('system', `❌ 错误: ${data.error}`);
        } else {
            // 显示思考过程（真实过程，非编造）
            if (data.thinking_process) {
                const thinkingDiv = document.createElement('div');
                thinkingDiv.className = 'thinking-info';
                const tp = data.thinking_process;
                thinkingDiv.innerHTML = `
                    <details style="margin: 5px 0;">
                        <summary style="cursor: pointer; color: #666;">
                            <span class="thinking-label">💭 思考过程</span>
                            <span style="margin-left: 10px; font-size: 12px;">${tp.deep_intent} (置信度${Math.round(tp.intent_confidence * 100)}%)</span>
                        </summary>
                        <div style="margin: 10px 0; padding: 10px; background: #f5f5f5; border-radius: 5px; font-size: 13px;">
                            <p><strong>场景角色:</strong> ${tp.scene_role} (${Math.round(tp.role_confidence * 100)}%)</p>
                            <p><strong>理解意图:</strong> ${tp.deep_intent}</p>
                            ${tp.evidence && tp.evidence.length > 0 ? `<p><strong>判断依据:</strong> ${tp.evidence.join(', ')}</p>` : ''}
                            <p><strong>响应策略:</strong> ${tp.response_strategy}</p>
                            ${tp.learning_triggered ? '<p style="color: #4caf50;">📚 从您的输入中学习</p>' : ''}
                        </div>
                    </details>
                `;
                document.getElementById('messages').appendChild(thinkingDiv);
            } else if (data.intent) {
                // 降级显示（无详细思考过程时）
                const thinkingDiv = document.createElement('div');
                thinkingDiv.className = 'thinking-info';
                
                // 构建详细的思考过程
                let thinkingHtml = `<span class="thinking-label">💭 思考过程</span>`;
                
                // 显示意图
                thinkingHtml += `<span class="thinking-detail">识别意图: <strong>${data.intent}</strong></span>`;
                
                // 显示RPV循环（如果有）
                if (data.plan) {
                    const tasks = data.plan.tasks || [];
                    thinkingHtml += `<span class="thinking-detail">执行计划: <strong>${tasks.length}个任务</strong></span>`;
                    
                    // 显示任务列表
                    if (tasks.length > 0) {
                        const taskList = tasks.slice(0, 3).map(t => t.type || t.description || '未知').join(' → ');
                        thinkingHtml += `<span class="thinking-detail" style="font-size: 12px; color: #888;">${taskList}</span>`;
                    }
                }
                
                // 显示置信度
                if (data.confidence) {
                    const confPercent = Math.round(data.confidence * 100);
                    thinkingHtml += `<span class="thinking-detail">置信度: <strong>${confPercent}%</strong></span>`;
                }
                
                // 显示执行结果（如果有）
                if (data.execution_results && data.execution_results.length > 0) {
                    const successCount = data.execution_results.filter(r => r.status === 'success').length;
                    thinkingHtml += `<span class="thinking-detail">执行结果: <strong>${successCount}/${data.execution_results.length}成功</strong></span>`;
                }
                
                // 显示耗时
                if (data.elapsed) {
                    thinkingHtml += `<span class="thinking-detail">耗时: <strong>${data.elapsed.toFixed(1)}秒</strong></span>`;
                }
                
                thinkingDiv.innerHTML = thinkingHtml;
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

        loadingDiv.remove();
        
        if (error.name === 'AbortError') {
            addMessage('system', '⏱️ 请求超时（30秒），请简化问题或稍后重试');
        } else {
            addMessage('system', `❌ 请求失败: ${error.message}`);
        }
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
async function checkHealth(retryCount = 0, maxRetry = 5) {
    const indicator = document.getElementById('status-indicator');
    const statusText = document.getElementById('status-text');
    
    try {
        const response = await fetch(`${API_BASE}/api/health`, {
            signal: AbortSignal.timeout(5000)
        });
        const data = await response.json();
        if (indicator) indicator.classList.add('connected');
        if (statusText) statusText.textContent = `已连接 (v${data.version})`;
        return true;
    } catch (error) {
        if (retryCount < maxRetry) {
            if (statusText) statusText.textContent = `连接中... (${retryCount + 1}/${maxRetry})`;
            await new Promise(resolve => setTimeout(resolve, 2000));
            return checkHealth(retryCount + 1, maxRetry);
        }
        if (indicator) indicator.classList.remove('connected');
        if (statusText) statusText.textContent = '连接失败（点击重试）';
        console.error('健康检查失败:', error);
        return false;
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
        
        loadKnowledgeHealth();
    } catch (error) {
        console.error('加载统计失败:', error);
    }
}

async function loadKnowledgeHealth() {
    try {
        const response = await fetch(`${API_BASE}/api/knowledge/health`);
        const data = await response.json();
        
        if (data.success && data.summary) {
            document.querySelector('.score-value').textContent = Math.round(data.summary.score);
            document.getElementById('knowledge-total').textContent = data.summary.total_knowledge || 0;
            document.getElementById('knowledge-skills').textContent = data.summary.skills || 0;
            document.getElementById('knowledge-rules').textContent = data.summary.rules || 0;
            
            if (data.report && data.report.score) {
                const score = data.report.score;
                document.getElementById('bar-coverage').style.width = `${score.coverage}%`;
                document.getElementById('bar-quality').style.width = `${score.quality}%`;
                document.getElementById('bar-memory').style.width = `${score.memory}%`;
                document.getElementById('bar-skills').style.width = `${score.skills}%`;
            }
        }
    } catch (error) {
        console.error('加载知识健康度失败:', error);
    }
}

function openBaguaKnowledge() {
    window.open(`${API_BASE}/bagua-knowledge`, '_blank');
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

async function refreshModels(event) {
    // 获取按钮元素
    const refreshBtn = event ? event.target : document.getElementById('refresh-models-btn');
    if (!refreshBtn) {
        console.error('找不到刷新按钮');
        return;
    }
    
    const originalText = refreshBtn.textContent;
    refreshBtn.textContent = '⏳ 刷新中...';
    refreshBtn.disabled = true;
    
    try {
        console.log('开始刷新模型...');
        const response = await fetch(`${API_BASE}/api/models/reload`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('刷新响应:', data);
        
        if (data.success) {
            // 重新加载模型列表
            await loadModels();
            
            refreshBtn.textContent = '✓ 已刷新';
            setTimeout(() => {
                refreshBtn.textContent = originalText;
                refreshBtn.disabled = false;
            }, 1500);
            
            // 更新统计
            const statModels = document.getElementById('stat-models');
            if (statModels) statModels.textContent = data.total;
            
            // 检查Ollama状态
            const ollamaStatus = data.ollama_status || 'unknown';
            
            // 显示新增模型
            if (data.added && data.added.length > 0) {
                console.log(`✅ 新增模型: ${data.added.join(', ')}`);
                alert(`✅ 检测到 ${data.added.length} 个新模型:\n${data.added.join('\n')}`);
            } else if (ollamaStatus === 'offline') {
                console.log('⚠️ Ollama服务未启动');
                alert(`⚠️ ${data.message}\n\n提示: 运行 'ollama serve' 启动服务`);
            } else if (ollamaStatus === 'error') {
                console.log('⚠️ Ollama服务异常');
                alert(`⚠️ ${data.message}`);
            } else {
                console.log('✅ 模型列表已刷新');
            }
        } else {
            refreshBtn.textContent = '✗ 失败';
            setTimeout(() => {
                refreshBtn.textContent = originalText;
                refreshBtn.disabled = false;
            }, 2000);
            console.error('刷新模型失败:', data.error);
            alert(`❌ 刷新失败: ${data.error || '未知错误'}`);
        }
    } catch (error) {
        refreshBtn.textContent = '✗ 错误';
        setTimeout(() => {
            refreshBtn.textContent = originalText;
            refreshBtn.disabled = false;
        }, 2000);
        console.error('刷新模型失败:', error);
        alert(`❌ 请求失败: ${error.message}\n\n请检查后端服务是否运行`);
    }
}

let autoRefreshInterval = null;

function startAutoRefresh(intervalSeconds = 30) {
    if (autoRefreshInterval) clearInterval(autoRefreshInterval);
    autoRefreshInterval = setInterval(async () => {
        try {
            const response = await fetch(`${API_BASE}/api/models/reload`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await response.json();
            if (data.success && data.added && data.added.length > 0) {
                await loadModels();
                const statModels = document.getElementById('stat-models');
                if (statModels) statModels.textContent = data.total;
                console.log(`🔄 自动检测到新模型: ${data.added.join(', ')}`);
            }
        } catch (error) {
            console.error('自动刷新模型失败:', error);
        }
    }, intervalSeconds * 1000);
}

function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
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
    
    // 只显示文件名，不显示完整内容
    const fileList = selectedFiles.map(f => {
        const parts = f.replace(/\\/g, '/').split('/');
        return `• ${parts[parts.length - 1]}`;
    }).join('\n');
    
    addMessage('user', `分析以下文件:\n${fileList}`);
    
    const sendBtn = document.getElementById('send-btn');
    if (sendBtn) sendBtn.disabled = true;
    
    try {
        // 读取文件内容
        const filesWithContent = [];
        
        for (const filePath of selectedFiles) {
            try {
                const response = await fetch(`${API_BASE}/api/file/preview`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ path: filePath })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    const pathParts = filePath.replace(/\\/g, '/').split('/');
                    const fileName = pathParts[pathParts.length - 1];
                    
                    filesWithContent.push({
                        name: fileName,
                        path: filePath,
                        content: data.content.substring(0, 3000), // 限制每个文件3000字符
                        size: data.size
                    });
                }
            } catch (e) {
                console.error(`读取文件失败 ${filePath}:`, e);
            }
        }
        
        if (filesWithContent.length === 0) {
            addMessage('assistant', '❌ 无法读取任何文件内容');
            return;
        }
        
        // 构建分析提示
        let analysisPrompt = `请分析以下${filesWithContent.length}个文件的内容:\n\n`;
        
        filesWithContent.forEach((file, index) => {
            analysisPrompt += `=== 文件 ${index + 1}: ${file.name} ===\n`;
            analysisPrompt += `大小: ${(file.size / 1024).toFixed(1)} KB\n\n`;
            analysisPrompt += `${file.content}\n\n`;
            analysisPrompt += `---\n\n`;
        });
        
        analysisPrompt += `\n请总结这些文件的主要内容、结构和关键信息。`;
        
        // 发送给AI分析（不保存到对话历史）
        const response = await fetch(`${API_BASE}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                message: analysisPrompt,
                skip_history: true  // 标记不保存到历史
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            addMessage('assistant', `❌ 分析失败: ${data.error}`);
        } else {
            const responseHtml = formatResponseEnhanced(data.response);
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message assistant';
            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';
            contentDiv.innerHTML = responseHtml;
            messageDiv.appendChild(contentDiv);
            document.getElementById('messages').appendChild(messageDiv);
            addCopyButtons(contentDiv);
            document.getElementById('messages').scrollTop = document.getElementById('messages').scrollHeight;
        }
        
    } catch (error) {
        addMessage('assistant', `❌ 分析失败: ${error.message}`);
    } finally {
        if (sendBtn) sendBtn.disabled = false;
    }
    
    selectedFiles = [];
}

async function learnFromFiles() {
    if (selectedFiles.length === 0) {
        alert('请先选择文件');
        return;
    }
    
    if (!confirm(`确定要从这 ${selectedFiles.length} 个文件中学习并保存知识点吗？\n\n知识点将保存到知识库，以后可以通过对话查询使用。`)) {
        return;
    }
    
    closeFileBrowser();
    
    const fileList = selectedFiles.map(f => {
        const parts = f.replace(/\\/g, '/').split('/');
        return `• ${parts[parts.length - 1]}`;
    }).join('\n');
    
    addMessage('user', `从以下文件学习:\n${fileList}`);
    
    const sendBtn = document.getElementById('send-btn');
    if (sendBtn) sendBtn.disabled = true;
    
    try {
        const response = await fetch(`${API_BASE}/api/files/learn`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ files: selectedFiles })
        });
        
        const data = await response.json();
        
        if (data.success) {
            addMessage('assistant', data.summary);
        } else {
            addMessage('assistant', `❌ 学习失败: ${data.error}`);
        }
    } catch (error) {
        addMessage('assistant', `❌ 学习失败: ${error.message}`);
    } finally {
        if (sendBtn) sendBtn.disabled = false;
    }
    
    selectedFiles = [];
}

// ==================== 外部模型配置 ====================
function showExternalModelConfig() {
    const modal = document.getElementById('external-model-modal');
    if (modal) modal.style.display = 'block';
    
    // 加载当前配置
    loadExternalModelConfig();
}

function closeExternalModelConfig() {
    const modal = document.getElementById('external-model-modal');
    if (modal) modal.style.display = 'none';
}

async function loadExternalModelConfig() {
    try {
        const response = await fetch(`${API_BASE}/api/config/external`);
        const data = await response.json();
        
        if (data.success) {
            const openaiKey = document.getElementById('openai-key');
            const deepseekKey = document.getElementById('deepseek-key');
            
            if (openaiKey && data.openai_key) {
                openaiKey.value = data.openai_key.substring(0, 10) + '...';
            }
            if (deepseekKey && data.deepseek_key) {
                deepseekKey.value = data.deepseek_key.substring(0, 10) + '...';
            }
        }
    } catch (error) {
        console.error('加载配置失败:', error);
    }
}

async function saveExternalModelConfig() {
    const openaiKey = document.getElementById('openai-key').value.trim();
    const deepseekKey = document.getElementById('deepseek-key').value.trim();
    const statusDiv = document.getElementById('external-model-status');
    
    if (!openaiKey && !deepseekKey) {
        if (statusDiv) statusDiv.innerHTML = '<p style="color: red;">请至少输入一个API Key</p>';
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/config/external`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                openai_api_key: openaiKey,
                deepseek_api_key: deepseekKey
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            if (statusDiv) statusDiv.innerHTML = '<p style="color: green;">✅ 配置已保存，请重启服务生效</p>';
            setTimeout(() => {
                closeExternalModelConfig();
                loadModels();
            }, 2000);
        } else {
            if (statusDiv) statusDiv.innerHTML = `<p style="color: red;">❌ 保存失败: ${data.error}</p>`;
        }
    } catch (error) {
        if (statusDiv) statusDiv.innerHTML = `<p style="color: red;">❌ 请求失败: ${error.message}</p>`;
    }
}

async function testExternalModel() {
    const statusDiv = document.getElementById('external-model-status');
    if (statusDiv) statusDiv.innerHTML = '<p style="color: blue;">⏳ 测试连接中...</p>';
    
    try {
        const response = await fetch(`${API_BASE}/api/models/test`);
        const data = await response.json();
        
        if (data.success) {
            const results = data.results || {};
            let html = '<p style="color: green;">✅ 测试结果:</p><ul>';
            
            for (const [model, result] of Object.entries(results)) {
                const status = result.success ? '✅' : '❌';
                html += `<li>${status} ${model}: ${result.message || 'OK'}</li>`;
            }
            
            html += '</ul>';
            if (statusDiv) statusDiv.innerHTML = html;
        } else {
            if (statusDiv) statusDiv.innerHTML = `<p style="color: red;">❌ 测试失败: ${data.error}</p>`;
        }
    } catch (error) {
        if (statusDiv) statusDiv.innerHTML = `<p style="color: red;">❌ 测试失败: ${error.message}</p>`;
    }
}

// ==================== 初始化（DOMContentLoaded） ====================
document.addEventListener('DOMContentLoaded', async () => {
    // 绑定添加模型表单提交事件
    const addForm = document.getElementById('add-model-form');
    if (addForm) {
        addForm.addEventListener('submit', addModelSubmit);
    }
    
    // 状态文本点击重试
    const statusText = document.getElementById('status-text');
    if (statusText) {
        statusText.style.cursor = 'pointer';
        statusText.title = '点击重试连接';
        statusText.addEventListener('click', async () => {
            if (statusText.textContent.includes('失败')) {
                statusText.textContent = '重新连接中...';
                const success = await checkHealth();
                if (success) {
                    loadStats();
                    loadModels();
                }
            }
        });
    }
    
    // 其他按钮的事件已在HTML中通过onclick绑定，无需额外绑定
    // 加载初始数据（带重试）
    const healthSuccess = await checkHealth();
    if (healthSuccess) {
        loadStats();
        loadModels();
    }
    // 定时刷新
    setInterval(checkHealth, 30000);
    setInterval(loadStats, 60000);
    // 自动检测新模型（每30秒）
    startAutoRefresh(30);
});
