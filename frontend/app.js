// ==================== 版本信息 ====================
// Version: 3.6.0
// Last Update: 2026-07-04
// ==================== 全局配置 ====================
const API_BASE = 'http://localhost:8000';
const APP_VERSION = '3.6.0';

// ==================== 全局变量 ====================
let selectedModel = 'auto';
let conversationHistory = [];
let currentSessionId = '';

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

    if (role === 'assistant') {
        const copyBtn = document.createElement('button');
        copyBtn.className = 'copy-response-btn';
        copyBtn.title = '复制回复';
        copyBtn.innerHTML = '&#128203;';
        copyBtn.onclick = async () => {
            const text = contentDiv.innerText || contentDiv.textContent || '';
            try {
                await navigator.clipboard.writeText(text);
                copyBtn.innerHTML = '&#10003;';
                copyBtn.title = '已复制';
                setTimeout(() => { copyBtn.innerHTML = '&#128203;'; copyBtn.title = '复制回复'; }, 1500);
            } catch {
                const ta = document.createElement('textarea');
                ta.value = text;
                document.body.appendChild(ta);
                ta.select();
                document.execCommand('copy');
                document.body.removeChild(ta);
                copyBtn.innerHTML = '&#10003;';
                setTimeout(() => { copyBtn.innerHTML = '&#128203;'; copyBtn.title = '复制回复'; }, 1500);
            }
        };
        messageDiv.appendChild(copyBtn);
    }

    messageDiv.appendChild(contentDiv);
    messagesDiv.appendChild(messageDiv);
    addCopyButtons(contentDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// ==================== 本地降级回复（前端兜底） ====================
function _generateLocalFallback(query) {
    return `关于「${query}」，我正在思考中，但响应时间较长。请稍等片刻再试，或尝试换个方式描述你的问题。`;
}

// ==================== 发送消息（全局函数 - 流式SSE） ====================
async function sendMessage() {
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const message = userInput.value.trim();
    if (!message) return;

    addMessage('user', message);
    userInput.value = '';
    sendBtn.disabled = true;
    
    const startTime = Date.now();
    
    // 创建思考过程容器
    const thinkingDiv = document.createElement('div');
    thinkingDiv.className = 'message system';
    thinkingDiv.innerHTML = `
        <div class="message-content">
            <div style="background: #e3f2fd; padding: 10px; border-radius: 8px;">
                <div style="font-weight: bold; margin-bottom: 8px;">🧠 思考过程 <span id="thinking-timer" style="color: #666; font-size: 12px;">0.0秒</span></div>
                <div id="thinking-steps" style="font-size: 13px; line-height: 1.8;"></div>
            </div>
        </div>
    `;
    document.getElementById('messages').appendChild(thinkingDiv);
    
    const stepsContainer = document.getElementById('thinking-steps');
    let currentStepEl = null;
    
    // 计时器
    const timerInterval = setInterval(() => {
        const timerEl = document.getElementById('thinking-timer');
        if (timerEl) timerEl.textContent = ((Date.now() - startTime) / 1000).toFixed(1) + '秒';
    }, 100);

    try {
        conversationHistory.push({ role: 'user', content: message });
        const requestBody = { message, history: conversationHistory.slice(-10) };
        if (selectedModel !== 'auto') requestBody.model = selectedModel;
        if (currentSessionId) requestBody.session_id = currentSessionId;

        const controller = new AbortController();
        const streamTimeout = setTimeout(() => {
            controller.abort();
        }, 180000);

        const response = await fetch(`${API_BASE}/api/chat/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody),
            signal: controller.signal
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let finalResult = null;
        let lastDataTime = Date.now();
        const dataTimeoutMs = 60000;

        while (true) {
            const readPromise = reader.read();
            const readTimeoutPromise = new Promise((_, reject) => {
                setTimeout(() => reject(new Error('读取超时')), 60000);
            });

            let readResult;
            try {
                readResult = await Promise.race([readPromise, readTimeoutPromise]);
            } catch (readErr) {
                console.warn('流读取异常:', readErr.message);
                break;
            }

            const { done, value } = readResult;
            if (done) break;

            lastDataTime = Date.now();
            clearTimeout(streamTimeout);
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';
            
            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                const jsonStr = line.slice(6).trim();
                if (!jsonStr) continue;
                
                try {
                    const event = JSON.parse(jsonStr);
                    
                    if (event.type === 'step') {
                        const phase = event.phase;
                        const status = event.status;
                        const detail = event.detail || '';
                        
                        if (status === 'running') {
                            if (currentStepEl) {
                                const icon = currentStepEl.querySelector('.step-icon');
                                if (icon) icon.textContent = '✅';
                            }
                            currentStepEl = document.createElement('div');
                            currentStepEl.style.marginTop = '4px';
                            currentStepEl.innerHTML = `<span class="step-icon">⏳</span> <strong>${phase}</strong> - ${detail}`;
                            stepsContainer.appendChild(currentStepEl);
                        } else if (status === 'timeout') {
                            if (currentStepEl) {
                                currentStepEl.innerHTML = `<span class="step-icon">⏱️</span> <strong>${phase}</strong> - ${detail}`;
                                currentStepEl.style.opacity = '0.7';
                            }
                            currentStepEl = null;
                        } else if (status === 'done') {
                            if (currentStepEl) {
                                const icon = currentStepEl.querySelector('.step-icon');
                                if (icon) icon.textContent = '✅';
                                currentStepEl.innerHTML = `<span class="step-icon">✅</span> <strong>${phase}</strong> - ${detail}`;
                            }
                            currentStepEl = null;
                        }
                    } else if (event.type === 'result') {
                        finalResult = event;
                        if (event.session_id && !currentSessionId) {
                            currentSessionId = event.session_id;
                        }
                    }
                } catch (e) {
                    // JSON解析失败，忽略
                }
            }
        }
        
        clearInterval(timerInterval);
        clearTimeout(streamTimeout);
        const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
        
        // 折叠思考过程
        setTimeout(() => {
            let metaHtml = '';
            if (finalResult) {
                if (finalResult.path_contributions && Object.keys(finalResult.path_contributions).length > 0) {
                    const bars = Object.entries(finalResult.path_contributions).map(([k, v]) => {
                        const color = k.includes('Ollama') || k.includes('本地') ? '#4CAF50' : 
                                      k.includes('DeepSeek') || k.includes('OpenAI') ? '#2196F3' : 
                                      k.includes('经验') ? '#FF9800' : '#9C27B0';
                        return `<span style="display:inline-block;margin-right:8px;font-size:12px;"><span style="display:inline-block;width:8px;height:8px;background:${color};border-radius:50%;margin-right:3px;"></span>${k} ${v}%</span>`;
                    }).join('');
                    metaHtml += `<div style="margin-top:6px;font-size:12px;color:#555;">📊 路径贡献: ${bars}</div>`;
                }
                if (finalResult.token_usage && Object.keys(finalResult.token_usage).length > 0) {
                    const tokens = Object.entries(finalResult.token_usage).map(([k, v]) => 
                        `<span style="font-size:12px;margin-right:8px;">💰 ${k}: ${v.total_tokens||0} tokens (输入${v.prompt_tokens||0}+输出${v.completion_tokens||0})</span>`
                    ).join('');
                    metaHtml += `<div style="margin-top:4px;font-size:12px;color:#555;">${tokens}</div>`;
                }
            }
            thinkingDiv.innerHTML = `
                <div class="message-content">
                    <details style="background: #f5f5f5; padding: 8px; border-radius: 5px;">
                        <summary style="cursor: pointer; font-weight: bold;">💭 思考过程 (${elapsed}秒)</summary>
                        <div style="font-size: 13px; margin-top: 8px; line-height: 1.8;">${stepsContainer.innerHTML}${metaHtml}</div>
                    </details>
                </div>
            `;
        }, 2000);

        // 显示最终回复
        if (finalResult && finalResult.response) {
            conversationHistory.push({ role: 'assistant', content: finalResult.response });
            if (finalResult.session_id && !currentSessionId) {
                currentSessionId = finalResult.session_id;
            }
            refreshChatHistory();
            const responseHtml = formatResponseEnhanced(finalResult.response);
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
            const copyBtn = document.createElement('button');
            copyBtn.className = 'copy-response-btn';
            copyBtn.title = '复制回复';
            copyBtn.innerHTML = '&#128203;';
            copyBtn.onclick = async () => {
                const text = contentDiv.innerText || contentDiv.textContent || '';
                try {
                    await navigator.clipboard.writeText(text);
                    copyBtn.innerHTML = '&#10003;';
                    copyBtn.title = '已复制';
                    setTimeout(() => { copyBtn.innerHTML = '&#128203;'; copyBtn.title = '复制回复'; }, 1500);
                } catch {
                    const ta = document.createElement('textarea');
                    ta.value = text;
                    document.body.appendChild(ta);
                    ta.select();
                    document.execCommand('copy');
                    document.body.removeChild(ta);
                    copyBtn.innerHTML = '&#10003;';
                    setTimeout(() => { copyBtn.innerHTML = '&#128203;'; copyBtn.title = '复制回复'; }, 1500);
                }
            };
            messageDiv.appendChild(copyBtn);
            messageDiv.appendChild(contentDiv);
            messageDiv.appendChild(feedbackDiv);
            document.getElementById('messages').appendChild(messageDiv);
            addCopyButtons(contentDiv);
        } else {
            // 流结束但无result事件——用规则推理直接生成回复
            const fallbackDiv = document.createElement('div');
            fallbackDiv.className = 'message assistant';
            const fallbackContent = document.createElement('div');
            fallbackContent.className = 'message-content';
            fallbackContent.innerHTML = formatResponseEnhanced(_generateLocalFallback(message));
            const fallbackCopyBtn = document.createElement('button');
            fallbackCopyBtn.className = 'copy-response-btn';
            fallbackCopyBtn.title = '复制回复';
            fallbackCopyBtn.innerHTML = '&#128203;';
            fallbackCopyBtn.onclick = async () => {
                const text = fallbackContent.innerText || fallbackContent.textContent || '';
                try { await navigator.clipboard.writeText(text); fallbackCopyBtn.innerHTML = '&#10003;'; setTimeout(() => { fallbackCopyBtn.innerHTML = '&#128203;'; }, 1500); } catch { const ta = document.createElement('textarea'); ta.value = text; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); document.body.removeChild(ta); fallbackCopyBtn.innerHTML = '&#10003;'; setTimeout(() => { fallbackCopyBtn.innerHTML = '&#128203;'; }, 1500); }
            };
            fallbackDiv.appendChild(fallbackCopyBtn);
            fallbackDiv.appendChild(fallbackContent);
            document.getElementById('messages').appendChild(fallbackDiv);
        }
        
        document.getElementById('messages').scrollTop = document.getElementById('messages').scrollHeight;

    } catch (error) {
        clearInterval(timerInterval);
        thinkingDiv.remove();
        
        if (error.name === 'AbortError') {
            // 超时也要给出回复，不能让用户白等
            const timeoutDiv = document.createElement('div');
            timeoutDiv.className = 'message assistant';
            const timeoutContent = document.createElement('div');
            timeoutContent.className = 'message-content';
            timeoutContent.innerHTML = formatResponseEnhanced(_generateLocalFallback(message));
            timeoutDiv.appendChild(timeoutContent);
            document.getElementById('messages').appendChild(timeoutDiv);
        } else {
            // 其他错误也尽量给出回复
            const errDiv = document.createElement('div');
            errDiv.className = 'message assistant';
            const errContent = document.createElement('div');
            errContent.className = 'message-content';
            errContent.innerHTML = formatResponseEnhanced(_generateLocalFallback(message));
            errDiv.appendChild(errContent);
            document.getElementById('messages').appendChild(errDiv);
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
        conversationHistory = [];
        currentSessionId = '';
        addMessage('system', '👋 消息已清空，继续对话吧！');
    }
}

async function refreshChatHistory() {
    try {
        const resp = await fetch(`${API_BASE}/api/chat-history/sessions?limit=15`);
        const data = await resp.json();
        const list = document.getElementById('chat-history-list');
        if (!data.sessions || data.sessions.length === 0) {
            list.innerHTML = '<p style="color:#999;font-size:11px;">暂无历史记录</p>';
            return;
        }
        list.innerHTML = data.sessions.map(s => {
            const time = s.updated_at ? s.updated_at.slice(0, 16).replace('T', ' ') : '';
            const active = s.id === currentSessionId ? 'font-weight:bold;background:#e3f2fd;' : '';
            return `<div style="padding:4px 6px;margin:2px 0;border-radius:4px;cursor:pointer;${active}" onclick="loadChatSession('${s.id}')" title="${s.title||''}">` +
                `<div style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${s.title||'对话'}</div>` +
                `<div style="font-size:10px;color:#888;">${time} · ${s.message_count||0}条</div></div>`;
        }).join('');
    } catch (e) {
        console.warn('对话历史加载失败:', e);
    }
}

async function loadChatSession(sessionId) {
    try {
        const resp = await fetch(`${API_BASE}/api/chat-history/sessions/${sessionId}?limit=200`);
        const data = await resp.json();
        if (!data.messages || data.messages.length === 0) return;
        const messagesDiv = document.getElementById('messages');
        messagesDiv.innerHTML = '';
        conversationHistory = [];
        currentSessionId = sessionId;
        for (const msg of data.messages) {
            if (msg.role === 'user') {
                conversationHistory.push({ role: 'user', content: msg.content });
                addMessage('user', msg.content);
            } else if (msg.role === 'assistant') {
                conversationHistory.push({ role: 'assistant', content: msg.content });
                const div = document.createElement('div');
                div.className = 'message assistant';
                const content = document.createElement('div');
                content.className = 'message-content';
                content.innerHTML = formatResponseEnhanced(msg.content);
                div.appendChild(content);
                messagesDiv.appendChild(div);
            }
        }
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
        refreshChatHistory();
    } catch (e) {
        console.warn('加载会话失败:', e);
    }
}

async function searchChatHistory() {
    const q = document.getElementById('chat-history-search').value.trim();
    if (!q) { refreshChatHistory(); return; }
    try {
        const resp = await fetch(`${API_BASE}/api/chat-history/search?q=${encodeURIComponent(q)}&limit=15`);
        const data = await resp.json();
        const list = document.getElementById('chat-history-list');
        if (!data.results || data.results.length === 0) {
            list.innerHTML = '<p style="color:#999;font-size:11px;">无搜索结果</p>';
            return;
        }
        list.innerHTML = data.results.map(r => {
            const time = r.timestamp ? r.timestamp.slice(0, 16).replace('T', ' ') : '';
            const preview = (r.content || '').slice(0, 40);
            return `<div style="padding:4px 6px;margin:2px 0;border-radius:4px;cursor:pointer;background:#fff8e1;" onclick="loadChatSession('${r.session_id}')" title="${r.title||''}">` +
                `<div style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${preview}...</div>` +
                `<div style="font-size:10px;color:#888;">${time} · ${r.title||''}</div></div>`;
        }).join('');
    } catch (e) {
        console.warn('搜索失败:', e);
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
        loadRecentLearning();
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
                const vc = document.getElementById('val-coverage');
                const vq = document.getElementById('val-quality');
                const vm = document.getElementById('val-memory');
                const vs = document.getElementById('val-skills');
                if (vc) vc.textContent = Math.round(score.coverage) + '%';
                if (vq) vq.textContent = Math.round(score.quality) + '%';
                if (vm) vm.textContent = Math.round(score.memory) + '%';
                if (vs) vs.textContent = Math.round(score.skills) + '%';
            }
        }
    } catch (error) {
        console.error('加载知识健康度失败:', error);
    }
}

function openKnowledgeGraph() {
    const modal = document.getElementById('knowledge-graph-modal');
    if (modal) modal.style.display = 'block';
    loadKnowledgeGraphData();
}

function closeKnowledgeGraph() {
    const modal = document.getElementById('knowledge-graph-modal');
    if (modal) modal.style.display = 'none';
}

async function loadKnowledgeGraphData() {
    const container = document.getElementById('knowledge-graph-content');
    if (!container) return;
    container.innerHTML = '<p style="color:#666;">加载中...</p>';
    try {
        const [statsRes, truthsRes, skillsRes] = await Promise.all([
            fetch(`${API_BASE}/api/stats`).then(r => r.json()),
            fetch(`${API_BASE}/api/truths`).then(r => r.json()),
            fetch(`${API_BASE}/api/skills`).then(r => r.json())
        ]);
        let html = '<div style="font-size:13px;line-height:1.8;">';
        html += '<h4>📊 系统概览</h4>';
        html += `<p>经验: ${statsRes.experiences || 0} | 活跃规则: ${statsRes.active_rules || 0} | 待激活: ${statsRes.pending_rules || 0}</p>`;
        if (truthsRes.top_truths && truthsRes.top_truths.length > 0) {
            html += '<h4>💡 核心真谛</h4>';
            truthsRes.top_truths.forEach((t, i) => {
                html += `<p>${i+1}. ${t.name} (证据${t.evidence}次)</p>`;
            });
        }
        if (skillsRes.top_skills && skillsRes.top_skills.length > 0) {
            html += '<h4>⚡ 涌现技能</h4>';
            skillsRes.top_skills.forEach((s, i) => {
                html += `<p>${i+1}. ${s.name} (成功率${(s.rate*100).toFixed(0)}%)</p>`;
            });
        }
        if (truthsRes.entropy) {
            html += '<h4>🧠 认知熵值</h4>';
            const e = truthsRes.entropy;
            const color = e.status === 'healthy' ? '#4caf50' : e.status === 'warning' ? '#ff9800' : '#f44336';
            html += `<p style="color:${color};">熵值: ${e.entropy_score.toFixed(3)} (${e.status}) | 矛盾率: ${(e.contradiction_rate*100).toFixed(1)}%</p>`;
        }
        html += '</div>';
        container.innerHTML = html;
    } catch (error) {
        container.innerHTML = `<p style="color:red;">加载失败: ${error.message}</p>`;
    }
}

async function loadRecentLearning() {
    const container = document.getElementById('recent-learning');
    if (!container) return;
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);
        const response = await fetch(`${API_BASE}/api/recent_learning`, { signal: controller.signal });
        clearTimeout(timeoutId);
        const data = await response.json();
        if (data.items && data.items.length > 0) {
            container.innerHTML = data.items.map(item => 
                `<div style="padding:4px 0;border-bottom:1px solid #eee;font-size:12px;">
                    <span style="color:#666;">${item.time}</span> ${escapeHtml(item.content)}
                </div>`
            ).join('');
        } else {
            container.innerHTML = '<p style="color:#666;font-size:12px;">暂无学习记录，开始对话后将自动记录</p>';
        }
    } catch (error) {
        container.innerHTML = '<p style="color:#666;font-size:12px;">暂无学习记录，开始对话后将自动记录</p>';
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
            
            if (openaiKey && data.openai_api_key) {
                openaiKey.value = data.openai_api_key.substring(0, 10) + '...';
            }
            if (deepseekKey && data.deepseek_api_key) {
                deepseekKey.value = data.deepseek_api_key.substring(0, 10) + '...';
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
    
    const payload = {};
    if (openaiKey && !openaiKey.endsWith('...')) {
        payload.openai_api_key = openaiKey;
    }
    if (deepseekKey && !deepseekKey.endsWith('...')) {
        payload.deepseek_api_key = deepseekKey;
    }
    
    if (!payload.openai_api_key && !payload.deepseek_api_key) {
        if (statusDiv) statusDiv.innerHTML = '<p style="color: #888;">配置未变更</p>';
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/config/external`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
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
        const response = await fetch(`${API_BASE}/api/models/test`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        
        if (data.success || data.results) {
            const results = data.results || {};
            let html = '<p style="color: green;">✅ 测试结果:</p><ul>';
            
            for (const [model, result] of Object.entries(results)) {
                const status = result.success ? '✅' : '❌';
                html += `<li>${status} ${model}: ${result.message || 'OK'}</li>`;
            }
            
            html += '</ul>';
            if (statusDiv) statusDiv.innerHTML = html;
        } else {
            if (statusDiv) statusDiv.innerHTML = `<p style="color: red;">❌ 测试失败: ${data.error || data.message || '未知错误'}</p>`;
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
        refreshChatHistory();
    }
    // 定时刷新
    setInterval(checkHealth, 30000);
    setInterval(loadStats, 60000);
    setInterval(refreshProbabilityCloud, 30000);
    setInterval(refreshResourceStatus, 30000);
    setInterval(refreshHardwareStatus, 10000);
    // 自动检测新模型（每30秒）
    startAutoRefresh(30);
    refreshProbabilityCloud();
    refreshResourceStatus();
    refreshHardwareStatus();
});

async function refreshProbabilityCloud() {
    try {
        const resp = await fetch('/api/weights');
        const data = await resp.json();
        if (data.error) return;

        const container = document.getElementById('weight-bars');
        if (!container) return;

        const weights = data.weights?.paths || {};
        const colors = ['#4fc3f7','#81c784','#fff176','#ff8a65','#ce93d8','#4dd0e1','#aed581','#f48fb1','#90a4ae'];

        let html = '';
        let i = 0;
        for (const [name, info] of Object.entries(weights)) {
            const pct = (info.weight * 100).toFixed(1);
            const sr = (info.success_rate * 100).toFixed(0);
            const color = colors[i % colors.length];
            html += `<div class="weight-bar-item">
                <span class="weight-bar-label" title="${name}">${name}</span>
                <div class="weight-bar-track">
                    <div class="weight-bar-fill" style="width:${pct}%;background:${color}"></div>
                </div>
                <span class="weight-bar-value">${pct}%</span>
            </div>`;
            i++;
        }
        container.innerHTML = html || '<p style="color:#999;font-size:12px">暂无数据</p>';

        const entropyEl = document.getElementById('entropy-indicator');
        if (entropyEl && data.confidence_distribution) {
            const topSource = Object.entries(data.confidence_distribution).sort((a,b) => b[1]-a[1])[0];
            entropyEl.textContent = `最可靠: ${topSource ? topSource[0] : '--'} | 路径数: ${Object.keys(weights).length}`;
        }

        // 概率分布展示
        const probDistContainer = document.getElementById('prob-dist-bars');
        if (probDistContainer && data.confidence_distribution) {
            const dist = data.confidence_distribution;
            const sorted = Object.entries(dist).sort((a,b) => b[1]-a[1]);
            let distHtml = '';
            let j = 0;
            for (const [name, prob] of sorted) {
                const pct = (prob * 100).toFixed(1);
                const color = colors[j % colors.length];
                distHtml += `<div class="weight-bar-item">
                    <span class="weight-bar-label" title="${name}">${name}</span>
                    <div class="weight-bar-track">
                        <div class="weight-bar-fill" style="width:${pct}%;background:${color}"></div>
                    </div>
                    <span class="weight-bar-value">${pct}%</span>
                </div>`;
                j++;
            }
            probDistContainer.innerHTML = distHtml || '<p style="color:#999;font-size:12px">暂无概率分布</p>';
        }

        // 检索信息展示
        const retrievalInfo = document.getElementById('retrieval-info');
        if (retrievalInfo) {
            const mode = data.prob_mode || '--';
            const queryEntropy = data.query_entropy != null ? data.query_entropy.toFixed(3) : '--';
            const alpha = data.alpha != null ? data.alpha.toFixed(3) : '--';
            retrievalInfo.textContent = `检索模式: ${mode} | 查询熵: ${queryEntropy} | α(稀疏权重): ${alpha}`;
        }
    } catch (e) {
        // silently fail
    }
}

async function refreshResourceStatus() {
    try {
        const resp = await fetch('/api/resource-status');
        const data = await resp.json();
        if (data.error) return;

        const snap = data.health?.snapshot || {};
        const hw = data.health?.hardware || {};
        const mode = snap.mode || 'normal';
        const mem = snap.memory_usage || 0;
        const threads = snap.thread_count || 0;
        const paths = data.parallel_paths || 9;
        const retrieval = data.retrieval_strategy || 'hybrid';
        const gpuMem = snap.gpu_memory || 0;
        const gpuVramUsed = snap.gpu_vram_used_gb || 0;
        const gpuVramTotal = snap.gpu_vram_total_gb || 0;

        const modeEl = document.getElementById('rs-mode');
        if (modeEl) {
            const modeLabels = {normal: '正常', conservative: '保守', emergency: '紧急'};
            const modeColors = {normal: '#4CAF50', conservative: '#FF9800', emergency: '#F44336'};
            modeEl.textContent = modeLabels[mode] || mode;
            modeEl.style.color = modeColors[mode] || '#666';
        }

        const memEl = document.getElementById('rs-memory');
        if (memEl) memEl.textContent = (mem * 100).toFixed(1) + '%';

        const memBar = document.getElementById('rs-memory-bar');
        if (memBar) {
            memBar.style.width = (mem * 100) + '%';
            if (mem > 0.88) memBar.style.background = '#F44336';
            else if (mem > 0.75) memBar.style.background = '#FF9800';
            else memBar.style.background = '#4CAF50';
        }

        const gpuSection = document.getElementById('rs-gpu-section');
        if (gpuSection && gpuVramTotal > 0) {
            gpuSection.style.display = 'block';
            const gpuEl = document.getElementById('rs-gpu');
            if (gpuEl) gpuEl.textContent = gpuVramUsed.toFixed(1) + '/' + gpuVramTotal.toFixed(1) + 'GB';
            const gpuBar = document.getElementById('rs-gpu-bar');
            if (gpuBar) {
                gpuBar.style.width = (gpuMem * 100) + '%';
                if (gpuMem > 0.88) gpuBar.style.background = '#F44336';
                else if (gpuMem > 0.75) gpuBar.style.background = '#FF9800';
                else gpuBar.style.background = '#2196F3';
            }
        }

        const threadsEl = document.getElementById('rs-threads');
        if (threadsEl) threadsEl.textContent = threads;

        const pathsEl = document.getElementById('rs-paths');
        if (pathsEl) pathsEl.textContent = paths + '/9';

        const retrievalEl = document.getElementById('rs-retrieval');
        if (retrievalEl) {
            const retrievalLabels = {hybrid: '混合', sparse_only: '仅词法'};
            retrievalEl.textContent = retrievalLabels[retrieval] || retrieval;
        }

        const hwEl = document.getElementById('rs-hardware');
        if (hwEl && hw.total_ram_gb) {
            let hwText = 'RAM: ' + hw.total_ram_gb.toFixed(1) + 'GB';
            if (hw.gpu_name) hwText += ' | GPU: ' + hw.gpu_name;
            hwEl.textContent = hwText;
        }
    } catch (e) {
        // silently fail
    }
}

async function refreshHardwareStatus() {
    try {
        const resp = await fetch(`${API_BASE}/api/hardware/status`);
        const data = await resp.json();
        if (data.error) return;

        const gpu = data.gpu || {};
        const cpu = data.cpu || {};
        const mem = data.memory || {};

        if (gpu.available) {
            const gpuTemp = gpu.temperature;
            const gpuTempEl = document.getElementById('hw-gpu-temp');
            if (gpuTempEl) {
                gpuTempEl.textContent = gpuTemp + '°C';
                gpuTempEl.style.color = gpuTemp > 85 ? '#F44336' : gpuTemp > 70 ? '#FF9800' : '#4CAF50';
            }
            const gpuBar = document.getElementById('hw-gpu-bar');
            if (gpuBar) {
                const pct = Math.min(gpuTemp / 100 * 100, 100);
                gpuBar.style.width = pct + '%';
                gpuBar.style.background = gpuTemp > 85 ? '#F44336' : gpuTemp > 70 ? '#FF9800' : '#2196F3';
            }
            const gpuUsageEl = document.getElementById('hw-gpu-usage');
            if (gpuUsageEl) gpuUsageEl.textContent = (gpu.usage != null ? gpu.usage + '%' : '--');
            const gpuClockEl = document.getElementById('hw-gpu-clock');
            if (gpuClockEl) gpuClockEl.textContent = (gpu.engine_clock || '--') + 'MHz';
            const gpuFanEl = document.getElementById('hw-gpu-fan');
            if (gpuFanEl) gpuFanEl.textContent = (gpu.fan_speed != null ? gpu.fan_speed + '%' : '--');
        }

        if (cpu.available) {
            const cpuUsage = cpu.usage;
            const cpuTempEl = document.getElementById('hw-cpu-temp');
            if (cpuTempEl) {
                cpuTempEl.textContent = cpuUsage.toFixed(0) + '%';
                cpuTempEl.style.color = cpuUsage > 90 ? '#F44336' : cpuUsage > 70 ? '#FF9800' : '#4CAF50';
            }
            const cpuBar = document.getElementById('hw-cpu-bar');
            if (cpuBar) {
                cpuBar.style.width = cpuUsage + '%';
                cpuBar.style.background = cpuUsage > 90 ? '#F44336' : cpuUsage > 70 ? '#FF9800' : '#4CAF50';
            }
        }

        const thermal = data.thermal || {};
        if (thermal.available && thermal.zones && thermal.zones.length > 0) {
            const cpuTempEl = document.getElementById('hw-cpu-temp');
            if (cpuTempEl && thermal.zones[0].temp_celsius != null) {
                const t = thermal.zones[0].temp_celsius;
                cpuTempEl.textContent = t + '°C';
                cpuTempEl.style.color = t > 85 ? '#F44336' : t > 70 ? '#FF9800' : '#4CAF50';
                const cpuBar = document.getElementById('hw-cpu-bar');
                if (cpuBar) {
                    cpuBar.style.width = Math.min(t / 100 * 100, 100) + '%';
                    cpuBar.style.background = t > 85 ? '#F44336' : t > 70 ? '#FF9800' : '#4CAF50';
                }
            }
        }
    } catch (e) {
        // silently fail
    }
}

let _currentPanoramaTab = '';

function switchPanoramaTab(tab) {
    _currentPanoramaTab = tab;
    document.querySelectorAll('[id^="pan-tab-"]').forEach(btn => {
        btn.style.background = '#e0e0e0';
        btn.style.color = '#333';
        btn.style.fontWeight = 'normal';
    });
    const activeBtn = document.getElementById('pan-tab-' + tab);
    if (activeBtn) {
        activeBtn.style.background = '#1976D2';
        activeBtn.style.color = 'white';
        activeBtn.style.fontWeight = 'bold';
    }
    refreshSystemPanorama();
}

async function refreshSystemPanorama() {
    const container = document.getElementById('panorama-content');
    if (!container) return;
    if (!_currentPanoramaTab) {
        container.innerHTML = '<p style="color:#999;font-size:11px;">点击标签查看子系统状态</p>';
        return;
    }
    container.innerHTML = '<p style="color:#999;font-size:11px;">加载中...</p>';
    try {
        if (_currentPanoramaTab === 'defense') {
            const [statusResp, anomaliesResp, metricsResp] = await Promise.all([
                fetch('/api/defense/status'),
                fetch('/api/defense/anomalies'),
                fetch('/api/defense/health/metrics')
            ]);
            const data = await statusResp.json();
            const anomaliesData = await anomaliesResp.json();
            const metricsData = await metricsResp.json();
            let html = '';
            if (data.error) {
                html = '<p style="color:#F44336;font-size:11px;">错误: ' + data.error + '</p>';
            } else {
                const running = data.running !== false;
                html += '<div style="margin-bottom:6px;"><b>守护者:</b> <span style="color:' + (running ? '#4CAF50' : '#F44336') + ';">' + (running ? '运行中' : '已停止') + '</span>';
                if (data.patrol_count != null) html += ' | 巡逻: ' + data.patrol_count + '次';
                html += '</div>';
                if (data.last_patrol) {
                    html += '<div style="font-size:10px;color:#888;margin-bottom:6px;">最近巡逻: ' + data.last_patrol.replace('T', ' ').substring(0, 19) + '</div>';
                }
                const hs = data.health_snapshot || {};
                if (hs.error_rate) {
                    const er = hs.error_rate;
                    const pct = (er.current * 100).toFixed(1);
                    const erColor = er.current > 0.1 ? '#F44336' : er.current > 0.05 ? '#FF9800' : '#4CAF50';
                    html += '<div style="margin:4px 0;padding:4px 6px;background:#f5f5f5;border-radius:3px;">';
                    html += '<b>错误率:</b> <span style="color:' + erColor + ';">' + pct + '%</span>';
                    if (er.trend) html += ' | 趋势: ' + (er.trend === 'stable' ? '稳定' : er.trend === 'increasing' ? '上升' : '下降');
                    html += '</div>';
                }
                const cb = data.circuit_breakers || {};
                const im = data.isolated_modules || {};
                const hs2 = data.healing_statuses || {};
                html += '<div style="margin:4px 0;padding:4px 6px;background:#f5f5f5;border-radius:3px;">';
                html += '<b>L2-熔断保护:</b> ' + (Object.keys(cb).length === 0 ? '<span style="color:#4CAF50;">全部正常</span>' : Object.keys(cb).length + '个熔断');
                html += '</div>';
                html += '<div style="margin:4px 0;padding:4px 6px;background:#f5f5f5;border-radius:3px;">';
                html += '<b>L3-故障隔离:</b> ' + (Object.keys(im).length === 0 ? '<span style="color:#4CAF50;">无隔离</span>' : Object.keys(im).length + '个隔离');
                html += '</div>';
                html += '<div style="margin:4px 0;padding:4px 6px;background:#f5f5f5;border-radius:3px;">';
                html += '<b>L4-认知自修复:</b> ' + (Object.keys(hs2).length === 0 ? '<span style="color:#4CAF50;">无修复中</span>' : Object.keys(hs2).length + '个修复中');
                html += '</div>';
                const anomalies = data.recent_anomalies || [];
                html += '<div style="margin:4px 0;padding:4px 6px;background:#f5f5f5;border-radius:3px;">';
                html += '<b>L1-异常检测:</b> ' + (anomalies.length === 0 ? '<span style="color:#4CAF50;">无异常</span>' : anomalies.length + '个异常');
                html += '</div>';
                const es = data.exception_stats || {};
                if (es.total_suppressed > 0) {
                    html += '<div style="font-size:10px;color:#FF9800;margin-top:4px;">已抑制异常: ' + es.total_suppressed + ' | 类型: ' + es.unique_types + '</div>';
                }
                if (anomaliesData && !anomaliesData.error) {
                    const anomList = anomaliesData.anomalies || anomaliesData.recent_anomalies || [];
                    html += '<div style="margin:4px 0;padding:4px 6px;background:#f5f5f5;border-radius:3px;">';
                    html += '<b>异常详情:</b> ' + (anomList.length === 0 ? '<span style="color:#4CAF50;">无异常</span>' : anomList.length + '个');
                    for (const a of anomList.slice(0, 3)) {
                        html += '<div style="font-size:9px;color:#666;margin:1px 0;">• ' + (a.type || a.module || '') + ': ' + (a.description || a.message || '').substring(0, 50) + '</div>';
                    }
                    html += '</div>';
                }
                if (metricsData && !metricsData.error) {
                    const mKeys = Object.keys(metricsData).filter(k => typeof metricsData[k] === 'number');
                    if (mKeys.length > 0) {
                        html += '<div style="margin:4px 0;padding:4px 6px;background:#f5f5f5;border-radius:3px;">';
                        html += '<b>健康指标:</b> ';
                        for (const k of mKeys.slice(0, 5)) {
                            html += '<span style="font-size:9px;margin-right:6px;">' + k + ': ' + (metricsData[k] * 100).toFixed(0) + '%</span>';
                        }
                        html += '</div>';
                    }
                }
                html += '<div style="margin-top:8px;border-top:1px solid #eee;padding-top:6px;"><b>操作:</b></div>';
                html += '<div style="display:flex;gap:4px;flex-wrap:wrap;margin-top:4px;">';
                html += '<button onclick="defenseAction(\'repair\')" style="font-size:10px;padding:2px 6px;background:#4CAF50;color:white;border:none;border-radius:3px;cursor:pointer;">认知修复</button>';
                if (Object.keys(cb).length > 0) {
                    html += '<button onclick="defenseAction(\'circuit_reset\')" style="font-size:10px;padding:2px 6px;background:#FF9800;color:white;border:none;border-radius:3px;cursor:pointer;">重置熔断</button>';
                }
                if (Object.keys(im).length > 0) {
                    html += '<button onclick="defenseAction(\'isolation_release\')" style="font-size:10px;padding:2px 6px;background:#2196F3;color:white;border:none;border-radius:3px;cursor:pointer;">解除隔离</button>';
                }
                html += '</div>';
            }
            container.innerHTML = html || '<p style="color:#999;font-size:11px;">暂无防御数据</p>';
        } else if (_currentPanoramaTab === 'presence') {
            const [presResp, forgetResp, percResp] = await Promise.all([
                fetch('/api/presence/status'),
                fetch('/api/forgetting/evaluate'),
                fetch('/api/perception/snapshot')
            ]);
            const data = await presResp.json();
            const forgetData = await forgetResp.json();
            let percData = {};
            try { percData = await percResp.json(); } catch(e) {}
            let html = '';
            if (data.error) {
                html = '<p style="color:#F44336;font-size:11px;">错误: ' + data.error + '</p>';
            } else {
                const stateColors = {awake: '#4CAF50', drowsy: '#FF9800', asleep: '#9C27B0', sleeping: '#9C27B0', deep_sleep: '#673AB7'};
                const stateLabels = {awake: '清醒', drowsy: '困倦', asleep: '睡眠', sleeping: '睡眠', deep_sleep: '深睡'};
                const st = data.state || 'awake';
                html += '<div style="text-align:center;margin-bottom:8px;">';
                html += '<div style="font-size:20px;font-weight:bold;color:' + (stateColors[st] || '#666') + ';">' + (stateLabels[st] || st) + '</div>';
                html += '</div>';
                const metrics = [
                    ['运行时间', data.uptime_seconds != null ? Math.floor(data.uptime_seconds / 60) + '分' : null],
                    ['总周期', data.total_cycles],
                    ['清醒周期', data.awake_cycles],
                    ['生长周期', data.growing_cycles],
                    ['休息周期', data.resting_cycles],
                    ['待处理信号', data.signals_pending],
                    ['已处理信号', data.signals_processed],
                    ['整合记忆', data.memories_consolidated],
                ];
                for (const [label, val] of metrics) {
                    if (val != null) {
                        html += '<div style="display:flex;justify-content:space-between;font-size:11px;margin:2px 0;">';
                        html += '<span style="color:#666;">' + label + '</span><span>' + val + '</span></div>';
                    }
                }
                const lp = data.last_perception || {};
                if (Object.keys(lp).length > 0) {
                    html += '<div style="margin-top:6px;padding-top:4px;border-top:1px solid #eee;"><b>最近感知:</b></div>';
                    const percLabels = {health: '健康度', confidence: '置信度', energy: '能量'};
                    for (const [k, v] of Object.entries(lp)) {
                        const pct = (v * 100).toFixed(0);
                        const color = v > 0.7 ? '#4CAF50' : v > 0.4 ? '#FF9800' : '#F44336';
                        html += '<div style="margin:2px 0;"><span style="font-size:10px;color:#888;">' + (percLabels[k] || k) + '</span>';
                        html += '<div style="height:4px;background:#e0e0e0;border-radius:2px;"><div style="height:4px;width:' + pct + '%;background:' + color + ';border-radius:2px;"></div></div></div>';
                    }
                }
                if (data.silence_duration != null) {
                    const silMins = Math.floor(data.silence_duration / 60);
                    html += '<div style="margin-top:4px;font-size:10px;color:#aaa;">静默: ' + silMins + '分</div>';
                }
            }
                if (percData && !percData.error && percData.summary) {
                    html += '<div style="margin-top:6px;border-top:1px solid #eee;padding-top:4px;">';
                    html += '<div style="font-size:10px;font-weight:bold;color:#607D8B;margin-bottom:2px;">统一感知</div>';
                    html += '<div style="font-size:10px;color:#666;">' + percData.summary + '</div>';
                    if (percData.knowledge) {
                        const k = percData.knowledge;
                        html += '<div style="font-size:9px;color:#999;margin-top:2px;">经验:' + (k.experience_count||0) + ' 真谛:' + (k.truth_count||0) + ' 图谱:' + (k.graph_nodes||0) + '节点</div>';
                    }
                    html += '</div>';
                }
                html += '<div style="margin-top:6px;border-top:1px solid #eee;padding-top:4px;">';
                html += '<button onclick="evalProactivity()" style="font-size:10px;padding:2px 6px;background:#9C27B0;color:white;border:none;border-radius:3px;cursor:pointer;margin-right:4px;">主动性评估</button>';
                html += '<button onclick="testProactivity()" style="font-size:10px;padding:2px 6px;background:#FF9800;color:white;border:none;border-radius:3px;cursor:pointer;margin-right:4px;">主动性测试</button>';
                html += '<button onclick="closedLoopOrchestrate()" style="font-size:10px;padding:2px 6px;background:#2196F3;color:white;border:none;border-radius:3px;cursor:pointer;margin-right:4px;">闭环编排</button>';
                html += '<button onclick="executeForgetting()" style="font-size:10px;padding:2px 6px;background:#795548;color:white;border:none;border-radius:3px;cursor:pointer;margin-right:4px;">执行遗忘</button>';
                html += '<button onclick="sendPresenceSignal()" style="font-size:10px;padding:2px 6px;background:#009688;color:white;border:none;border-radius:3px;cursor:pointer;margin-right:4px;">发送信号</button>';
                html += '<select id="force-state-select" style="font-size:10px;padding:1px 3px;border-radius:3px;margin-right:2px;"><option value="awake">清醒</option><option value="drowsy">困倦</option><option value="asleep">睡眠</option></select>';
                html += '<button onclick="forcePresenceState()" style="font-size:10px;padding:2px 6px;background:#E91E63;color:white;border:none;border-radius:3px;cursor:pointer;">切换状态</button>';
                html += '<div id="presence-action-result" style="margin-top:4px;font-size:10px;"></div>';
                html += '</div>';
            container.innerHTML = html || '<p style="color:#999;font-size:11px;">暂无存在层数据</p>';
        } else if (_currentPanoramaTab === 'assessment') {
            const [assessResp, historyResp, attrResp, deltaResp, covResp, gapsResp, suggResp] = await Promise.all([
                fetch('/api/self-assessment'),
                fetch('/api/self-assessment/history'),
                fetch('/api/attributions'),
                fetch('/api/delta-stats'),
                fetch('/api/coverage/report'),
                fetch('/api/coverage/gaps'),
                fetch('/api/coverage/suggestions')
            ]);
            const data = await assessResp.json();
            const historyData = await historyResp.json();
            const attrData = await attrResp.json();
            const deltaData = await deltaResp.json();
            const covReport = await covResp.json();
            const covGaps = await gapsResp.json();
            const covSugg = await suggResp.json();
            let html = '';
            if (data.error) {
                html = '<p style="color:#F44336;font-size:11px;">错误: ' + data.error + '</p>';
            } else {
                if (data.overall) {
                    const score = data.overall.score || 0;
                    const level = data.overall.level || '--';
                    const scorePct = (score * 100).toFixed(1);
                    const scoreColor = score >= 0.8 ? '#4CAF50' : score >= 0.6 ? '#FF9800' : '#F44336';
                    const levelLabels = {thriving: '繁荣', healthy: '健康', degraded: '退化', critical: '危急'};
                    html += '<div style="text-align:center;margin-bottom:8px;">';
                    html += '<div style="font-size:28px;font-weight:bold;color:' + scoreColor + ';">' + scorePct + '</div>';
                    html += '<div style="font-size:11px;color:#888;">' + (levelLabels[level] || level) + '</div>';
                    html += '</div>';
                    const dimScores = data.overall.dimension_scores || {};
                    const dimLabels = {loop_integrity: '闭环完整性', knowledge_vitality: '知识活力', learning_efficiency: '学习效率', behavior_deviation: '行为偏差', adaptation_speed: '适应速度', frontend_coverage: '前端覆盖率'};
                    const dimColors = {loop_integrity: '#2196F3', knowledge_vitality: '#4CAF50', learning_efficiency: '#FF9800', behavior_deviation: '#9C27B0', adaptation_speed: '#E91E63', frontend_coverage: '#00BCD4'};
                    if (Object.keys(dimScores).length > 0) {
                        html += '<div><b>六维评估:</b></div>';
                        for (const [key, val] of Object.entries(dimScores)) {
                            const pct = Math.min(100, Math.max(0, val * 100)).toFixed(0);
                            const label = dimLabels[key] || key;
                            const color = dimColors[key] || '#2196F3';
                            html += '<div style="margin:4px 0;">';
                            html += '<div style="display:flex;justify-content:space-between;font-size:11px;"><span>' + label + '</span><span>' + pct + '%</span></div>';
                            html += '<div style="height:6px;background:#e0e0e0;border-radius:3px;"><div style="height:6px;width:' + pct + '%;background:' + color + ';border-radius:3px;"></div></div>';
                            html += '</div>';
                        }
                    }
                    const fc = data.frontend_coverage || {};
                    if (fc.metrics && fc.metrics.coverage_rate != null) {
                        html += '<div style="margin-top:6px;padding-top:4px;border-top:1px solid #eee;">';
                        html += '<div style="font-size:10px;color:#00BCD4;">前端覆盖率: ' + (fc.metrics.coverage_rate * 100).toFixed(1) + '% (' + fc.metrics.covered_endpoints + '/' + fc.metrics.total_endpoints + ')</div>';
                        if (fc.metrics.high_priority_gaps_count > 0) {
                            html += '<div style="font-size:9px;color:#F44336;">高优先级缺口: ' + fc.metrics.high_priority_gaps_count + '个</div>';
                        }
                        html += '</div>';
                    }
                }
                const recs = data.recommendations || [];
                if (recs.length > 0) {
                    html += '<div style="margin-top:6px;"><b>建议:</b></div>';
                    for (const r of recs.slice(0, 3)) {
                        const priColor = r.priority === 'high' ? '#F44336' : r.priority === 'medium' ? '#FF9800' : '#4CAF50';
                        html += '<div style="font-size:10px;margin:2px 0;padding:2px 4px;border-left:3px solid ' + priColor + ';">' + (r.area || '') + ': ' + (r.action || '') + '</div>';
                    }
                }
                if (historyData && historyData.trends) {
                    html += '<div style="margin-top:6px;padding-top:4px;border-top:1px solid #eee;font-size:10px;color:#888;">';
                    html += '<b>趋势:</b> ';
                    for (const [dim, trend] of Object.entries(historyData.trends)) {
                        const tLabel = {overall: '总体', loop_integrity: '闭环', knowledge_vitality: '知识', learning_efficiency: '学习', frontend_coverage: '覆盖'}[dim] || dim;
                        const tIcon = trend === 'improving' ? '↑' : trend === 'declining' ? '↓' : '→';
                        html += tLabel + tIcon + ' ';
                    }
                    html += '</div>';
                }
                if (data.timestamp) {
                    html += '<div style="margin-top:4px;font-size:10px;color:#aaa;">评估时间: ' + data.timestamp.replace('T', ' ').substring(0, 19) + '</div>';
                }
                if (covGaps && covGaps.uncovered_endpoints && covGaps.uncovered_endpoints.length > 0) {
                    html += '<div style="margin-top:6px;border-top:1px solid #eee;padding-top:4px;"><b>未覆盖端点:</b></div>';
                    for (const ep of covGaps.uncovered_endpoints.slice(0, 6)) {
                        html += '<div style="font-size:10px;color:#F44336;margin:1px 0;">' + ep + '</div>';
                    }
                    html += '<button onclick="autoGenerateCoverage()" style="font-size:10px;padding:2px 6px;background:#009688;color:white;border:none;border-radius:3px;cursor:pointer;margin-top:4px;">自动生成覆盖</button>';
                }
                if (covSugg && covSugg.suggestions && covSugg.suggestions.length > 0) {
                    html += '<div style="margin-top:4px;border-top:1px solid #eee;padding-top:4px;"><b>覆盖建议:</b></div>';
                    for (const s of covSugg.suggestions.slice(0, 3)) {
                        html += '<div style="font-size:10px;color:#666;margin:1px 0;">' + (s.endpoint || s) + '</div>';
                    }
                }
            }
            container.innerHTML = html || '<p style="color:#999;font-size:11px;">暂无评估数据</p>';
        } else if (_currentPanoramaTab === 'genes') {
            const resp = await fetch('/api/genes');
            const data = await resp.json();
            let html = '';
            if (data.error) {
                html = '<p style="color:#F44336;font-size:11px;">错误: ' + data.error + '</p>';
            } else {
                const genes = data.genes || {};
                const personality = data.personality || '未定型';
                html += '<div style="margin-bottom:8px;"><b>性格类型:</b> <span style="color:#1976D2;">' + personality + '</span></div>';
                if (Object.keys(genes).length > 0) {
                    html += '<div><b>基因参数:</b></div>';
                    const geneColors = ['#2196F3', '#4CAF50', '#FF9800', '#9C27B0', '#E91E63', '#00BCD4', '#FF5722', '#607D8B'];
                    let gi = 0;
                    for (const [name, value] of Object.entries(genes)) {
                        const val = typeof value === 'number' ? value : parseFloat(value) || 0;
                        const pct = Math.min(100, Math.max(0, val * 100));
                        const color = geneColors[gi % geneColors.length];
                        html += '<div style="margin:3px 0;">';
                        html += '<div style="display:flex;justify-content:space-between;font-size:11px;"><span>' + name + '</span><span>' + (val * 100).toFixed(1) + '%</span></div>';
                        html += '<div style="height:5px;background:#e0e0e0;border-radius:3px;"><div style="height:5px;width:' + pct + '%;background:' + color + ';border-radius:3px;"></div></div>';
                        html += '</div>';
                        gi++;
                    }
                }
                if (data.radar && Object.keys(data.radar).length > 0) {
                    html += '<div style="margin-top:8px;"><b>雷达维度:</b></div>';
                    for (const [k, v] of Object.entries(data.radar)) {
                        html += '<span style="display:inline-block;font-size:10px;background:#e3f2fd;padding:1px 4px;border-radius:2px;margin:1px;">' + k + ': ' + (typeof v === 'number' ? v.toFixed(2) : v) + '</span>';
                    }
                }
                if (data.mutation_history && data.mutation_history.length > 0) {
                    html += '<div style="margin-top:8px;"><b>最近突变:</b></div>';
                    for (const m of data.mutation_history.slice(0, 5)) {
                        const delta = m.delta != null ? (m.delta > 0 ? '+' : '') + m.delta.toFixed(2) : '';
                        html += '<div style="font-size:10px;color:#666;margin:1px 0;">' + (m.key || '?') + ': ' + (m.old != null ? m.old.toFixed(2) : '') + ' → ' + (m.new != null ? m.new.toFixed(2) : '') + ' <span style="color:' + (m.delta > 0 ? '#4CAF50' : '#F44336') + ';">' + delta + '</span> <span style="color:#aaa;">(' + (m.trigger || '') + ')</span></div>';
                    }
                }
            }
            container.innerHTML = html || '<p style="color:#999;font-size:11px;">暂无基因数据</p>';
        } else if (_currentPanoramaTab === 'cognitive') {
            const [entropyResp, truthsResp, probResp, reflResp, eventsResp] = await Promise.all([
                fetch('/api/truths/entropy'),
                fetch('/api/truths'),
                fetch('/api/probability-field'),
                fetch('/api/reflection/stats'),
                fetch('/api/events/stats')
            ]);
            const entropy = await entropyResp.json();
            const truths = await truthsResp.json();
            const prob = await probResp.json();
            let html = '';
            html += '<div style="text-align:center;margin-bottom:8px;">';
            const eScore = entropy.entropy_score || 0;
            const eColor = eScore < 0.3 ? '#4CAF50' : eScore < 0.6 ? '#FF9800' : '#F44336';
            const eStatus = entropy.status || 'unknown';
            const statusLabels = {healthy: '健康', warning: '警告', critical: '危急', unknown: '未知'};
            html += '<div style="font-size:24px;font-weight:bold;color:' + eColor + ';">' + (eScore * 100).toFixed(1) + '</div>';
            html += '<div style="font-size:11px;color:#888;">认知熵 | ' + (statusLabels[eStatus] || eStatus) + '</div>';
            html += '</div>';
            html += '<div style="margin:4px 0;padding:4px 6px;background:#f5f5f5;border-radius:3px;">';
            html += '<b>真谛沉淀:</b> ' + (truths.total_truths || 0) + '条';
            if (truths.by_level) {
                const levels = Object.entries(truths.by_level);
                html += ' | ' + levels.map(([l, c]) => l + ':' + c).join(' ');
            }
            html += '</div>';
            html += '<div style="margin:4px 0;padding:4px 6px;background:#f5f5f5;border-radius:3px;">';
            html += '<b>重组候选:</b> ' + (truths.reorganization_candidates || 0) + '个';
            html += '</div>';
            html += '<div style="margin-top:6px;border-top:1px solid #eee;padding-top:4px;">';
                html += '<button onclick="truthsReorg(\'propose\')" style="font-size:10px;padding:2px 6px;background:#2196F3;color:white;border:none;border-radius:3px;cursor:pointer;margin-right:4px;">提议重组</button>';
                html += '<button onclick="truthsReorg(\'approve\')" style="font-size:10px;padding:2px 6px;background:#4CAF50;color:white;border:none;border-radius:3px;cursor:pointer;margin-right:4px;">批准重组</button>';
                html += '<button onclick="truthsReorg(\'execute\')" style="font-size:10px;padding:2px 6px;background:#FF9800;color:white;border:none;border-radius:3px;cursor:pointer;margin-right:4px;">执行重组</button>';
                html += '<button onclick="runReorganization()" style="font-size:10px;padding:2px 6px;background:#9C27B0;color:white;border:none;border-radius:3px;cursor:pointer;">自动重组</button>';
            html += '<div id="reorg-result" style="margin-top:4px;font-size:10px;"></div>';
            html += '</div>';
            const entMetrics = [
                ['矛盾率', entropy.contradiction_rate, '%'],
                ['真谛冲突率', entropy.truth_conflict_rate, '%'],
                ['基因安全违规', entropy.gene_safety_violations, ''],
            ];
            for (const [label, val, unit] of entMetrics) {
                if (val != null) {
                    const display = unit === '%' ? (val * 100).toFixed(1) + unit : val;
                    const color = unit === '%' ? (val > 0.5 ? '#F44336' : val > 0.2 ? '#FF9800' : '#4CAF50') : (val > 100 ? '#F44336' : val > 10 ? '#FF9800' : '#4CAF50');
                    html += '<div style="display:flex;justify-content:space-between;font-size:11px;margin:2px 0;">';
                    html += '<span style="color:#666;">' + label + '</span><span style="color:' + color + ';">' + display + '</span></div>';
                }
            }
            if (prob.distribution) {
                html += '<div style="margin-top:6px;padding-top:4px;border-top:1px solid #eee;"><b>概率场:</b></div>';
                const dist = prob.distribution;
                if (dist.entropy != null) {
                    html += '<div style="font-size:11px;color:#666;">分布熵: ' + dist.entropy.toFixed(3) + ' | 置信: ' + (dist.confidence_level || '--') + '</div>';
                }
                if (dist.top) {
                    html += '<div style="font-size:11px;">最可靠: <span style="color:#1976D2;">' + (dist.top.source || '--') + '</span> (' + ((dist.top.probability || 0) * 100).toFixed(1) + '%)</div>';
                }
                if (dist.candidates) {
                    for (const [id, cand] of Object.entries(dist.candidates)) {
                        const pct = ((cand.probability || 0) * 100).toFixed(1);
                        html += '<div style="margin:2px 0;">';
                        html += '<div style="display:flex;justify-content:space-between;font-size:10px;"><span>' + (cand.source || id) + '</span><span>' + pct + '%</span></div>';
                        html += '<div style="height:4px;background:#e0e0e0;border-radius:2px;"><div style="height:4px;width:' + pct + '%;background:#2196F3;border-radius:2px;"></div></div>';
                        html += '</div>';
                    }
                }
            }
            if (prob.gap_stats && prob.gap_stats.total_gaps > 0) {
                html += '<div style="margin-top:6px;"><b>知识缺口:</b> ' + prob.gap_stats.total_gaps + '个';
                if (prob.gap_stats.top_gap) html += ' | 最大: ' + prob.gap_stats.top_gap;
                html += '</div>';
            }
            try {
                const reflData = await reflResp.json();
                if (reflData && !reflData.error) {
                    html += '<div style="margin-top:6px;padding-top:4px;border-top:1px solid #eee;"><b>反思统计:</b> ' + (reflData.total_reflections || 0) + '次 | 成功率: ' + ((reflData.success_rate || 0) * 100).toFixed(0) + '%</div>';
                }
            } catch(e) {}
            try {
                const evData = await eventsResp.json();
                if (evData && !evData.error) {
                    html += '<div style="margin-top:4px;"><b>事件统计:</b> ' + (evData.total_events || 0) + '个事件</div>';
                }
            } catch(e) {}
            container.innerHTML = html || '<p style="color:#999;font-size:11px;">暂无认知数据</p>';
        } else if (_currentPanoramaTab === 'agents') {
            const resp = await fetch('/api/agent/status');
            const data = await resp.json();
            let html = '';
            if (data.error) {
                html = '<p style="color:#F44336;font-size:11px;">错误: ' + data.error + '</p>';
            } else {
                const coord = data.coordinator || {};
                html += '<div style="margin-bottom:6px;"><b>协调器:</b> 迭代 ' + (coord.iteration_count || 0) + '/' + (coord.max_iterations || 3) + ' | 质量阈值: ' + (coord.quality_threshold || 50) + '</div>';
                const roleLabels = {planner: '规划者', executor: '执行者', reflector: '反思者'};
                const roleColors = {planner: '#2196F3', executor: '#4CAF50', reflector: '#FF9800'};
                const roleIcons = {planner: '🧭', executor: '⚡', reflector: '🔍'};
                const agentKeys = ['planner', 'executor', 'reflector'];
                for (const key of agentKeys) {
                    const agent = data[key];
                    if (agent) {
                        const stateColors = {idle: '#999', working: '#4CAF50', waiting: '#FF9800', error: '#F44336'};
                        const stateLabels = {idle: '空闲', working: '工作中', waiting: '等待', error: '错误'};
                        const st = agent.state || 'idle';
                        const label = roleLabels[agent.role || key] || key;
                        const color = roleColors[agent.role || key] || '#666';
                        const icon = roleIcons[agent.role || key] || '🤖';
                        html += '<div style="margin:4px 0;padding:6px;background:#f5f5f5;border-radius:4px;border-left:3px solid ' + color + ';">';
                        html += '<div style="display:flex;justify-content:space-between;align-items:center;">';
                        html += '<span><b>' + icon + ' ' + label + '</b></span>';
                        html += '<span style="font-size:10px;padding:1px 4px;border-radius:2px;background:' + (stateColors[st] || '#999') + ';color:white;">' + (stateLabels[st] || st) + '</span>';
                        html += '</div>';
                        html += '<div style="font-size:10px;color:#888;margin-top:2px;">';
                        html += '发送: ' + (agent.messages_sent || 0) + ' | 接收: ' + (agent.messages_received || 0);
                        if (agent.errors > 0) html += ' | <span style="color:#F44336;">错误: ' + agent.errors + '</span>';
                        html += '</div>';
                        html += '</div>';
                    }
                }
                html += '<div style="margin-top:8px;border-top:1px solid #eee;padding-top:6px;">';
                html += '<input id="agent-query-input" type="text" placeholder="输入问题触发协作..." style="width:100%;font-size:11px;padding:3px 6px;border:1px solid #ddd;border-radius:3px;box-sizing:border-box;">';
                html += '<button onclick="triggerAgentCollab()" style="font-size:10px;padding:2px 8px;margin-top:4px;background:#2196F3;color:white;border:none;border-radius:3px;cursor:pointer;">触发协作</button>';
                html += '<div id="agent-collab-result" style="margin-top:4px;max-height:120px;overflow-y:auto;font-size:10px;"></div>';
                html += '</div>';
                const lastResult = data.last_collaboration;
                if (lastResult) {
                    html += '<div style="margin-top:6px;border-top:1px solid #eee;padding-top:4px;"><b>最近协作:</b></div>';
                    html += '<div style="font-size:10px;color:#666;">质量: ' + ((lastResult.quality || 0) * 100).toFixed(0) + '% | 迭代: ' + (lastResult.iterations || 0) + '次</div>';
                    if (lastResult.improvement) html += '<div style="font-size:10px;color:#4CAF50;">提升: +' + ((lastResult.improvement || 0) * 100).toFixed(0) + '%</div>';
                }
            }
            container.innerHTML = html || '<p style="color:#999;font-size:11px;">暂无协作数据</p>';
        } else if (_currentPanoramaTab === 'facts') {
            const resp = await fetch('/api/facts/stats');
            const data = await resp.json();
            let html = '<div style="text-align:center;margin-bottom:8px;">';
            html += '<div style="font-size:24px;font-weight:bold;color:#2196F3;">' + (data.total || 0) + '</div>';
            html += '<div style="font-size:11px;color:#888;">事实锚点</div></div>';
            html += '<div style="display:flex;gap:6px;justify-content:center;margin-bottom:8px;">';
            html += '<div style="padding:4px 8px;background:#E8F5E9;border-radius:3px;font-size:11px;">✓ ' + (data.positive || 0) + ' 正向</div>';
            html += '<div style="padding:4px 8px;background:#FFF3E0;border-radius:3px;font-size:11px;">✗ ' + (data.negations || 0) + ' 否定</div>';
            html += '<div style="padding:4px 8px;background:#E3F2FD;border-radius:3px;font-size:11px;">↻ ' + (data.corrections || 0) + ' 纠正</div>';
            html += '</div>';
            html += '<div style="margin-top:6px;border-top:1px solid #eee;padding-top:6px;">';
            html += '<input id="fact-search-input" type="text" placeholder="搜索事实..." style="width:100%;font-size:11px;padding:3px 6px;border:1px solid #ddd;border-radius:3px;box-sizing:border-box;">';
            html += '<button onclick="searchFacts()" style="font-size:10px;padding:2px 8px;margin-top:4px;background:#2196F3;color:white;border:none;border-radius:3px;cursor:pointer;">搜索</button>';
            html += '<div id="fact-search-results" style="margin-top:4px;max-height:120px;overflow-y:auto;"></div>';
            html += '</div>';
            html += '<div style="margin-top:6px;border-top:1px solid #eee;padding-top:6px;">';
            html += '<input id="fact-add-input" type="text" placeholder="添加新事实..." style="width:100%;font-size:11px;padding:3px 6px;border:1px solid #ddd;border-radius:3px;box-sizing:border-box;">';
            html += '<button onclick="addFact()" style="font-size:10px;padding:2px 8px;margin-top:4px;background:#4CAF50;color:white;border:none;border-radius:3px;cursor:pointer;">添加</button>';
            html += '</div>';
            container.innerHTML = html;
        } else if (_currentPanoramaTab === 'memory') {
            const resp = await fetch('/api/memory/stats');
            const data = await resp.json();
            let html = '<div style="text-align:center;margin-bottom:8px;">';
            html += '<div style="font-size:24px;font-weight:bold;color:#9C27B0;">' + (data.total_memories || 0) + '</div>';
            html += '<div style="font-size:11px;color:#888;">立体记忆</div></div>';
            const byType = data.by_type || {};
            const typeLabels = {conversation: '对话', knowledge: '知识', experience: '经验', emotion: '情感', relationship: '关系', skill: '技能'};
            const typeColors = {conversation: '#2196F3', knowledge: '#4CAF50', experience: '#FF9800', emotion: '#E91E63', relationship: '#9C27B0', skill: '#00BCD4'};
            for (const [k, v] of Object.entries(byType)) {
                if (v > 0) {
                    const pct = ((v / (data.total_memories || 1)) * 100).toFixed(0);
                    html += '<div style="margin:3px 0;">';
                    html += '<div style="display:flex;justify-content:space-between;font-size:11px;"><span>' + (typeLabels[k] || k) + '</span><span>' + v + ' (' + pct + '%)</span></div>';
                    html += '<div style="height:5px;background:#e0e0e0;border-radius:3px;"><div style="height:5px;width:' + pct + '%;background:' + (typeColors[k] || '#666') + ';border-radius:3px;"></div></div>';
                    html += '</div>';
                }
            }
            html += '<div style="margin-top:6px;font-size:10px;color:#888;">平均重要度: ' + ((data.avg_importance || 0) * 100).toFixed(0) + '% | 平均访问: ' + (data.avg_access_count || 0).toFixed(2) + '</div>';
            html += '<div style="margin-top:6px;border-top:1px solid #eee;padding-top:6px;">';
            html += '<input id="memory-search-input" type="text" placeholder="搜索记忆..." style="width:100%;font-size:11px;padding:3px 6px;border:1px solid #ddd;border-radius:3px;box-sizing:border-box;">';
            html += '<button onclick="searchMemories()" style="font-size:10px;padding:2px 8px;margin-top:4px;background:#9C27B0;color:white;border:none;border-radius:3px;cursor:pointer;">搜索</button>';
            html += '<div id="memory-search-results" style="margin-top:4px;max-height:120px;overflow-y:auto;"></div>';
            html += '</div>';
            container.innerHTML = html;
        } else if (_currentPanoramaTab === 'relation') {
            const [summaryResp, metricsResp] = await Promise.all([
                fetch('/api/relationship/summary'),
                fetch('/api/relationship/metrics')
            ]);
            const data = await summaryResp.json();
            const metricsData = await metricsResp.json();
            let html = '';
            const metrics = [
                ['信任度', data.trust_level, data.trust_trend],
                ['亲密度', data.intimacy_level, data.intimacy_trend],
                ['理解度', data.understanding_level, null],
            ];
            for (const [label, val, trend] of metrics) {
                if (val != null) {
                    const pct = (val * 100).toFixed(0);
                    const color = val > 0.7 ? '#4CAF50' : val > 0.4 ? '#FF9800' : '#F44336';
                    const trendIcon = trend === 'rising' ? '↑' : trend === 'declining' ? '↓' : '→';
                    html += '<div style="margin:4px 0;">';
                    html += '<div style="display:flex;justify-content:space-between;font-size:11px;"><span>' + label + '</span><span style="color:' + color + ';">' + pct + '% ' + trendIcon + '</span></div>';
                    html += '<div style="height:6px;background:#e0e0e0;border-radius:3px;"><div style="height:6px;width:' + pct + '%;background:' + color + ';border-radius:3px;"></div></div>';
                    html += '</div>';
                }
            }
            html += '<div style="margin-top:6px;font-size:10px;color:#888;">互动: ' + (data.total_interactions || 0) + '次 | 风格: ' + (data.communication_style || '--') + '</div>';
            container.innerHTML = html || '<p style="color:#999;font-size:11px;">暂无关系数据</p>';
        } else if (_currentPanoramaTab === 'system') {
            const [sched, traj, tools, modHealth, trajSearch, bgTasks] = await Promise.all([
                fetch('/api/scheduled-tasks/status'),
                fetch('/api/trajectory/stats'),
                fetch('/api/tools/stats'),
                fetch('/api/module/health'),
                fetch('/api/trajectory/search?limit=5'),
                fetch('/api/background-tasks')
            ]);
            const schedData = await sched.json();
            const trajData = await traj.json();
            const toolsData = await tools.json();
            const modHealthData = await modHealth.json();
            let html = '';
            html += '<div style="margin-bottom:6px;"><b>定时任务:</b> ' + (schedData.running ? '<span style="color:#4CAF50;">运行中</span>' : '<span style="color:#F44336;">已停止</span>') + '</div>';
            const jobs = schedData.jobs || {};
            for (const [name, info] of Object.entries(jobs)) {
                if (info.enabled) {
                    html += '<div style="font-size:10px;color:#666;margin:1px 0;">' + name + ': ' + (info.run_count || 0) + '次 | 间隔' + (info.interval_seconds || 0) + 's</div>';
                }
            }
            html += '<div style="margin-top:6px;padding-top:4px;border-top:1px solid #eee;"><b>轨迹进化:</b> ' + (trajData.total_trajectories || 0) + '条 | 活跃: ' + (trajData.live_trajectories || 0) + ' | 适应度: ' + (trajData.avg_fitness || 0).toFixed(1) + '</div>';
            html += '<div style="margin-top:6px;padding-top:4px;border-top:1px solid #eee;"><b>工具框架:</b> ' + (toolsData.total_tools || 0) + '个工具</div>';
            if (modHealthData && !modHealthData.error) {
                const mods = modHealthData.modules || [];
                const healthy = mods.filter(m => m.status === 'healthy').length;
                html += '<div style="margin-top:6px;padding-top:4px;border-top:1px solid #eee;"><b>模块健康:</b> <span style="color:#4CAF50;">' + healthy + '/' + mods.length + '</span> 健康</div>';
            }
            container.innerHTML = html || '<p style="color:#999;font-size:11px;">暂无系统数据</p>';
        } else if (_currentPanoramaTab === 'introspection') {
            const [reportResp, statusResp, anomaliesResp] = await Promise.all([
                fetch('/api/introspection/report'),
                fetch('/api/introspection/status'),
                fetch('/api/introspection/anomalies')
            ]);
            const report = await reportResp.json();
            const status = await statusResp.json();
            const anomaliesData = await anomaliesResp.json();
            let html = '';
            const healthColor = report.overall_health > 0.8 ? '#4CAF50' : report.overall_health > 0.5 ? '#FF9800' : '#F44336';
            html += '<div style="margin-bottom:6px;"><b>系统健康度:</b> <span style="color:' + healthColor + ';font-weight:bold;">' + (report.overall_health * 100).toFixed(0) + '%</span></div>';
            html += '<div style="margin-bottom:4px;font-size:10px;">检查次数: ' + (status.check_count || 0) + ' | 异常: ' + (report.anomaly_count || 0) + ' | 严重: ' + (report.critical_count || 0) + ' | 重要: ' + (report.major_count || 0) + '</div>';
            if (report.anomalies && report.anomalies.length > 0) {
                html += '<div style="margin-top:4px;border-top:1px solid #eee;padding-top:4px;"><b>异常列表:</b></div>';
                for (const a of report.anomalies.slice(0, 5)) {
                    const sevColor = a.severity === 'critical' ? '#F44336' : a.severity === 'major' ? '#FF9800' : '#999';
                    html += '<div style="font-size:10px;margin:2px 0;"><span style="color:' + sevColor + ';">[' + a.severity + ']</span> ' + (a.title || a.description || '').substring(0, 50) + '</div>';
                }
            }
            if (report.recommendations && report.recommendations.length > 0) {
                html += '<div style="margin-top:4px;border-top:1px solid #eee;padding-top:4px;"><b>建议:</b></div>';
                for (const r of report.recommendations) {
                    html += '<div style="font-size:10px;color:#666;margin:1px 0;">• ' + r + '</div>';
                }
            }
            if (anomaliesData && !anomaliesData.error) {
                const anomList = anomaliesData.anomalies || anomaliesData.recent || [];
                html += '<div style="margin-top:4px;border-top:1px solid #eee;padding-top:4px;"><b>异常详情:</b> ' + (anomList.length === 0 ? '<span style="color:#4CAF50;">无</span>' : anomList.length + '个') + '</div>';
            }
            container.innerHTML = html || '<p style="color:#999;font-size:11px;">暂无内省数据</p>';
        } else if (_currentPanoramaTab === 'knowledgegraph') {
            const resp = await fetch('/api/knowledge-graph/stats');
            const data = await resp.json();
            let html = '';
            html += '<div style="margin-bottom:6px;"><b>知识图谱:</b> ' + (data.node_count || 0) + '个节点 | ' + (data.connection_count || 0) + '条连接</div>';
            if (data.node_type_distribution) {
                html += '<div style="font-size:10px;color:#666;">节点类型: ';
                const types = Object.entries(data.node_type_distribution);
                html += types.map(([t, c]) => t + ':' + c).join(' | ');
                html += '</div>';
            }
            if (data.connection_type_distribution) {
                html += '<div style="font-size:10px;color:#666;">连接类型: ';
                const ctypes = Object.entries(data.connection_type_distribution);
                html += ctypes.map(([t, c]) => t + ':' + c).join(' | ');
                html += '</div>';
            }
            html += '<div style="margin-top:4px;font-size:10px;color:#888;">平均重要度: ' + (data.avg_importance || 0).toFixed(3) + '</div>';
            const clusterResp = await fetch('/api/knowledge-graph/clusters');
            const clusterData = await clusterResp.json();
            const searchResp = await fetch('/api/knowledge-graph/search?query=');
            const searchData = await searchResp.json();
            if (clusterData.clusters && clusterData.clusters.length > 0) {
                html += '<div style="margin-top:4px;border-top:1px solid #eee;padding-top:4px;"><b>知识群落:</b> ' + clusterData.clusters.length + '个</div>';
                for (const c of clusterData.clusters.slice(0, 5)) {
                    html += '<div style="font-size:10px;color:#666;margin:1px 0;">• ' + c.dominant_type + ': ' + c.size + '个节点</div>';
                }
            }
            if (searchData && !searchData.error) {
                const results = searchData.results || searchData.nodes || [];
                html += '<div style="margin-top:4px;font-size:10px;color:#888;">搜索可用: ' + results.length + '条结果</div>';
            }
            container.innerHTML = html || '<p style="color:#999;font-size:11px;">暂无图谱数据</p>';
        } else if (_currentPanoramaTab === 'alignment') {
            const [statsResp, devsResp] = await Promise.all([
                fetch('/api/alignment/stats'),
                fetch('/api/alignment/deviations?limit=10')
            ]);
            const stats = await statsResp.json();
            const devs = await devsResp.json();
            let html = '';
            const openCount = stats.open || 0;
            const statusColor = openCount === 0 ? '#4CAF50' : openCount > 3 ? '#F44336' : '#FF9800';
            html += '<div style="margin-bottom:6px;"><b>思想对齐状态:</b> <span style="color:' + statusColor + ';font-weight:bold;">' + (openCount === 0 ? '对齐' : openCount + '个偏离') + '</span></div>';
            html += '<div style="font-size:10px;color:#666;">总记录: ' + (stats.total || 0) + ' | 已修正: ' + (stats.corrected || 0) + '</div>';
            if (stats.by_type && Object.keys(stats.by_type).length > 0) {
                html += '<div style="margin-top:4px;font-size:10px;">偏离类型: ';
                html += Object.entries(stats.by_type).map(([t, c]) => t + ':' + c).join(' | ');
                html += '</div>';
            }
            if (devs.deviations && devs.deviations.length > 0) {
                html += '<div style="margin-top:4px;border-top:1px solid #eee;padding-top:4px;"><b>未修正偏离:</b></div>';
                for (const d of devs.deviations) {
                    const sevColor = d.severity === 'critical' ? '#F44336' : d.severity === 'major' ? '#FF9800' : '#999';
                    html += '<div style="font-size:10px;margin:2px 0;"><span style="color:' + sevColor + ';">[' + d.severity + ']</span> ' + d.module + ': ' + (d.description || '').substring(0, 40);
                    html += ' <button onclick="correctDeviation(' + d.id + ')" style="font-size:9px;padding:1px 4px;background:#4CAF50;color:white;border:none;border-radius:2px;cursor:pointer;">修正</button>';
                    html += '</div>';
                }
            } else {
                html += '<div style="margin-top:4px;font-size:10px;color:#4CAF50;">✅ 所有模块与核心思想对齐</div>';
            }
            html += '<div style="margin-top:6px;border-top:1px solid #eee;padding-top:4px;font-size:9px;color:#aaa;">审查标准: 闭环适配 / SpiritCore / 可塑性 / 同行者 / 能力关系</div>';
            container.innerHTML = html || '<p style="color:#999;font-size:11px;">暂无对齐数据</p>';
        } else if (_currentPanoramaTab === 'tools') {
            const [toolsResp, statsResp, histResp] = await Promise.all([
                fetch('/api/tools'),
                fetch('/api/tools/stats'),
                fetch('/api/tools/history?limit=10')
            ]);
            const tools = await toolsResp.json();
            const stats = await statsResp.json();
            const histData = await histResp.json();
            let html = '';
            html += '<div style="margin-bottom:6px;"><b>工具框架:</b> ' + (stats.total_tools || 0) + '个工具</div>';
            const toolList = tools.tools || [];
            if (toolList.length > 0) {
                for (const t of toolList) {
                    const catColors = {search: '#2196F3', computation: '#4CAF50', knowledge: '#FF9800', verification: '#9C27B0', user: '#00BCD4'};
                    const color = catColors[t.category] || '#666';
                    html += '<div style="margin:3px 0;padding:4px 6px;background:#f5f5f5;border-radius:3px;border-left:3px solid ' + color + ';">';
                    html += '<div style="display:flex;justify-content:space-between;font-size:11px;">';
                    html += '<span><b>' + t.name + '</b></span>';
                    html += '<span style="font-size:9px;color:#888;">' + (t.category || '') + '</span>';
                    html += '</div>';
                    if (t.description) html += '<div style="font-size:10px;color:#666;">' + t.description.substring(0, 60) + '</div>';
                    html += '</div>';
                }
            } else {
                html += '<div style="font-size:10px;color:#999;">暂无工具</div>';
            }
            html += '<div style="margin-top:8px;border-top:1px solid #eee;padding-top:6px;">';
            html += '<div style="font-size:10px;color:#888;margin-bottom:4px;">执行工具:</div>';
            html += '<select id="tool-select" style="width:100%;font-size:11px;padding:3px;border:1px solid #ddd;border-radius:3px;box-sizing:border-box;">';
            for (const t of toolList) {
                html += '<option value="' + t.name + '">' + t.name + ' - ' + (t.description || '').substring(0, 40) + '</option>';
            }
            html += '</select>';
            html += '<input id="tool-args-input" type="text" placeholder="参数 (JSON)" style="width:100%;font-size:11px;padding:3px 6px;border:1px solid #ddd;border-radius:3px;box-sizing:border-box;margin-top:4px;">';
            html += '<button onclick="executeTool()" style="font-size:10px;padding:2px 8px;margin-top:4px;background:#2196F3;color:white;border:none;border-radius:3px;cursor:pointer;">执行</button>';
            html += '<div id="tool-execute-result" style="margin-top:4px;max-height:100px;overflow-y:auto;font-size:10px;"></div>';
            html += '</div>';
            if (histData.history && histData.history.length > 0) {
                html += '<div style="margin-top:8px;border-top:1px solid #eee;padding-top:6px;"><b>执行历史:</b> ' + histData.history.length + '条</div>';
                for (const h of histData.history.slice(0, 8)) {
                    const succColor = h.success ? '#4CAF50' : '#F44336';
                    html += '<div style="font-size:9px;margin:2px 0;padding:2px 4px;background:#f5f5f5;border-radius:2px;">';
                    html += '<span style="color:' + succColor + ';">' + (h.success ? '✓' : '✗') + '</span> ' + h.tool_name;
                    if (h.duration_ms) html += ' <span style="color:#888;">' + h.duration_ms + 'ms</span>';
                    html += '</div>';
                }
            }
            container.innerHTML = html;
        } else if (_currentPanoramaTab === 'audit') {
            const resp = await fetch('/api/system/audit');
            const data = await resp.json();
            let html = '';
            if (data.error) {
                html = '<p style="color:#F44336;font-size:11px;">错误: ' + data.error + '</p>';
            } else {
                const gaps = data.gaps || [];
                const score = data.overall_score || 0;
                const scoreColor = score > 0.8 ? '#4CAF50' : score > 0.5 ? '#FF9800' : '#F44336';
                html += '<div style="text-align:center;margin-bottom:8px;">';
                html += '<div style="font-size:24px;font-weight:bold;color:' + scoreColor + ';">' + (score * 100).toFixed(0) + '%</div>';
                html += '<div style="font-size:11px;color:#888;">系统审核评分</div></div>';
                if (gaps.length > 0) {
                    html += '<div style="margin-bottom:4px;"><b>差距列表 (' + gaps.length + '):</b></div>';
                    for (const g of gaps.slice(0, 8)) {
                        const sevColor = g.severity === 'critical' ? '#F44336' : g.severity === 'major' ? '#FF9800' : '#999';
                        html += '<div style="font-size:10px;margin:2px 0;padding:2px 4px;border-left:2px solid ' + sevColor + ';">';
                        html += (g.module || '') + ': ' + (g.description || '').substring(0, 50);
                        html += '</div>';
                    }
                } else {
                    html += '<div style="color:#4CAF50;font-size:11px;">系统审核通过，无差距</div>';
                }
                if (data.recommendations && data.recommendations.length > 0) {
                    html += '<div style="margin-top:4px;border-top:1px solid #eee;padding-top:4px;"><b>建议:</b></div>';
                    for (const r of data.recommendations.slice(0, 3)) {
                        html += '<div style="font-size:10px;color:#666;margin:1px 0;">• ' + r + '</div>';
                    }
                }
            }
            container.innerHTML = html || '<p style="color:#999;font-size:11px;">暂无审核数据</p>';
        } else if (_currentPanoramaTab === 'cbnr') {
            let html = '';
            html += '<div style="text-align:center;margin-bottom:8px;">';
            html += '<div style="font-size:16px;font-weight:bold;color:#9C27B0;">CBNR 核心枢纽</div>';
            html += '<div style="font-size:10px;color:#888;">认知规范化 · 瓶颈 · 残差</div></div>';
            html += '<div style="margin-bottom:6px;">';
            html += '<input id="cbnr-input" type="text" placeholder="输入测试文本" style="font-size:11px;padding:3px 6px;width:60%;border:1px solid #ddd;border-radius:3px;">';
            html += '<button onclick="testCBNR()" style="font-size:10px;padding:2px 8px;background:#9C27B0;color:white;border:none;border-radius:3px;cursor:pointer;margin-left:4px;">处理</button>';
            html += '</div>';
            html += '<div id="cbnr-result" style="font-size:10px;color:#666;">点击"处理"测试CBNR三层管道</div>';
            html += '<div style="margin-top:8px;border-top:1px solid #eee;padding-top:4px;">';
            html += '<div style="font-size:10px;font-weight:bold;color:#607D8B;margin-bottom:4px;">三层关键问句</div>';
            html += '<div style="font-size:9px;color:#666;margin:2px 0;padding:2px 4px;background:#f5f5f5;border-radius:2px;">L1 规范化：我是否已重置到正确的基准状态？</div>';
            html += '<div style="font-size:9px;color:#666;margin:2px 0;padding:2px 4px;background:#f5f5f5;border-radius:2px;">L2 瓶颈：这个问题的本质是什么？我可以安全地忽略什么？</div>';
            html += '<div style="font-size:9px;color:#666;margin:2px 0;padding:2px 4px;background:#f5f5f5;border-radius:2px;">L3 残差：这个问题与哪些已处理问题相似？我能在旧方案上只调整差异？</div>';
            html += '</div>';
            try {
                const statsResp = await fetch('/api/cbnr/stats');
                const stats = await statsResp.json();
                if (!stats.error) {
                    html += '<div style="margin-top:6px;border-top:1px solid #eee;padding-top:4px;">';
                    html += '<div style="font-size:10px;font-weight:bold;color:#607D8B;">统计</div>';
                    html += '<div style="font-size:9px;color:#888;">处理次数: ' + (stats.process_count||0) + ' | 平均耗时: ' + ((stats.avg_processing_time_ms||0).toFixed(1)) + 'ms</div>';
                    html += '</div>';
                }
            } catch(e) {}
            container.innerHTML = html;
        }
    } catch (e) {
        container.innerHTML = '<p style="color:#F44336;font-size:11px;">加载失败: ' + e.message + '</p>';
    }
}

// ==================== 主动性SSE订阅 ====================

// ==================== 全景Tab辅助函数 ====================
async function defenseAction(action) {
    const urls = {
        repair: '/api/defense/repair/run',
        circuit_reset: '/api/defense/circuit/reset',
        isolation_release: '/api/defense/isolation/release'
    };
    try {
        const resp = await fetch(urls[action], {method: 'POST'});
        const data = await resp.json();
        if (data.error) {
            alert('操作失败: ' + data.error);
        } else {
            alert('操作成功');
            refreshSystemPanorama();
        }
    } catch (e) {
        alert('请求失败: ' + e.message);
    }
}

async function searchFacts() {
    const query = document.getElementById('fact-search-input')?.value;
    if (!query) return;
    const resultsDiv = document.getElementById('fact-search-results');
    if (!resultsDiv) return;
    try {
        const resp = await fetch('/api/facts/search?query=' + encodeURIComponent(query));
        const data = await resp.json();
        const results = data.results || data.facts || [];
        if (results.length === 0) {
            resultsDiv.innerHTML = '<div style="font-size:10px;color:#999;">无结果</div>';
        } else {
            let html = '';
            for (const f of results.slice(0, 10)) {
                html += '<div style="font-size:10px;margin:2px 0;padding:2px 4px;background:#f5f5f5;border-radius:2px;">' + (f.content || f.text || JSON.stringify(f)).substring(0, 80) + '</div>';
            }
            resultsDiv.innerHTML = html;
        }
    } catch (e) {
        resultsDiv.innerHTML = '<div style="font-size:10px;color:#F44336;">搜索失败</div>';
    }
}

async function addFact() {
    const content = document.getElementById('fact-add-input')?.value;
    if (!content) return;
    try {
        const resp = await fetch('/api/facts/add', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({content: content, type: 'positive'})
        });
        const data = await resp.json();
        if (data.error) {
            alert('添加失败: ' + data.error);
        } else {
            document.getElementById('fact-add-input').value = '';
            alert('事实已添加');
            refreshSystemPanorama();
        }
    } catch (e) {
        alert('请求失败: ' + e.message);
    }
}

async function correctFact() {
    const original = document.getElementById('fact-correct-original')?.value;
    const corrected = document.getElementById('fact-correct-new')?.value;
    if (!original || !corrected) return;
    try {
        const resp = await fetch('/api/facts/correct', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({original: original, corrected: corrected})
        });
        const data = await resp.json();
        if (data.error) {
            alert('纠正失败: ' + data.error);
        } else {
            alert('事实已纠正');
            refreshSystemPanorama();
        }
    } catch (e) {
        alert('请求失败: ' + e.message);
    }
}

async function searchMemories() {
    const query = document.getElementById('memory-search-input')?.value;
    if (!query) return;
    const resultsDiv = document.getElementById('memory-search-results');
    if (!resultsDiv) return;
    try {
        const resp = await fetch('/api/memory/search?query=' + encodeURIComponent(query));
        const data = await resp.json();
        const results = data.results || data.memories || [];
        if (results.length === 0) {
            resultsDiv.innerHTML = '<div style="font-size:10px;color:#999;">无结果</div>';
        } else {
            let html = '';
            for (const m of results.slice(0, 10)) {
                const typeLabels = {conversation: '对话', knowledge: '知识', experience: '经验', emotion: '情感', relationship: '关系', skill: '技能'};
                html += '<div style="font-size:10px;margin:2px 0;padding:2px 4px;background:#f5f5f5;border-radius:2px;">';
                html += '<span style="color:#9C27B0;">[' + (typeLabels[m.type] || m.type || '') + ']</span> ' + (m.content || m.text || '').substring(0, 80);
                html += '</div>';
            }
            resultsDiv.innerHTML = html;
        }
    } catch (e) {
        resultsDiv.innerHTML = '<div style="font-size:10px;color:#F44336;">搜索失败</div>';
    }
}

async function executeTool() {
    const toolName = document.getElementById('tool-select')?.value;
    const argsStr = document.getElementById('tool-args-input')?.value;
    const resultDiv = document.getElementById('tool-execute-result');
    if (!toolName || !resultDiv) return;
    resultDiv.innerHTML = '<div style="color:#888;">执行中...</div>';
    try {
        let args = {};
        if (argsStr) {
            try { args = JSON.parse(argsStr); } catch { args = {input: argsStr}; }
        }
        const resp = await fetch('/api/tools/execute', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({tool_name: toolName, arguments: args})
        });
        const data = await resp.json();
        if (data.error) {
            resultDiv.innerHTML = '<div style="color:#F44336;">失败: ' + data.error + '</div>';
        } else {
            const result = typeof data.result === 'string' ? data.result : JSON.stringify(data.result || data).substring(0, 200);
            resultDiv.innerHTML = '<div style="color:#4CAF50;">' + result + '</div>';
        }
    } catch (e) {
        resultDiv.innerHTML = '<div style="color:#F44336;">请求失败: ' + e.message + '</div>';
    }
}

