/**
 * 文件名: market.js
 * 功能说明: 行情首页逻辑 - 大盘指数 + A股排行列表 + 分页 + 实时刷新
 */

let currentPage = 1;
let currentSort = { field: 'f3', order: 'desc' };
let refreshTimer = null;
let lastUpdateTime = null;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    loadIndices();
    loadStocks();
    loadNews();
    startAutoRefresh();
});

/**
 * 加载大盘指数
 */
async function loadIndices() {
    const data = await apiGet('/api/market/indices');
    const grid = document.getElementById('indexGrid');
    if (!grid) return;

    if (!data || data.length === 0) {
        grid.innerHTML = '<div class="empty-state"><div class="emoji">📉</div><div class="text">暂无行情数据<br><small style="color:var(--text-muted);">可能处于非交易时段或网络异常</small></div></div>';
        return;
    }

    grid.innerHTML = data.map(idx => {
        const cls = idx.change_pct > 0 ? 'up' : (idx.change_pct < 0 ? 'down' : '');
        const colorCls = getChangeClass(idx.change_pct);
        const sign = getChangeSign(idx.change_pct);
        return `
            <div class="index-card ${cls}" onclick="goToStock('${idx.code}')">
                <div class="index-name">${idx.name}</div>
                <div class="index-price ${colorCls}">${formatNumber(idx.price)}</div>
                <div class="index-change ${colorCls}">
                    <span class="change-badge ${getBgClass(idx.change_pct)}">${sign}${formatNumber(idx.change)}</span>
                    <span class="change-badge ${getBgClass(idx.change_pct)}">${sign}${formatNumber(idx.change_pct)}%</span>
                </div>
            </div>
        `;
    }).join('');
}

/**
 * 加载热点讯息
 */
async function loadNews() {
    const card = document.getElementById('newsCard');
    const list = document.getElementById('newsList');
    const badge = document.getElementById('newsRefreshBadge');
    if (!card || !list) return;

    card.style.display = 'block';

    try {
        const resp = await fetch('/api/news?count=12');
        const json = await resp.json();

        // 市场状态
        const statusEl = document.getElementById('marketStatus');
        if (statusEl && json.market_open !== undefined) {
            statusEl.textContent = json.market_open ? '🟢 交易中' : '🔴 已收盘';
            statusEl.className = 'market-status ' + (json.market_open ? 'open' : 'closed');
        }

        const news = json.data || [];
        if (news.length === 0) {
            list.innerHTML = '<div class="empty-state"><div class="text">暂无热点讯息</div></div>';
        } else {
            list.innerHTML = news.slice(0, 10).map(n => `
                <a class="news-item" href="${n.url || '#'}" target="_blank" rel="noopener">
                    <span class="news-time">${n.time || ''}</span>
                    <span class="news-title">${n.title}</span>
                    <span class="news-source">${n.source || ''}</span>
                    ${n.intro ? `<span class="news-intro">${n.intro}</span>` : ''}
                </a>
            `).join('');
        }

        // 更新刷新时间
        if (badge) {
            const now = new Date();
            const ts = String(now.getHours()).padStart(2,'0') + ':' +
                       String(now.getMinutes()).padStart(2,'0') + ':' +
                       String(now.getSeconds()).padStart(2,'0');
            badge.textContent = '更新 ' + ts;
            badge.style.opacity = '1';
            setTimeout(() => { badge.style.opacity = '0.6'; }, 1500);
        }
    } catch (e) {
        list.innerHTML = '<div class="empty-state"><div class="text">热点讯息加载失败</div></div>';
    }
}

/**
 * 加载股票列表
 * @param {string} sortField - 排序字段
 * @param {string} sortOrder - 排序方向
 * @param {number} page - 页码
 */
