# 多巴胺行情终端 - 投资分析应用

> 基于 Python Flask + SQLite + ECharts 的多巴胺风格投资分析 Web 应用
> 对标东方财富 PC 端核心功能，高饱和渐变配色，开箱即用

## 功能概览

| 页面 | 功能说明 |
|------|---------|
| 行情首页 | 大盘指数实时行情、A股排行榜（涨跌幅/成交额/市值/换手率排序）、分页浏览 |
| 个股K线 | 实时行情详情、交互式K线图（日/周/月/15分/60分）、均线MA5/10/20/60、成交量副图 |
| 自选股 | 添加/删除自选、实时行情推送、期间涨幅计算 |
| 持仓交易 | 模拟买卖交易、账户总资产/可用资金/持仓盈亏、交易记录查询 |
| 龙虎榜 | 龙虎榜上榜股票、净买入额排名、上榜原因 |
| 设置 | 4套主题切换、暗色模式、刷新间隔配置、均线周期配置 |

## 快速启动

```bash
# 1. 进入项目目录
cd investment_app

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动应用
python app.py

# 4. 打开浏览器访问
# http://127.0.0.1:5000
```

> SQLite 数据库会在首次启动时自动创建，无需额外配置

## 使用 MySQL（可选）

如需使用 Navicat 管理 MySQL 数据库：

1. 在 Navicat 中连接 MySQL
2. 执行 `database/schema_mysql.sql` 建表脚本
3. 修改 `config.py` 中的 MySQL 连接信息
4. 修改 `db_helper.py` 切换为 MySQL 连接

## 技术栈

- **后端**: Python 3.13 + Flask 3.1
- **数据库**: SQLite（默认）/ MySQL（可选）
- **前端**: HTML5 + CSS3 + JavaScript (ES6+)
- **图表**: Apache ECharts 5.5
- **数据源**: 东方财富网免费行情 API

## 项目结构

```
investment_app/
├── app.py                 # Flask 主程序（路由 + API）
├── config.py              # 全局配置
├── db_helper.py           # SQLite 数据库工具
├── data_fetcher.py        # 东方财富行情数据获取
├── requirements.txt       # 依赖清单
├── database/
│   ├── investment.db      # SQLite 数据库（自动生成）
│   └── schema_mysql.sql   # MySQL 建表脚本
├── static/
│   ├── css/style.css      # 多巴胺风格样式表
│   └── js/
│       ├── app.js         # 公共工具函数
│       ├── market.js      # 行情首页
│       ├── stock_detail.js # 个股K线
│       ├── watchlist.js   # 自选股
│       ├── portfolio.js   # 持仓交易
│       ├── dragon_tiger.js # 龙虎榜
│       └── settings.js    # 设置
└── templates/
    ├── base.html          # 基础模板（导航栏）
    ├── index.html         # 行情首页
    ├── stock.html         # 个股详情
    ├── watchlist.html     # 自选股
    ├── portfolio.html     # 持仓交易
    ├── dragon_tiger.html  # 龙虎榜
    └── settings.html      # 设置
```

## 配色规范（中国股市）

- **上涨**: 红色渐变 `#e74c3c → #ee5a6f`
- **下跌**: 青绿色渐变 `#00b894 → #3bb4a0`
- **主色**: 紫蓝渐变 `#667eea → #764ba2`

## 风险提醒

- 本应用仅用于学习和模拟，不构成任何投资建议
- 模拟交易资金为虚拟资金，与真实交易无关
- 行情数据来自公开免费接口，可能存在延迟