async function triggerAgentCollab() {
    const query = document.getElementById('agent-query-input')?.value;
    const resultDiv = document.getElementById('agent-collab-result');
    if (!query || !resultDiv) return;
    resultDiv.innerHTML = '<div style="color:#888;">协作中...</div>';
    try {
        const resp = await fetch('/api/agent/collaborate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({query: query})
        });
        const data = await resp.json();
        if (data.error) {
            resultDiv.innerHTML = '<div style="color:#F44336;">失败: ' + data.error + '</div>';
        } else {
            const quality = data.quality_score || data.quality || 'N/A';
            const iterations = data.iterations || data.iteration_count || 0;
            const answer = (data.final_answer || data.answer || '').substring(0, 150);
            resultDiv.innerHTML = '<div style="color:#4CAF50;">质量: ' + quality + ' | 迭代: ' + iterations + '</div><div style="color:#666;margin-top:2px;">' + answer + '</div>';
        }
    } catch (e) {
        resultDiv.innerHTML = '<div style="color:#F44336;">请求失败: ' + e.message + '</div>';
    }
}

async function truthsReorg(action) {
    const resultDiv = document.getElementById('reorg-result');
    if (!resultDiv) return;
    resultDiv.innerHTML = '<div style="color:#888;">处理中...</div>';
    try {
        const resp = await fetch('/api/truths/reorganization/' + action, {method: 'POST'});
        const data = await resp.json();
        if (data.error) {
            resultDiv.innerHTML = '<div style="color:#F44336;">失败: ' + data.error + '</div>';
        } else {
            const summary = data.proposals ? data.proposals.length + '个提议' : data.executed ? data.executed + '个已执行' : '完成';
            resultDiv.innerHTML = '<div style="color:#4CAF50;">' + summary + '</div>';
            refreshSystemPanorama();
        }
    } catch (e) {
        resultDiv.innerHTML = '<div style="color:#F44336;">请求失败: ' + e.message + '</div>';
    }
}

