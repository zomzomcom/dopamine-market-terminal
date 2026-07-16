/**
 * 文件名: app.js
 * 功能说明: 全局公共工具函数库
 *          API请求封装 / 数据格式化 / Toast通知 / 全局搜索 / 时间显示
 */

// ==================== API 请求封装 ====================

/**
 * 封装 GET 请求
 * @param {string} url - API 地址
 * @param {object} params - 查询参数
 * @returns {Promise<object>} 响应数据
 */
async function apiGet(url, params = {}) {
    try {
        const query = new URLSearchParams(params).toString();
        const fullUrl = query ? `${url}?${query}` : url;
        const resp = await fetch(fullUrl);
        const data = await resp.json();
        if (!data.success) {
            showToast(data.message || '请求失败', 'error');
            return null;
        }
        return data.data;
    } catch (e) {
        console.error('API GET Error:', e);
        showToast('网络请求失败，请检查后端服务是否启动', 'error');
        return null;
    }
}

/**
 * 封装 POST 请求
 * @param {string} url - API 地址
 * @param {object} body - 请求体
 * @returns {Promise<object>} 响应数据
 */
async function apiPost(url, body = {}) {
    try {
        const resp = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        const data = await resp.json();
        if (!data.success) {
            showToast(data.message || '操作失败', 'error');
            return null;
        }
        if (data.message) showToast(data.message, 'success');
        return data.data;
    } catch (e) {
        console.error('API POST Error:', e);
        showToast('网络请求失败，请检查后端服务是否启动', 'error');
        return null;
    }
}

/**
 * 封装 PUT 请求
 */
async function apiPut(url, body = {}) {
    try {
        const resp = await fetch(url, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        const data = await resp.json();
        if (!data.success) {
            showToast(data.message || '操作失败', 'error');
            return null;
        }
        if (data.message) showToast(data.message, 'success');
        return data.data;
    } catch (e) {
        console.error('API PUT Error:', e);
        showToast('网络请求失败', 'error');
        return null;
    }
}

/**
 * 封装 DELETE 请求
 */
async function apiDelete(url) {
    try {
        const resp = await fetch(url, { method: 'DELETE' });
        const data = await resp.json();
        if (!data.success) {
            showToast(data.message || '删除失败', 'error');
            return null;
        }
        if (data.message) showToast(data.message, 'success');
        return data.data;
    } catch (e) {
        console.error('API DELETE Error:', e);
        showToast('网络请求失败', 'error');
        return null;
    }
}

// ==================== 数据格式化 ====================

/**
 * 格式化数字（千分位）
 * @param {number} num
 * @param {number} decimals - 小数位数
 * @returns {string}
 */
function formatNumber(num, decimals = 2) {
    if (num === null || num === undefined || isNaN(num)) return '--';
    return Number(num).toLocaleString('zh-CN', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
    });
}

/**
 * 格式化大数字（亿/万）
 * @param {number} num
 * @returns {string}
 */
function formatBigNumber(num) {
    if (num === null || num === undefined || isNaN(num)) return '--';
    const abs = Math.abs(num);
    if (abs >= 1e8) return (num / 1e8).toFixed(2) + '亿';
    if (abs >= 1e4) return (num / 1e4).toFixed(2) + '万';
    return num.toFixed(2);
}

/**
 * 格式化成交量（手）
 */
function formatVolume(vol) {
    if (!vol || isNaN(vol)) return '--';
    return formatBigNumber(vol / 100); // 股转手
}

/**
 * 获取涨跌样式类名
 * @param {number} val - 涨跌值
 * @returns {string} 'text-up' | 'text-down' | 'text-flat'
 */
function getChangeClass(val) {
    if (val > 0) return 'text-up';
    if (val < 0) return 'text-down';
    return 'text-flat';
}

/**
 * 获取涨跌符号
 */
function getChangeSign(val) {
    if (val > 0) return '+';
    return '';
}

/**
 * 获取涨跌背景色类名
 */
function getBgClass(val) {
    if (val > 0) return 'bg-up';
    if (val < 0) return 'bg-down';
    return '';
}

