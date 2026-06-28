// ==================== 版本信息 ====================
// Version: 3.5.0
// Last Update: 2026-06-28
// ==================== 全局配置 ====================
const API_BASE = 'http://localhost:8000';
const APP_VERSION = '3.5.0';

// ==================== 全局变量 ====================
let selectedModel = 'auto';
let conversationHistory = [];

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

// ==================== 本地降级回复（前端兜底） ====================
function _generateLocalFallback(query) {
    const q = query.toLowerCase();
    
    if (q.includes('命运') || q.includes('人生') || q.includes('意义') || q.includes('哲学')) {
        return `关于"${query}"，这是一个哲学与科学交汇的深刻问题：\n\n**不同视角的分析：**\n1. **生物学视角** - 基因遗传决定了我们的部分特质，这是"先天"的部分\n2. **社会学视角** - 家庭环境、教育经历、社会阶层等塑造了我们的机会和选择空间\n3. **心理学视角** - 个人的认知模式、决策习惯、情绪管理能力影响人生轨迹\n4. **哲学视角** - 自由意志与决定论的争论：我们是否真正"选择"了自己的命运？\n5. **复杂性科学** - 微小的初始差异可能通过正反馈放大，导致截然不同的结果\n\n**核心观点：**\n- 命运不是单一因素决定的，而是基因、环境、选择、偶然性共同作用的结果\n- 我们无法选择起点，但可以通过认知升级和持续行动来改变轨迹`;
    }
    if (q.includes('认知') || q.includes('意识') || q.includes('思维') || q.includes('智能')) {
        return `关于"${query}"，这是一个深刻的问题：\n\n**认知的产生涉及多个层面：**\n1. **生物学基础** - 认知源于大脑神经元的连接与活动，约860亿个神经元通过突触形成复杂网络\n2. **感知与输入** - 通过视觉、听觉、触觉等感官接收外界信息\n3. **信息加工** - 大脑对感知信息进行编码、存储、检索和推理\n4. **涌现特性** - 认知不是单个神经元的功能，而是大量简单单元交互后涌现出的复杂特性\n5. **学习与适应** - 通过经验不断调整神经连接（神经可塑性），使认知能力持续进化\n\n**关键理论：**\n- 具身认知：认知不仅在大脑中，还依赖身体与环境的互动\n- 连接主义：认知是神经网络中分布式表征的计算结果\n- 预测编码：大脑不断预测输入，用预测误差来更新内部模型`;
    }
    if (q.includes('为什么')) {
        return `关于"${query}"，从因果分析的角度来思考：\n\n**第一层：直接原因**\n最显而易见的表象是什么？\n\n**第二层：深层原因**\n- **历史因素** - 过去的事件和决策如何塑造了当前的局面？\n- **结构因素** - 系统性的制度、规则或环境如何影响结果？\n- **个体因素** - 人的选择、能力和行为如何发挥作用？\n\n**第三层：根本原因**\n- 追问5个"为什么"：不断追问更深层的因果链\n- 区分必要条件和充分条件\n- 注意因果的复杂性：单一原因很少能解释复杂现象\n\n💡 如果你能告诉我更具体的关注点，我可以给出更精准的分析。`;
    }
    if (q.includes('代码') || q.includes('编程') || q.includes('函数')) {
        return `关于"${query}"，我可以帮助你：\n\n1. **代码生成** - 请告诉我具体需求\n2. **代码解释** - 请提供代码，我会解释原理\n3. **代码优化** - 请提供代码，我给出建议\n\n请告诉我更具体的需求。`;
    }
    if (q.includes('什么是') || q.includes('是什么') || q.includes('介绍')) {
        const topic = query.replace(/什么是|是什么|介绍一下/g, '').trim();
        return `关于"${topic}"：\n\n1. **概念层面** - ${topic}是一个重要的知识领域\n2. **应用层面** - ${topic}在实际中有广泛的应用\n3. **学习方向** - 可以从基础概念、核心原理、实践案例三个维度深入\n\n💡 建议你尝试更具体的问题。`;
    }
    if (q.includes('如何') || q.includes('怎么') || q.includes('怎样')) {
        return `关于"${query}"，我的分析：\n\n1. **问题拆解** - 将复杂问题分解为可执行的小步骤\n2. **方法选择** - 根据具体场景选择最合适的方案\n3. **实践验证** - 通过实际操作来验证和调整\n\n💡 请告诉我更具体的场景和约束条件，我会给出针对性的详细指导。`;
    }
    return `关于"${query}"，我的深度思考：\n\n**1. 问题本质分析**\n这个问题的核心是什么？它属于哪类问题（事实性、价值性、因果性、方法性）？\n\n**2. 多角度审视**\n- **正面视角** - 最直观的理解是什么？\n- **反面视角** - 如果反过来想，会得到什么洞察？\n- **旁观视角** - 第三方如何看待这个问题？\n- **历史视角** - 这个问题在历史上是如何演变的？\n\n**3. 关键变量识别**\n影响这个问题结果的关键变量有哪些？哪些是可控的，哪些是不可控的？\n\n💡 我正在持续学习和进化。如果你能提供更多背景，我可以给出更深入的分析。`;
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
            thinkingDiv.innerHTML = `
                <div class="message-content">
                    <details style="background: #f5f5f5; padding: 8px; border-radius: 5px;">
                        <summary style="cursor: pointer; font-weight: bold;">💭 思考过程 (${elapsed}秒)</summary>
                        <div style="font-size: 13px; margin-top: 8px; line-height: 1.8;">${stepsContainer.innerHTML}</div>
                    </details>
                </div>
            `;
        }, 2000);

        // 显示最终回复
        if (finalResult && finalResult.response) {
            conversationHistory.push({ role: 'assistant', content: finalResult.response });
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
        const response = await fetch(`${API_BASE}/api/recent_learning`);
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
    }
    // 定时刷新
    setInterval(checkHealth, 30000);
    setInterval(loadStats, 60000);
    // 自动检测新模型（每30秒）
    startAutoRefresh(30);
});
