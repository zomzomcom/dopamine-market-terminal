/**
 * 文件名: stock_detail.js
 * 功能说明: 个股详情页逻辑 - 实时行情 + K线图 + 技术指标
 */

let klineChart = null;
let volumeChart = null;
let currentKlt = 101;
let showMA = true;
let showVolume = true;
let stockRefreshTimer = null;

// ECharts 多巴胺配色
const CHART_COLORS = {
    up: '#e74c3c',
    down: '#00b894',
    ma5: '#f093fb',
    ma10: '#4facfe',
    ma20: '#fa709a',
    ma60: '#fee140',
    text: '#6c7293',
    grid: 'rgba(102, 126, 234, 0.08)',
};

// 页面初始化
document.addEventListener('DOMContentLoaded', function() {
    loadStockDetail();
    loadKline();
    // 定时刷新实时行情
    stockRefreshTimer = setInterval(loadStockDetail, 5000);
});

/**
 * 加载个股实时详情
 */
async function loadStockDetail() {
    const data = await apiGet(`/api/stock/${STOCK_CODE}`);
    if (!data) return;

    // 更新名称
    document.getElementById('stockName').textContent = data.name || STOCK_CODE;

    // 更新价格
    const priceEl = document.getElementById('stockPrice');
    priceEl.textContent = formatNumber(data.price);
    priceEl.className = 'stock-price-big ' + getChangeClass(data.change_pct);

    // 更新涨跌信息
    const changeEl = document.getElementById('stockChange');
    const sign = getChangeSign(data.change_pct);
    changeEl.innerHTML = `
        <span class="${getChangeClass(data.change_pct)}">${sign}${formatNumber(data.change)}</span>
        <span class="change-badge ${getBgClass(data.change_pct)}">${sign}${formatNumber(data.change_pct)}%</span>
    `;

    // 更新数据网格
    document.getElementById('dOpen').textContent = formatNumber(data.open);
    document.getElementById('dHigh').textContent = formatNumber(data.high);
    document.getElementById('dLow').textContent = formatNumber(data.low);
    document.getElementById('dPrevClose').textContent = formatNumber(data.prev_close);
    document.getElementById('dVolume').textContent = formatVolume(data.volume);
    document.getElementById('dAmount').textContent = formatBigNumber(data.amount);
    document.getElementById('dMarketCap').textContent = formatBigNumber(data.market_cap);
    document.getElementById('dFloatCap').textContent = formatBigNumber(data.float_cap);
    document.getElementById('dPe').textContent = data.pe ? formatNumber(data.pe) : '--';
    document.getElementById('dPb').textContent = data.pb ? formatNumber(data.pb) : '--';
}

/**
 * 加载 K 线数据并渲染图表
 */
async function loadKline() {
    const data = await apiGet(`/api/stock/${STOCK_CODE}/kline`, { klt: currentKlt, count: 120 });
    if (!data || data.length === 0) {
        showToast('暂无K线数据', 'info');
        return;
    }
    renderKlineChart(data);
}

/**
 * 切换 K 线类型
 */
function switchKline(klt) {
    currentKlt = klt;
    // 更新选项卡状态
    document.querySelectorAll('.chart-tab').forEach(tab => tab.classList.remove('active'));
    document.querySelector(`.chart-tab[data-klt="${klt}"]`).classList.add('active');
    loadKline();
}

/**
 * 计算移动平均线
 * @param {Array} data - K线数据
 * @param {number} period - 周期
 * @returns {Array} MA 数据
 */
function calcMA(data, period) {
    const result = [];
    for (let i = 0; i < data.length; i++) {
        if (i < period - 1) {
            result.push(null);
        } else {
            let sum = 0;
            for (let j = i - period + 1; j <= i; j++) {
                sum += data[j].close;
            }
            result.push((sum / period).toFixed(2));
        }
    }
    return result;
}

/**
 * 渲染 K 线图
 */
