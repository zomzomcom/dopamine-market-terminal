/**
 * 文件名: watchlist.js
 * 功能说明: 自选股页面逻辑 - 增删改查 + 实时行情
 */

let watchlistTimer = null;

document.addEventListener('DOMContentLoaded', function() {
    loadWatchlist();
    watchlistTimer = setInterval(loadWatchlist, 10000); // 10秒刷新
});

/**
 * 加载自选股列表
 */
async function loadWatchlist() {
    const data = await apiGet('/api/watchlist');
    const tbody = document.getElementById('watchlistBody');
    if (!tbody) return;

    if (!data || data.length === 0) {
        tbody.innerHTML = `
            <tr><td colspan="8">
                <div class="empty-state">
                    <div class="emoji">⭐</div>
                    <div class="text">还没有自选股，快去添加吧！</div>
                </div>
            </td></tr>`;
        return;
    }

    tbody.innerHTML = data.map(s => {
        const colorCls = getChangeClass(s.change_pct);
        const sign = getChangeSign(s.change_pct);
        // 计算期间涨幅（从加入价到现价）
        let periodPct = 0;
        if (s.add_price && s.add_price > 0 && s.current_price) {
            periodPct = ((s.current_price - s.add_price) / s.add_price * 100);
        }
        const periodCls = getChangeClass(periodPct);
        return `
            <tr onclick="goToStock('${s.stock_code}')">
                <td>
                    <div class="stock-code-cell">
                        <span class="stock-name">${s.stock_name}</span>
                        <span class="code">${s.stock_code}</span>
                    </div>
                </td>
                <td class="${colorCls}" style="font-weight:700;">${formatNumber(s.current_price)}</td>
                <td><span class="change-badge ${getBgClass(s.change_pct)}">${sign}${formatNumber(s.change_pct)}%</span></td>
                <td class="${colorCls}">${sign}${formatNumber(s.change)}</td>
                <td>${formatNumber(s.add_price)}</td>
                <td class="${periodCls}" style="font-weight:600;">${getChangeSign(periodPct)}${formatNumber(periodPct)}%</td>
                <td style="color:var(--text-muted);">${s.note || '--'}</td>
                <td>
                    <button class="btn btn-sm btn-outline" style="color:var(--color-down);border-color:rgba(0,184,148,0.3);"
                        onclick="event.stopPropagation();removeWatch(${s.id})">删除</button>
                </td>
            </tr>
        `;
    }).join('');
}

/**
 * 添加自选股
 */
async function addStock() {
    const code = document.getElementById('addStockCode').value.trim();
    if (!code) {
        showToast('请输入股票代码', 'error');
        return;
    }
    const result = await apiPost('/api/watchlist', { stock_code: code });
    if (result !== null) {
        document.getElementById('addStockCode').value = '';
        loadWatchlist();
    }
}

/**
 * 删除自选股
 */
async function removeWatch(id) {
    if (!confirm('确定要删除该自选股吗？')) return;
    await apiDelete(`/api/watchlist/${id}`);
    loadWatchlist();
}