async function evalProactivity() {
    const resultDiv = document.getElementById('presence-action-result');
    if (!resultDiv) return;
    resultDiv.innerHTML = '<div style="color:#888;">评估中...</div>';
    try {
        const resp = await fetch('/api/proactivity/evaluate');
        const data = await resp.json();
        if (data.error) {
            resultDiv.innerHTML = '<div style="color:#F44336;">失败: ' + data.error + '</div>';
        } else {
            const should = data.should_act ? '需要行动' : '无需行动';
            const score = data.proactivity_score != null ? (data.proactivity_score * 100).toFixed(0) + '%' : 'N/A';
            resultDiv.innerHTML = '<div style="color:#4CAF50;">' + should + ' | 主动性: ' + score + '</div>';
        }
    } catch (e) {
        resultDiv.innerHTML = '<div style="color:#F44336;">请求失败: ' + e.message + '</div>';
    }
}

async function closedLoopOrchestrate() {
    const resultDiv = document.getElementById('presence-action-result');
    if (!resultDiv) return;
    resultDiv.innerHTML = '<div style="color:#888;">编排中...</div>';
    try {
        const resp = await fetch('/api/closed-loop/orchestrate', {method: 'POST'});
        const data = await resp.json();
        if (data.error) {
            resultDiv.innerHTML = '<div style="color:#F44336;">失败: ' + data.error + '</div>';
        } else {
            const loops = data.loops_completed || data.completed || 0;
            resultDiv.innerHTML = '<div style="color:#4CAF50;">闭环完成: ' + loops + '个</div>';
        }
    } catch (e) {
        resultDiv.innerHTML = '<div style="color:#F44336;">请求失败: ' + e.message + '</div>';
    }
}

