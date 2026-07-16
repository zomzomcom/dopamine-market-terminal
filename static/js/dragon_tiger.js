/**
 * 文件名: dragon_tiger.js
 * 功能说明: 龙虎榜页面逻辑
 */

document.addEventListener('DOMContentLoaded', function() {
    loadDragonTiger();
});

/**
 * 加载龙虎榜数据
 */
async function loadDragonTiger() {
    const data = await apiGet('/api/dragon-tiger');
    const el = document.getElementById('dtList');
    if (!el) return;

    if (!data || data.length === 0) {
        el.innerHTML = `
            <div class="empty-state">
                <div class="emoji">🐉</div>
                <div class="text">暂无龙虎榜数据</div>
            </div>`;
        return;
    }

    el.innerHTML = data.map((s, i) => {
        const rank = i + 1;
        const rankCls = rank <= 3 ? `r${rank}` : 'r4';
        const colorCls = getChangeClass(s.change_pct);
        const sign = getChangeSign(s.change_pct);
        const netBuyCls = getChangeClass(s.net_buy);
        const netBuySign = getChangeSign(s.net_buy);
        return `
            <div class="dt-item" onclick="goToStock('${s.code}')">
                <div class="dt-rank ${rankCls}">${rank}</div>
                <div>
                    <div style="font-weight:700;font-size:14px;color:var(--text-primary);">${s.name}</div>
                    <div style="font-size:12px;color:var(--text-muted);">${s.code} · ${s.reason || ''}</div>
                </div>
                <div style="text-align:right;">
                    <div style="font-size:16px;font-weight:700;" class="${colorCls}">¥${formatNumber(s.close)}</div>
                    <div class="${colorCls}" style="font-size:12px;">${sign}${formatNumber(s.change_pct)}%</div>
                </div>
                <div style="text-align:right;">
                    <div style="font-size:12px;color:var(--text-muted);">净买入</div>
                    <div class="${netBuyCls}" style="font-weight:700;font-size:14px;">${netBuySign}${formatBigNumber(Math.abs(s.net_buy))}</div>
                </div>
                <div style="text-align:right;">
                    <div style="font-size:12px;color:var(--text-muted);">买入额</div>
                    <div style="font-weight:600;font-size:13px;">${formatBigNumber(s.buy_amount)}</div>
                </div>
            </div>
        `;
    }).join('');
}