async function loadStocks(sortField, sortOrder, page) {
    if (sortField) currentSort = { field: sortField, order: sortOrder || 'desc' };
    if (page) currentPage = page;

    const data = await apiGet('/api/market/stocks', {
        page: currentPage,
        page_size: 30,
        sort_field: currentSort.field,
        sort_order: currentSort.order,
    });

    const tbody = document.getElementById('stockTableBody');
    if (!tbody) return;

    if (!data || !data.list || data.list.length === 0) {
        tbody.innerHTML = '<tr><td colspan="12"><div class="empty-state"><div class="emoji">📭</div><div class="text">暂无数据</div></div></td></tr>';
        return;
    }

    tbody.innerHTML = data.list.map(s => {
        const colorCls = getChangeClass(s.change_pct);
        const sign = getChangeSign(s.change_pct);
        return `
            <tr onclick="goToStock('${s.code}')">
                <td>
                    <div class="stock-code-cell">
                        <span class="stock-name">${s.name}</span>
                        <span class="code">${s.code}</span>
                    </div>
                </td>
                <td class="${colorCls}" style="font-weight:700;font-size:14px;">${formatNumber(s.price)}</td>
                <td><span class="change-badge ${getBgClass(s.change_pct)}">${sign}${formatNumber(s.change_pct)}%</span></td>
                <td class="${colorCls}">${sign}${formatNumber(s.change)}</td>
                <td>${formatVolume(s.volume)}</td>
                <td>${formatBigNumber(s.amount)}</td>
                <td>${formatNumber(s.amplitude)}%</td>
                <td>${formatNumber(s.turnover)}%</td>
                <td>${s.pe ? formatNumber(s.pe) : '--'}</td>
                <td class="text-up">${formatNumber(s.high)}</td>
                <td class="text-down">${formatNumber(s.low)}</td>
                <td>
                    <button class="btn btn-sm btn-outline" onclick="event.stopPropagation();quickAddWatch('${s.code}','${s.name}')">⭐自选</button>
                </td>
            </tr>
        `;
    }).join('');

    // 渲染分页
    renderPagination(data.total, data.page, data.page_size);
}

/**
 * 渲染分页控件
 */
function renderPagination(total, page, pageSize) {
    const el = document.getElementById('pagination');
    if (!el) return;

    const totalPages = Math.ceil(total / pageSize);
    if (totalPages <= 1) {
        el.innerHTML = '';
        return;
    }

    let html = '';
    // 上一页
    html += `<button class="page-btn" ${page <= 1 ? 'disabled' : ''} onclick="loadStocks(null,null,${page - 1})">‹</button>`;

    // 页码
    const start = Math.max(1, page - 2);
    const end = Math.min(totalPages, page + 2);
    for (let i = start; i <= end; i++) {
        html += `<button class="page-btn ${i === page ? 'active' : ''}" onclick="loadStocks(null,null,${i})">${i}</button>`;
    }

    // 下一页
    html += `<button class="page-btn" ${page >= totalPages ? 'disabled' : ''} onclick="loadStocks(null,null,${page + 1})">›</button>`;
    el.innerHTML = html;
}

/**
 * 快速添加自选
 */
async function quickAddWatch(code, name) {
    await apiPost('/api/watchlist', { stock_code: code, stock_name: name });
}

/**
 * 启动自动刷新（大盘每 3 秒，列表每 30 秒，新闻每 30 秒）
 */
function startAutoRefresh() {
    updateRefreshBadge();
    if (refreshTimer) clearInterval(refreshTimer);
    let tick = 0;
    refreshTimer = setInterval(() => {
        tick++;
        loadIndices();
        updateRefreshBadge();
        if (tick % 10 === 0) {  // 每30秒
            loadStocks(null, null, null);
            loadNews();
        }
    }, 3000);
}

/**
 * 更新页面刷新时间徽章
 */
function updateRefreshBadge() {
    const badge = document.getElementById('refreshBadge');
    if (!badge) return;
    lastUpdateTime = new Date();
    const h = String(lastUpdateTime.getHours()).padStart(2, '0');
    const m = String(lastUpdateTime.getMinutes()).padStart(2, '0');
    const s = String(lastUpdateTime.getSeconds()).padStart(2, '0');
    badge.textContent = `更新于 ${h}:${m}:${s}`;
    badge.style.opacity = '1';
    setTimeout(() => { badge.style.opacity = '0.6'; }, 1500);
}