let proactivitySource = null;
let proactivityReconnectTimer = null;

function connectProactivity() {
    if (proactivitySource) {
        proactivitySource.close();
    }

    try {
        proactivitySource = new EventSource(API_BASE + '/api/proactivity/stream');

        proactivitySource.onmessage = function(event) {
            try {
                const msg = JSON.parse(event.data);
                showProactivityMessage(msg);
            } catch (e) {
                console.warn('主动性消息解析失败:', e);
            }
        };

        proactivitySource.onerror = function() {
            proactivitySource.close();
            proactivitySource = null;
            if (proactivityReconnectTimer) clearTimeout(proactivityReconnectTimer);
            proactivityReconnectTimer = setTimeout(connectProactivity, 30000);
        };
    } catch (e) {
        console.warn('SSE连接失败:', e);
    }
}

function showProactivityMessage(msg) {
    const messagesDiv = document.getElementById('messages');
    if (!messagesDiv) return;

    const typeConfig = {
        greeting: { icon: '👋', bg: '#E8F5E9', border: '#4CAF50' },
        reminder: { icon: '💡', bg: '#FFF3E0', border: '#FF9800' },
        discovery: { icon: '🔍', bg: '#E3F2FD', border: '#2196F3' },
        system_anomaly: { icon: '⚠️', bg: '#FFEBEE', border: '#F44336' },
        learning: { icon: '📚', bg: '#F3E5F5', border: '#9C27B0' },
        reflection: { icon: '🪞', bg: '#E0F7FA', border: '#00BCD4' },
    };

    const config = typeConfig[msg.type] || typeConfig.discovery;
    const content = msg.content || msg.message || msg.detail || '';
    if (!content) return;

    const proactivityDiv = document.createElement('div');
    proactivityDiv.className = 'message system';
    proactivityDiv.style.cssText = 'animation: fadeIn 0.3s ease-in;';

    let html = `<div class="message-content" style="background:${config.bg};border-left:3px solid ${config.border};padding:8px 12px;border-radius:6px;">`;
    html += `<div style="font-size:12px;color:#666;margin-bottom:4px;">${config.icon} 系统主动消息 · ${msg.type || 'info'}</div>`;
    html += `<div style="font-size:13px;line-height:1.6;">${renderMarkdown(content)}</div>`;
    if (msg.recommendations && msg.recommendations.length > 0) {
        html += `<div style="margin-top:6px;font-size:11px;color:#888;">建议: ${msg.recommendations.slice(0, 2).join(' | ')}</div>`;
    }
    html += '</div>';

    proactivityDiv.innerHTML = html;
    messagesDiv.appendChild(proactivityDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    setTimeout(() => {
        if (proactivityDiv.parentNode) {
            proactivityDiv.style.transition = 'opacity 1s';
            proactivityDiv.style.opacity = '0.6';
        }
    }, 30000);
}

connectProactivity();

async function testProactivity() {
    const resultDiv = document.getElementById('presence-action-result');
    if (!resultDiv) return;
    resultDiv.innerHTML = '<div style="color:#888;">测试中...</div>';
    try {
        const resp = await fetch('/api/proactivity/test', {method: 'POST'});
        const data = await resp.json();
        if (data.error) {
            resultDiv.innerHTML = '<div style="color:#F44336;">失败: ' + data.error + '</div>';
        } else {
            const triggered = data.triggered || data.actions_triggered || 0;
            resultDiv.innerHTML = '<div style="color:#4CAF50;">主动性测试完成，触发: ' + triggered + '个行动</div>';
        }
    } catch (e) {
        resultDiv.innerHTML = '<div style="color:#F44336;">请求失败: ' + e.message + '</div>';
    }
}

async function loadModuleHealth() {
    try {
        const resp = await fetch('/api/module/health');
        const data = await resp.json();
        const container = document.getElementById('module-health-info');
        if (container && data.modules) {
            const healthy = data.modules.filter(m => m.status === 'healthy').length;
            const total = data.modules.length;
            container.innerHTML = '<span style="color:#4CAF50;">模块健康: ' + healthy + '/' + total + '</span>';
        }
        return data;
    } catch (e) {
        console.warn('模块健康查询失败:', e);
        return null;
    }
}

async function loadIntrospectionAnomalies() {
    try {
        const resp = await fetch('/api/introspection/anomalies');
        return await resp.json();
    } catch (e) { return null; }
}

async function loadReflectionStats() {
    try {
        const resp = await fetch('/api/reflection/stats');
        return await resp.json();
    } catch (e) { return null; }
}

async function searchKnowledgeGraph(query) {
    try {
        const resp = await fetch('/api/knowledge-graph/search?query=' + encodeURIComponent(query));
        return await resp.json();
    } catch (e) { return null; }
}

async function loadEventsStats() {
    try {
        const resp = await fetch('/api/events/stats');
        return await resp.json();
    } catch (e) { return null; }
}

async function loadInputProcessorDemo() {
    try {
        const resp = await fetch('/api/input-processor/demo');
        return await resp.json();
    } catch (e) { return null; }
}

async function runEvolution() {
    try {
        const resp = await fetch('/api/evolution/run', {method: 'POST'});
        return await resp.json();
    } catch (e) { return null; }
}

async function clearModule(moduleName) {
    try {
        const resp = await fetch('/api/module/clear', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({module: moduleName})
        });
        return await resp.json();
    } catch (e) { return null; }
}