// ==================== Toast 通知 ====================

/**
 * 显示 Toast 通知
 * @param {string} message - 消息内容
 * @param {string} type - 类型: success/error/info
 * @param {number} duration - 持续时间(毫秒)
 */
function showToast(message, type = 'info', duration = 3000) {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const icons = { success: '✅', error: '❌', info: '💡' };
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span>${icons[type] || ''}</span> <span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'toastSlide 0.3s reverse';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// ==================== 全局搜索 ====================

let searchTimer = null;

document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('globalSearch');
    const resultsDiv = document.getElementById('searchResults');

    if (searchInput) {
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimer);
            const keyword = this.value.trim();
            if (keyword.length < 1) {
                resultsDiv.classList.remove('show');
                return;
            }
            // 防抖搜索
            searchTimer = setTimeout(async () => {
                const results = await apiGet('/api/stock/search', { keyword });
                if (results && results.length > 0) {
                    resultsDiv.innerHTML = results.map(s => `
                        <div class="search-result-item" onclick="goToStock('${s.code}')">
                            <span class="sr-code">${s.code}</span>
                            <span class="sr-name">${s.name}</span>
                        </div>
                    `).join('');
                    resultsDiv.classList.add('show');
                } else {
                    resultsDiv.innerHTML = '<div class="search-result-item"><span style="color:var(--text-muted);">未找到相关股票</span></div>';
                    resultsDiv.classList.add('show');
                }
            }, 300);
        });

        // 点击外部关闭搜索结果
        document.addEventListener('click', function(e) {
            if (!searchInput.contains(e.target) && !resultsDiv.contains(e.target)) {
                resultsDiv.classList.remove('show');
            }
        });
    }

    // 启动时钟 + 数据源检测
    updateClock();
    setInterval(updateClock, 1000);
    updateDataSourceStatus();
    setInterval(updateDataSourceStatus, 5000);
});

/**
 * 跳转到个股详情页
 */
function goToStock(code) {
    window.location.href = `/stock/${code}`;
}

/**
 * 更新导航栏时钟
 */
function updateClock() {
    const el = document.getElementById('navTime');
    if (!el) return;
    const now = new Date();
    const h = String(now.getHours()).padStart(2, '0');
    const m = String(now.getMinutes()).padStart(2, '0');
    const s = String(now.getSeconds()).padStart(2, '0');
    const days = ['日', '一', '二', '三', '四', '五', '六'];
    el.textContent = `${now.getMonth() + 1}月${now.getDate()}日 周${days[now.getDay()]} ${h}:${m}:${s}`;
}

/**
 * 更新数据源状态指示器
 */
async function updateDataSourceStatus() {
    const el = document.getElementById('navStatus');
    if (!el) return;

    try {
        const resp = await fetch('/api/status');
        const json = await resp.json();
        const source = json.data && json.data.data_source;

        const dot = el.querySelector('.status-dot');
        const text = el.querySelector('.status-text');

        if (source === 'live') {
            el.className = 'nav-status live';
            if (dot) dot.style.background = '#00b894';
            if (text) text.textContent = '实时行情';
            el.title = '数据来源: 东方财富实时接口 ✅';
        } else if (source === 'mock') {
            el.className = 'nav-status mock';
            if (dot) dot.style.background = '#f39c12';
            if (text) text.textContent = '模拟数据';
            el.title = '⚠️ 行情接口异常，当前为模拟数据';
        } else {
            el.className = 'nav-status';
            if (dot) dot.style.background = '#6c7293';
            if (text) text.textContent = '检测中...';
        }
    } catch (e) {
        const dot = el.querySelector('.status-dot');
        const text = el.querySelector('.status-text');
        el.className = 'nav-status error';
        if (dot) dot.style.background = '#e74c3c';
        if (text) text.textContent = '连接断开';
        el.title = '❌ 后端服务不可用';
    }
}

/**
 * 加入自选股（从详情页调用）
 */
async function addToWatchlist(code) {
    const result = await apiPost('/api/watchlist', { stock_code: code });
    if (result !== null) {
        // 成功消息已在 apiPost 中显示
    }
}
