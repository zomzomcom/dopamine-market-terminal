/**
 * 文件名: dragon_tiger.js
 * 功能说明: 龙虎榜页面逻辑
 *          展示：个股信息、买入游资、席位名称、净流向金额、热点板块
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

        // 游资席位
        const buyers = s.top_buyers || [];
        const buyersHtml = buyers.length
            ? buyers.map(b => `<span class="tag tag-purple" style="margin:2px;">${b}</span>`).join('')
            : '<span style="color:var(--text-muted);font-size:12px;">暂无数据</span>';

        // 热点板块
        const sector = s.hot_sector || '—';

        // 席位数
        const seatCount = s.buy_seat_count || 0;

        return `
            <div class="dt-item" onclick="goToStock('${s.code}')">
                <div class="dt-rank ${rankCls}">${rank}</div>
                <div class="dt-main">
                    <div class="dt-header">
                        <span class="dt-name">${s.name}</span>
                        <span class="dt-code">${s.code}</span>
                        <span class="tag tag-blue" style="margin-left:8px;">${sector}</span>
                    </div>
                    <div class="dt-meta">
                        <span class="dt-meta-item">📊 ${seatCount}个席位</span>
                        <span class="dt-meta-item">💹 ${s.reason || '—'}</span>
                    </div>
                    <div class="dt-buyers">
                        <span class="dt-label">买入游资:</span>
                        ${buyersHtml}
                    </div>
                </div>
                <div class="dt-stats">
                    <div class="dt-stat">
                        <div class="dt-stat-label">收盘价</div>
                        <div class="dt-stat-value ${colorCls}">¥${formatNumber(s.close)}</div>
                    </div>
                    <div class="dt-stat">
                        <div class="dt-stat-label">涨跌幅</div>
                        <div class="dt-stat-value ${colorCls}">${sign}${formatNumber(s.change_pct)}%</div>
                    </div>
                </div>
                <div class="dt-money">
                    <div class="dt-money-item">
                        <span class="dt-money-label">净买入</span>
                        <span class="dt-money-value ${netBuyCls}">${netBuySign}${formatBigNumber(s.net_buy)}</span>
                    </div>
                    <div class="dt-money-item">
                        <span class="dt-money-label">买入额</span>
                        <span class="dt-money-value">${formatBigNumber(s.buy_amount)}</span>
                    </div>
                    <div class="dt-money-item">
                        <span class="dt-money-label">卖出额</span>
                        <span class="dt-money-value">${formatBigNumber(s.sell_amount)}</span>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}