function renderKlineChart(data) {
    const chartDom = document.getElementById('klineChart');
    if (!chartDom) return;

    if (!klineChart) {
        klineChart = echarts.init(chartDom);
    }

    // 准备数据
    const dates = data.map(d => d.date);
    const ohlc = data.map(d => [d.open, d.close, d.low, d.high]);
    const volumes = data.map(d => ({
        value: d.volume,
        itemStyle: { color: d.close >= d.open ? CHART_COLORS.up : CHART_COLORS.down },
    }));

    // 计算均线
    const ma5 = calcMA(data, 5);
    const ma10 = calcMA(data, 10);
    const ma20 = calcMA(data, 20);
    const ma60 = calcMA(data, 60);

    const series = [
        {
            name: 'K线',
            type: 'candlestick',
            data: ohlc,
            itemStyle: {
                color: CHART_COLORS.up,        // 阳线颜色（上涨红）
                color0: CHART_COLORS.down,     // 阴线颜色（下跌绿）
                borderColor: CHART_COLORS.up,
                borderColor0: CHART_COLORS.down,
            },
        },
    ];

    // 添加均线
    if (showMA) {
        const maConfigs = [
            { name: 'MA5', data: ma5, color: CHART_COLORS.ma5 },
            { name: 'MA10', data: ma10, color: CHART_COLORS.ma10 },
            { name: 'MA20', data: ma20, color: CHART_COLORS.ma20 },
            { name: 'MA60', data: ma60, color: CHART_COLORS.ma60 },
        ];
        maConfigs.forEach(ma => {
            series.push({
                name: ma.name,
                type: 'line',
                data: ma.data,
                smooth: true,
                symbol: 'none',
                lineStyle: { width: 1.5, color: ma.color },
            });
        });
    }

    const option = {
        backgroundColor: 'transparent',
        animation: true,
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'cross' },
            backgroundColor: 'rgba(255,255,255,0.95)',
            borderColor: 'rgba(102,126,234,0.3)',
            textStyle: { color: '#1a1a2e', fontSize: 12 },
            formatter: function(params) {
                let html = `<div style="font-weight:700;margin-bottom:4px;">${params[0].axisValue}</div>`;
                params.forEach(p => {
                    if (p.seriesName === 'K线') {
                        const d = data[p.dataIndex];
                        html += `<div style="color:${p.color}">开 ${formatNumber(d.open)} 收 ${formatNumber(d.close)}</div>`;
                        html += `<div style="color:${p.color}">高 ${formatNumber(d.high)} 低 ${formatNumber(d.low)}</div>`;
                        html += `<div style="color:${p.color}">量 ${formatVolume(d.volume)}</div>`;
                    } else {
                        html += `<div style="color:${p.color}">${p.seriesName} ${p.value || '--'}</div>`;
                    }
                });
                return html;
            },
        },
        legend: {
            data: showMA ? ['K线', 'MA5', 'MA10', 'MA20', 'MA60'] : ['K线'],
            top: 8,
            textStyle: { color: CHART_COLORS.text, fontSize: 11 },
        },
        grid: {
            left: '3%',
            right: '3%',
            bottom: showVolume ? '35%' : '8%',
            top: '12%',
            containLabel: true,
        },
        xAxis: {
            type: 'category',
            data: dates,
            boundaryGap: false,
            axisLine: { lineStyle: { color: CHART_COLORS.grid } },
            axisLabel: { color: CHART_COLORS.text, fontSize: 10 },
            splitLine: { show: false },
        },
        yAxis: {
            type: 'value',
            scale: true,
            axisLine: { lineStyle: { color: CHART_COLORS.grid } },
            axisLabel: { color: CHART_COLORS.text, fontSize: 10 },
            splitLine: { lineStyle: { color: CHART_COLORS.grid } },
        },
        dataZoom: [
            {
                type: 'inside',
                start: 60,
                end: 100,
            },
            {
                show: true,
                type: 'slider',
                bottom: showVolume ? '20%' : '2%',
                start: 60,
                end: 100,
                height: 20,
                borderColor: 'transparent',
                fillerColor: 'rgba(102,126,234,0.15)',
                handleStyle: { color: '#667eea' },
            },
        ],
        series: series,
    };

    klineChart.setOption(option, true);

    // 成交量图
    if (showVolume) {
        renderVolumeChart(dates, volumes);
    } else {
        const volDom = document.getElementById('volumeChart');
        if (volDom) volDom.style.display = 'none';
    }
}

/**
 * 渲染成交量图
 */
function renderVolumeChart(dates, volumes) {
    const volDom = document.getElementById('volumeChart');
    if (!volDom) return;
    volDom.style.display = 'block';

    if (!volumeChart) {
        volumeChart = echarts.init(volDom);
    }

    volumeChart.setOption({
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'axis',
            backgroundColor: 'rgba(255,255,255,0.95)',
            textStyle: { color: '#1a1a2e', fontSize: 12 },
            formatter: function(params) {
                return `<div style="font-weight:700;">${params[0].axisValue}</div>
                        <div>成交量: ${formatVolume(params[0].data.value * 100)}</div>`;
            },
        },
        grid: { left: '3%', right: '3%', top: '5%', bottom: '8%', containLabel: true },
        xAxis: {
            type: 'category',
            data: dates,
            axisLabel: { show: false },
            axisLine: { lineStyle: { color: CHART_COLORS.grid } },
        },
        yAxis: {
            type: 'value',
            axisLabel: { color: CHART_COLORS.text, fontSize: 10,
                formatter: function(val) { return formatBigNumber(val * 100); }
            },
            splitLine: { lineStyle: { color: CHART_COLORS.grid } },
        },
        series: [{
            type: 'bar',
            data: volumes,
            barWidth: '60%',
        }],
    }, true);
}

/**
 * 切换均线显示
 */
function toggleMA() {
    showMA = document.getElementById('showMA').checked;
    loadKline();
}

/**
 * 切换成交量显示
 */
function toggleVolume() {
    showVolume = document.getElementById('showVol').checked;
    loadKline();
}

// 窗口大小变化时重绘图表
window.addEventListener('resize', function() {
    if (klineChart) klineChart.resize();
    if (volumeChart) volumeChart.resize();
});
