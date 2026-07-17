/**
 * 文件名: portfolio.js
 * 功能说明: 模拟交易页面逻辑
 *          5个 Tab: 买入 / 卖出 / 撤单 / 持仓 / 交易记录
 */

let portfolioTimer = null;
let currentTab = 'buy';

document.addEventListener('DOMContentLoaded', function() {
    loadAccount();
    loadPortfolio();
    loadTransactions();
    portfolioTimer = setInterval(() => {
        loadAccount();
        loadPortfolio();
    }, 10000);
});

/**
 * 切换模拟交易 Tab
 */
function switchTradeTab(tab) {
    currentTab = tab;
    // 更新 tab 按钮状态
    document.querySelectorAll('.trade-tab').forEach(t => t.classList.remove('active'));
    document.querySelector(`.trade-tab[data-tab="${tab}"]`).classList.add('active');
    // 更新面板状态
    document.querySelectorAll('.trade-pane').forEach(p => p.classList.remove('active'));
    document.getElementById(`pane-${tab}`).classList.add('active');
    // 切换到对应 tab 时刷新数据
    if (tab === 'hold') loadPortfolio();
    if (tab === 'record') loadTransactions();
}

/**
 * 加载账户概览
 */
async function loadAccount() {
    const data = await apiGet('/api/account');
    const el = document.getElementById('accountOverview');
    if (!el || !data) return;

    const profitCls = getChangeClass(data.total_profit);
    const profitSign = getChangeSign(data.total_profit);

    el.innerHTML = `
        <div class="account-card">
            <div class="ac-icon" style="background:rgba(102,126,234,0.12);">💰</div>
            <div class="ac-label">总资产</div>
            <div class="ac-value">¥${formatNumber(data.total_assets)}</div>
        </div>
        <div class="account-card">
            <div class="ac-icon" style="background:rgba(0,184,148,0.12);">💵</div>
            <div class="ac-label">可用资金</div>
            <div class="ac-value">¥${formatNumber(data.balance)}</div>
        </div>
        <div class="account-card">
            <div class="ac-icon" style="background:rgba(255,107,107,0.12);">📈</div>
            <div class="ac-label">持仓市值</div>
            <div class="ac-value">¥${formatNumber(data.total_market_value)}</div>
        </div>
        <div class="account-card">
            <div class="ac-icon" style="background:rgba(168,85,247,0.12);">📊</div>
            <div class="ac-label">总盈亏</div>
            <div class="ac-value ${profitCls}">${profitSign}¥${formatNumber(Math.abs(data.total_profit))}</div>
            <div style="margin-top:4px;">
                <span class="change-badge ${getBgClass(data.total_profit)}">${profitSign}${formatNumber(data.total_profit_pct)}%</span>
            </div>
        </div>
    `;
}

/**
 * 加载持仓列表
 */
async function loadPortfolio() {
    const data = await apiGet('/api/portfolio');
    const tbody = document.getElementById('portfolioBody');
    if (!tbody) return;

    if (!data || data.length === 0) {
        tbody.innerHTML = `
            <tr><td colspan="8">
                <div class="empty-state">
                    <div class="emoji">💼</div>
                    <div class="text">暂无持仓，去买入第一只股票吧！</div>
                </div>
            </td></tr>`;
        return;
    }

    tbody.innerHTML = data.map(p => {
        const profitCls = getChangeClass(p.profit);
        const profitSign = getChangeSign(p.profit);
        const todayCls = getChangeClass(p.change_pct);
        return `
            <tr onclick="goToStock('${p.stock_code}')">
                <td>
                    <div class="stock-code-cell">
                        <span class="stock-name">${p.name || p.stock_name}</span>
                        <span class="code">${p.stock_code}</span>
                    </div>
                </td>
                <td style="font-weight:600;">${p.quantity}股</td>
                <td>¥${formatNumber(p.avg_cost)}</td>
                <td class="${todayCls}" style="font-weight:700;">¥${formatNumber(p.current_price)}</td>
                <td>¥${formatNumber(p.market_value)}</td>
                <td class="${profitCls}" style="font-weight:700;">${profitSign}¥${formatNumber(Math.abs(p.profit))}</td>
                <td><span class="change-badge ${getBgClass(p.profit)}">${profitSign}${formatNumber(p.profit_pct)}%</span></td>
                <td class="${todayCls}">${getChangeSign(p.change_pct)}${formatNumber(p.change_pct)}%</td>
            </tr>
        `;
    }).join('');
}

/**
 * 加载交易记录
 */
async function loadTransactions() {
    const data = await apiGet('/api/transactions', { page: 1, page_size: 20 });
    const tbody = document.getElementById('transactionsBody');
    if (!tbody) return;

    if (!data || !data.list || data.list.length === 0) {
        tbody.innerHTML = `
            <tr><td colspan="7">
                <div class="empty-state">
                    <div class="emoji">📋</div>
                    <div class="text">暂无交易记录</div>
                </div>
            </td></tr>`;
        return;
    }

    tbody.innerHTML = data.list.map(t => {
        const isBuy = t.trade_type === 'buy';
        return `
            <tr>
                <td style="color:var(--text-muted);font-size:12px;">${t.created_at}</td>
                <td>
                    <div class="stock-code-cell">
                        <span class="stock-name">${t.stock_name}</span>
                        <span class="code">${t.stock_code}</span>
                    </div>
                </td>
                <td><span class="tag ${isBuy ? 'tag-red' : 'tag-green'}">${isBuy ? '买入' : '卖出'}</span></td>
                <td>${t.quantity}股</td>
                <td style="font-weight:600;">¥${formatNumber(t.price)}</td>
                <td>¥${formatNumber(t.total_amount)}</td>
                <td style="color:var(--text-muted);">¥${formatNumber(t.fee)}</td>
            </tr>
        `;
    }).join('');
}

/**
 * 执行交易
 */
async function doTrade(type) {
    const prefix = type === 'buy' ? 'buy' : 'sell';
    const code = document.getElementById(`${prefix}Code`).value.trim();
    const name = document.getElementById(`${prefix}Name`).value.trim();
    const price = parseFloat(document.getElementById(`${prefix}Price`).value);
    const qty = parseInt(document.getElementById(`${prefix}Qty`).value);

    if (!code) { showToast('请输入股票代码', 'error'); return; }
    if (!price || price <= 0) { showToast('请输入有效价格', 'error'); return; }
    if (!qty || qty <= 0) { showToast('请输入有效数量', 'error'); return; }

    // 如果没有名称，尝试自动获取
    let stockName = name;
    if (!stockName) {
        const detail = await apiGet(`/api/stock/${code}`);
        stockName = detail ? detail.name : code;
    }

    const result = await apiPost('/api/trade', {
        stock_code: code,
        stock_name: stockName,
        trade_type: type,
        quantity: qty,
        price: price,
    });

    if (result !== null) {
        // 清空表单
        document.getElementById(`${prefix}Code`).value = '';
        document.getElementById(`${prefix}Name`).value = '';
        document.getElementById(`${prefix}Price`).value = '';
        document.getElementById(`${prefix}Qty`).value = '100';
        // 刷新数据
        loadAccount();
        loadPortfolio();
        loadTransactions();
    }
}