async function runReorganization() {
    try {
        const resp = await fetch('/api/reorganization/run', {method: 'POST'});
        const data = await resp.json();
        if (data.error) {
            alert('重组失败: ' + data.error);
        } else {
            alert('自动重组完成: ' + (data.reorganized || 0) + '条');
            refreshSystemPanorama();
        }
    } catch (e) {
        alert('请求失败: ' + e.message);
    }
}

async function executeForgetting() {
    try {
        const resp = await fetch('/api/forgetting/execute', {method: 'POST'});
        const data = await resp.json();
        if (data.error) {
            alert('遗忘失败: ' + data.error);
        } else {
            alert('遗忘完成: ' + (data.forgotten || 0) + '条');
            refreshSystemPanorama();
        }
    } catch (e) {
        alert('请求失败: ' + e.message);
    }
}

async function correctDeviation(devId) {
    try {
        const resp = await fetch('/api/alignment/correct/' + devId, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({correction: '已修正'})
        });
        const data = await resp.json();
        if (data.error) {
            alert('修正失败: ' + data.error);
        } else {
            alert('偏离已修正');
            refreshSystemPanorama();
        }
    } catch (e) {
        alert('请求失败: ' + e.message);
    }
}

async function sendPresenceSignal() {
    try {
        const resp = await fetch('/api/presence/signal', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({signal_type: 'user_ping', data: {}})
        });
        const data = await resp.json();
        document.getElementById('presence-action-result').textContent = data.message || '信号已发送';
        setTimeout(() => refreshSystemPanorama(), 1000);
    } catch (e) {
        document.getElementById('presence-action-result').textContent = '失败: ' + e.message;
    }
}

