/**
 * 文件名: settings.js
 * 功能说明: 设置页面逻辑 - 主题切换 / 暗色模式 / 刷新间隔 / 账户重置
 */

document.addEventListener('DOMContentLoaded', function() {
    loadSettings();
});

/**
 * 加载当前配置
 */
async function loadSettings() {
    const data = await apiGet('/api/settings');
    if (!data) return;

    // 设置刷新间隔下拉
    if (data.refresh_interval) {
        const sel = document.getElementById('refreshIntervalSelect');
        if (sel) sel.value = data.refresh_interval;
    }

    // 设置均线周期
    if (data.ma_periods) {
        const inp = document.getElementById('maPeriodsInput');
        if (inp) inp.value = data.ma_periods;
    }
}

/**
 * 设置主题色
 */
function setTheme(theme, el) {
    // 更新选项卡状态
    document.querySelectorAll('.theme-option').forEach(o => o.classList.remove('active'));
    el.classList.add('active');

    if (theme === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
        const sw = document.getElementById('darkModeSwitch');
        if (sw) sw.classList.add('on');
    } else {
        document.documentElement.removeAttribute('data-theme');
        const sw = document.getElementById('darkModeSwitch');
        if (sw) sw.classList.remove('on');

        // 根据主题调整主色
        const root = document.documentElement;
        if (theme === 'warm') {
            root.style.setProperty('--grad-primary', 'linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%)');
        } else if (theme === 'cool') {
            root.style.setProperty('--grad-primary', 'linear-gradient(135deg, #00d2d3 0%, #3bb4a0 100%)');
        } else {
            root.style.setProperty('--grad-primary', 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)');
        }
    }

    apiPut('/api/settings', { theme: theme });
    showToast(`主题已切换为 ${theme}`, 'success');
}

/**
 * 切换暗色模式
 */
function toggleDarkMode() {
    const sw = document.getElementById('darkModeSwitch');
    if (sw.classList.contains('on')) {
        sw.classList.remove('on');
        document.documentElement.removeAttribute('data-theme');
        showToast('已关闭暗色模式', 'info');
    } else {
        sw.classList.add('on');
        document.documentElement.setAttribute('data-theme', 'dark');
        showToast('已开启暗色模式', 'info');
    }
}

/**
 * 切换自动刷新
 */
function toggleAutoRefresh() {
    const sw = document.getElementById('autoRefreshSwitch');
    if (sw.classList.contains('on')) {
        sw.classList.remove('on');
        showToast('已关闭自动刷新', 'info');
    } else {
        sw.classList.add('on');
        showToast('已开启自动刷新', 'info');
    }
}

/**
 * 更新刷新间隔
 */
function updateRefreshInterval() {
    const sel = document.getElementById('refreshIntervalSelect');
    if (sel) {
        apiPut('/api/settings', { refresh_interval: sel.value });
        showToast(`刷新间隔已设为 ${sel.value} 秒`, 'success');
    }
}

/**
 * 更新均线设置
 */
function updateMASettings() {
    const inp = document.getElementById('maPeriodsInput');
    if (inp) {
        apiPut('/api/settings', { ma_periods: inp.value });
        showToast('均线设置已保存', 'success');
    }
}

/**
 * 重置模拟账户
 */
async function resetAccount() {
    if (!confirm('⚠️ 确定要重置模拟账户吗？\n\n这将清空所有持仓和交易记录，资金恢复为 100 万。\n此操作不可撤销！')) {
        return;
    }
    if (!confirm('再次确认：真的要重置吗？所有交易数据将丢失！')) {
        return;
    }
    // 通过特殊接口重置（这里简化处理，清空表数据）
    // 实际项目中应添加后端重置接口
    showToast('账户重置功能开发中，请手动删除 database/investment.db 后重启', 'info');
}
