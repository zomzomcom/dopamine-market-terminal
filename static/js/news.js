/**
 * 文件名: news.js
 * 功能说明: 热点资讯独立页面 - 实时财经新闻列表 + 自动刷新 + 筛选
 */

let newsAllData = [];
let newsCurrentFilter = 'all';
let newsRefreshTimer = null;
const NEWS_PAGE_SIZE = 20;
const NEWS_AUTO_REFRESH_INTERVAL = 30000; // 30秒自动刷新

document.addEventListener('DOMContentLoaded', function() {
    loadNewsPage();
    setupFilterButtons();
    startNewsAutoRefresh();
});

/**
 * 加载新闻页面数据
 */
async function loadNewsPage() {
    try {
        const resp = await fetch('/api/news?count=50');
        const json = await resp.json();

        // 更新市场状态
        const statusEl = document.getElementById('marketStatus');
        if (statusEl && json.market_open !== undefined) {
            statusEl.textContent = json.market_open ? '🟢 交易中' : '🔴 已收盘';
            statusEl.className = 'market-status ' + (json.market_open ? 'open' : 'closed');
        }

        newsAllData = json.data || [];
        renderFilteredNews();

        // 更新刷新时间
        const badge = document.getElementById('newsRefreshBadge');
        if (badge) {
            const now = new Date();
            const ts = String(now.getHours()).padStart(2,'0') + ':' +
                       String(now.getMinutes()).padStart(2,'0') + ':' +
                       String(now.getSeconds()).padStart(2,'0');
            badge.textContent = '更新于 ' + ts;
            badge.style.opacity = '1';
            setTimeout(() => { badge.style.opacity = '0.6'; }, 1500);
        }
    } catch (e) {
        document.getElementById('newsPageList').innerHTML =
            '<div class="empty-state"><div class="emoji">📡</div><div class="text">热点资讯加载失败<br><small style="color:var(--text-muted);">请检查网络连接后刷新页面</small></div></div>';
    }
}

/**
 * 关键词匹配筛选
 */
function matchFilter(title, intro, filter) {
    const text = (title + ' ' + (intro || '')).toLowerCase();

    const keywords = {
        'policy': ['政策', '央行', '证监会', '国务院', '发改委', '财政部', '银保监', '政治局', '法规', '监管', '改革', '降准', '降息', '利率', 'LPR', 'MLF'],
        'market': ['股市', 'A股', '大盘', '指数', '涨停', '跌停', '牛市', '熊市', '反弹', '回调', '震荡', '成交', '资金', '北向', '南向', 'ETF', '板块', '概念'],
        'company': ['公司', '股份', '业绩', '财报', '营收', '利润', '分红', '回购', '减持', '增持', 'IPO', '上市', '退市', 'ST', '重组', '并购'],
        'global': ['美股', '港股', '美联储', '欧洲', '日本', '全球', '国际', '贸易', '关税', '美元', '人民币', '汇率', '原油', '黄金', '大宗'],
    };

    const kws = keywords[filter];
    if (!kws) return true;

    return kws.some(kw => text.includes(kw));
}

/**
 * 渲染筛选后的新闻
 */
function renderFilteredNews() {
    const list = document.getElementById('newsPageList');
    const loadMore = document.getElementById('newsLoadMore');

    if (!newsAllData || newsAllData.length === 0) {
        list.innerHTML = '<div class="empty-state"><div class="emoji">📭</div><div class="text">暂无热点资讯<br><small style="color:var(--text-muted);">数据源可能暂时不可用，请稍后刷新</small></div></div>';
        loadMore.style.display = 'none';
        return;
    }

    // 筛选
    let filtered = newsAllData;
    if (newsCurrentFilter !== 'all') {
        filtered = newsAllData.filter(item =>
            matchFilter(item.title, item.intro, newsCurrentFilter)
        );
    }

    if (filtered.length === 0) {
        list.innerHTML = '<div class="empty-state"><div class="emoji">🔍</div><div class="text">该分类下暂无相关资讯</div></div>';
        loadMore.style.display = 'none';
        return;
    }

    // 只显示前 NEWS_PAGE_SIZE 条
    const displayItems = filtered.slice(0, NEWS_PAGE_SIZE);
    const hasMore = filtered.length > NEWS_PAGE_SIZE;

    list.innerHTML = displayItems.map((n, i) => `
        <a class="news-card-item" href="${n.url || '#'}" target="_blank" rel="noopener">
            <div class="news-card-left">
                <span class="news-card-index">${String(i + 1).padStart(2, '0')}</span>
            </div>
            <div class="news-card-body">
                <div class="news-card-meta">
                    <span class="news-card-source">${n.source || '财经快讯'}</span>
                    <span class="news-card-time">${n.time || ''}</span>
                </div>
                <h3 class="news-card-title">${n.title}</h3>
                ${n.intro ? `<p class="news-card-intro">${n.intro}</p>` : ''}
            </div>
            <div class="news-card-arrow">
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                    <path d="M7.5 15L12.5 10L7.5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
            </div>
        </a>
    `).join('');

    loadMore.style.display = hasMore ? 'block' : 'none';
}

/**
 * 筛选按钮事件
 */
function setupFilterButtons() {
    const buttons = document.querySelectorAll('.news-filter-btn');
    buttons.forEach(btn => {
        btn.addEventListener('click', function() {
            buttons.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            newsCurrentFilter = this.dataset.filter;
            renderFilteredNews();
        });
    });
}

/**
 * 加载更多（增大显示数量）
 */
let newsDisplayCount = NEWS_PAGE_SIZE;
function loadMoreNews() {
    newsDisplayCount += NEWS_PAGE_SIZE;
    const list = document.getElementById('newsPageList');
    const loadMore = document.getElementById('newsLoadMore');

    let filtered = newsAllData;
    if (newsCurrentFilter !== 'all') {
        filtered = newsAllData.filter(item =>
            matchFilter(item.title, item.intro, newsCurrentFilter)
        );
    }

    const displayItems = filtered.slice(0, newsDisplayCount);
    const hasMore = filtered.length > newsDisplayCount;

    list.innerHTML = displayItems.map((n, i) => `
        <a class="news-card-item" href="${n.url || '#'}" target="_blank" rel="noopener">
            <div class="news-card-left">
                <span class="news-card-index">${String(i + 1).padStart(2, '0')}</span>
            </div>
            <div class="news-card-body">
                <div class="news-card-meta">
                    <span class="news-card-source">${n.source || '财经快讯'}</span>
                    <span class="news-card-time">${n.time || ''}</span>
                </div>
                <h3 class="news-card-title">${n.title}</h3>
                ${n.intro ? `<p class="news-card-intro">${n.intro}</p>` : ''}
            </div>
            <div class="news-card-arrow">
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                    <path d="M7.5 15L12.5 10L7.5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
            </div>
        </a>
    `).join('');

    loadMore.style.display = hasMore ? 'block' : 'none';
}

/**
 * 启动自动刷新
 */
function startNewsAutoRefresh() {
    if (newsRefreshTimer) clearInterval(newsRefreshTimer);
    newsRefreshTimer = setInterval(() => {
        loadNewsPage();
    }, NEWS_AUTO_REFRESH_INTERVAL);
}

// 页面卸载时清理定时器
window.addEventListener('beforeunload', function() {
    if (newsRefreshTimer) {
        clearInterval(newsRefreshTimer);
        newsRefreshTimer = null;
    }
});