async function forcePresenceState() {
    const state = document.getElementById('force-state-select').value;
    try {
        const resp = await fetch('/api/presence/force-state', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({state: state})
        });
        const data = await resp.json();
        document.getElementById('presence-action-result').textContent = data.message || '状态已切换';
        setTimeout(() => refreshSystemPanorama(), 1000);
    } catch (e) {
        document.getElementById('presence-action-result').textContent = '失败: ' + e.message;
    }
}

async function queryTaskStatus(taskId) {
    try {
        const resp = await fetch('/api/tasks/' + taskId);
        const data = await resp.json();
        return data;
    } catch (e) {
        return {error: e.message};
    }
}

async function queryEventHistory(eventType) {
    try {
        const resp = await fetch('/api/events/history/' + eventType);
        const data = await resp.json();
        return data;
    } catch (e) {
        return {error: e.message};
    }
}

async function autoGenerateCoverage() {
    try {
        const resp = await fetch('/api/coverage/auto-generate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({})
        });
        const data = await resp.json();
        if (data.error) {
            alert('自动生成失败: ' + data.error);
        } else {
            alert('自动生成完成: ' + (data.generated || 0) + '个片段');
            refreshSystemPanorama();
        }
    } catch (e) {
        alert('请求失败: ' + e.message);
    }
}

async function testCBNR() {
    const input = document.getElementById('cbnr-input').value || '测试输入';
    const resultDiv = document.getElementById('cbnr-result');
    resultDiv.innerHTML = '<span style="color:#999;">处理中...</span>';
    try {
        const resp = await fetch('/api/cbnr/process', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({input: input})
        });
        const data = await resp.json();
        if (data.error) {
            resultDiv.innerHTML = '<span style="color:#F44336;">错误: ' + data.error + '</span>';
        } else {
            let html = '';
            html += '<div style="margin:4px 0;padding:4px;background:#E8F5E9;border-radius:3px;">';
            html += '<b>L1 规范化</b>: 不确定性=' + (data.l1?.uncertainty||0).toFixed(2) + ' 强度=' + (data.l1?.strength||0).toFixed(2);
            if (data.l1?.biases?.length) html += ' 偏差=' + data.l1.biases.join(',');
            if (data.l1?.principles?.length) html += ' 原则=' + data.l1.principles.join(',');
            html += '</div>';
            html += '<div style="margin:4px 0;padding:4px;background:#E3F2FD;border-radius:3px;">';
            html += '<b>L2 瓶颈</b>: 压缩=' + (data.l2?.compression_ratio||0).toFixed(2) + ' 冲突ΔF=' + (data.l2?.conflict_delta||0).toFixed(2) + ' 模式=' + (data.l2?.conflict_mode||'?');
            if (data.l2?.topic) html += ' 主题=' + data.l2.topic.substring(0,30);
            html += '</div>';
            html += '<div style="margin:4px 0;padding:4px;background:#F3E5F5;border-radius:3px;">';
            html += '<b>L3 残差</b>: 复用率=' + ((data.l3?.reuse_rate||0)*100).toFixed(0) + '% 搜索树=' + (data.l3?.search_tree_size||0) + ' 保底=' + (data.l3?.fallback_used?'是':'否');
            html += '</div>';
            html += '<div style="font-size:9px;color:#aaa;margin-top:2px;">耗时: ' + (data.processing_time_ms||0).toFixed(1) + 'ms</div>';
            resultDiv.innerHTML = html;
        }
    } catch (e) {
        resultDiv.innerHTML = '<span style="color:#F44336;">失败: ' + e.message + '</span>';
    }
}
