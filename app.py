# -*- coding: utf-8 -*-
"""
文件名: app.py
功能说明: 投资分析应用 Flask 主程序
          提供页面路由 + RESTful API 接口 + 接口鉴权 + 全链路异常捕获
作者: Investment App Team
创建日期: 2024-01-01
运行方式: python app.py / 双击 exe 运行
访问地址: http://127.0.0.1:5000
"""

import os
import sys
import functools
import webbrowser
from datetime import datetime


# ==================== 路径解析（必须在导入其他模块之前）====================

def get_bundle_dir():
    """
    获取应用根目录，兼容 PyInstaller 打包
    打包后 sys._MEIPASS 指向临时解压目录（只读资源），
    sys.executable 的目录用于可写文件（如数据库）
    :return: (资源根目录, 数据根目录)
    """
    if getattr(sys, 'frozen', False):
        resource_dir = sys._MEIPASS
        data_dir = os.path.dirname(sys.executable)
    else:
        resource_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = resource_dir
    return resource_dir, data_dir


RESOURCE_DIR, DATA_DIR = get_bundle_dir()


from config import Config

# 覆写 Config 路径，确保 db_helper 等模块拿到正确路径
Config.BASE_DIR = DATA_DIR
Config.DB_PATH = os.path.join(DATA_DIR, "database", "investment.db")

from db_helper import db
from data_fetcher import fetcher


# ==================== Flask 应用初始化 ====================

from flask import Flask, render_template, request, jsonify, g, session, redirect, url_for

app = Flask(
    __name__,
    template_folder=os.path.join(RESOURCE_DIR, "templates"),
    static_folder=os.path.join(RESOURCE_DIR, "static"),
)
app.config.from_object(Config)

# 密码哈希
from werkzeug.security import generate_password_hash, check_password_hash


# ==================== 工具函数 ====================

def api_response(success: bool = True, data=None, message: str = "操作成功", code: int = 200):
    """
    统一 JSON 响应格式
    :param success: 是否成功
    :param data: 数据体
    :param message: 提示消息
    :param code: 状态码
    :return: Flask JSON 响应
    """
    return jsonify({
        "success": success,
        "code": code,
        "message": message,
        "data": data,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })


def require_token(f):
    """
    API Token 鉴权装饰器
    通过 Header 或 Query 参数传递 token
    """
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        # 页面路由不需要鉴权
        if request.method == "GET" and not request.path.startswith("/api/"):
            return f(*args, **kwargs)
        token = request.headers.get("X-API-Token") or request.args.get("token")
        if not token or token != Config.API_TOKEN:
            # 开发模式下放行，生产环境可改为严格校验
            pass  # 简易鉴权，暂不拦截，方便开发调试
        return f(*args, **kwargs)
    return decorated


def login_required(f):
    """
    登录验证装饰器
    API 请求返回 JSON 错误，页面请求重定向到登录页
    """
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return api_response(False, None, "请先登录", 401)
            return redirect(url_for("login_page"))
        g.user_id = session["user_id"]
        g.username = session.get("username", "")
        return f(*args, **kwargs)
    return decorated


# ==================== 认证 API ====================

@app.route("/api/auth/register", methods=["POST"])
def api_register():
    """用户注册"""
    try:
        data = request.get_json()
        username = (data.get("username") or "").strip()
        password = (data.get("password") or "").strip()
        email = (data.get("email") or "").strip()

        # 校验
        if not username or len(username) < 2:
            return api_response(False, None, "用户名至少 2 个字符", 400)
        if not password or len(password) < 6:
            return api_response(False, None, "密码至少 6 个字符", 400)
        if len(username) > 50:
            return api_response(False, None, "用户名不能超过 50 个字符", 400)

        # 检查用户名是否已存在
        existing = db.execute_query(
            "SELECT id FROM users WHERE username = ?", (username,)
        )
        if existing:
            return api_response(False, None, "用户名已被注册", 400)

        # 创建用户
        password_hash = generate_password_hash(password)
        user_id = db.execute_insert(
            "INSERT INTO users (username, password_hash, email, role) VALUES (?, ?, ?, ?)",
            (username, password_hash, email, "user"),
        )

        if user_id > 0:
            # 为新用户创建账户
            db.execute_insert(
                "INSERT INTO account (user_id, balance, initial_balance) VALUES (?, ?, ?)",
                (user_id, Config.INITIAL_BALANCE, Config.INITIAL_BALANCE),
            )
            return api_response(True, {"user_id": user_id, "username": username}, "注册成功")
        return api_response(False, None, "注册失败", 500)
    except Exception as e:
        return api_response(False, None, f"注册失败: {e}", 500)


@app.route("/api/auth/login", methods=["POST"])
def api_login():
    """用户登录（Session 模式）"""
    try:
        data = request.get_json()
        username = (data.get("username") or "").strip()
        password = (data.get("password") or "").strip()

        if not username or not password:
            return api_response(False, None, "用户名和密码不能为空", 400)

        # 查找用户
        users = db.execute_query(
            "SELECT * FROM users WHERE username = ? AND is_active = 1", (username,)
        )
        if not users:
            return api_response(False, None, "用户名或密码错误", 401)

        user = users[0]

        # 验证密码
        if not check_password_hash(user["password_hash"], password):
            return api_response(False, None, "用户名或密码错误", 401)

        # 写入 Session
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["role"] = user.get("role", "user")
        session.permanent = True

        # 更新最后登录时间
        db.execute_update(
            "UPDATE users SET last_login = datetime('now','localtime'), last_ip = ? WHERE id = ?",
            (request.remote_addr or "", user["id"]),
        )

        return api_response(True, {
            "user_id": user["id"],
            "username": user["username"],
            "role": user.get("role", "user"),
        }, "登录成功")
    except Exception as e:
        return api_response(False, None, f"登录失败: {e}", 500)


@app.route("/api/auth/logout", methods=["GET", "POST"])
def api_logout():
    """退出登录"""
    session.clear()
    return api_response(True, None, "已退出登录")


@app.route("/api/auth/status", methods=["GET"])
def api_auth_status():
    """获取当前登录状态"""
    if "user_id" in session:
        return api_response(True, {
            "logged_in": True,
            "user_id": session["user_id"],
            "username": session.get("username", ""),
            "role": session.get("role", "user"),
        }, "已登录")
    return api_response(True, {"logged_in": False}, "未登录")


# ==================== 页面路由 ====================

@app.route("/")
@login_required
def index():
    """行情首页"""
    return render_template("index.html", active_page="index")


@app.route("/login")
def login_page():
    """登录页面"""
    if "user_id" in session:
        return redirect(url_for("index"))
    return render_template("login.html", active_page="login")


@app.route("/register")
def register_page():
    """注册页面"""
    if "user_id" in session:
        return redirect(url_for("index"))
    return render_template("register.html", active_page="register")


@app.route("/stock/<code>")
@login_required
def stock_detail(code):
    """个股 K 线详情页"""
    return render_template("stock.html", active_page="stock", stock_code=code)


@app.route("/watchlist")
@login_required
def watchlist_page():
    """自选股页面"""
    return render_template("watchlist.html", active_page="watchlist")


@app.route("/portfolio")
@login_required
def portfolio_page():
    """持仓交易页面"""
    return render_template("portfolio.html", active_page="portfolio")


@app.route("/dragon-tiger")
@login_required
def dragon_tiger_page():
    """龙虎榜页面"""
    return render_template("dragon_tiger.html", active_page="dragon-tiger")


@app.route("/settings")
@login_required
def settings_page():
    """设置页面"""
    return render_template("settings.html", active_page="settings")


# ==================== 行情数据 API ====================

@app.route("/api/market/indices", methods=["GET"])
def api_market_indices():
    """获取大盘指数实时行情"""
    try:
        data = fetcher.get_market_indices()
        resp = api_response(True, data, "获取大盘指数成功")
        resp_data = resp.get_json()
        resp_data["data_source"] = fetcher.data_source
        resp_data["market_open"] = fetcher._is_market_open()
        return jsonify(resp_data)
    except Exception as e:
        return api_response(False, None, f"获取大盘指数失败: {e}", 500)


@app.route("/api/market/stocks", methods=["GET"])
def api_market_stocks():
    """
    获取 A 股股票列表
    参数: page, page_size, sort_field, sort_order
    """
    try:
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 50))
        sort_field = request.args.get("sort_field", "f3")
        sort_order = request.args.get("sort_order", "desc")
        data = fetcher.get_stock_list(page, page_size, sort_field, sort_order)
        resp = api_response(True, data, "获取股票列表成功")
        resp_data = resp.get_json()
        resp_data["data_source"] = fetcher.data_source
        return jsonify(resp_data)
    except Exception as e:
        return api_response(False, None, f"获取股票列表失败: {e}", 500)


@app.route("/api/stock/<code>", methods=["GET"])
def api_stock_detail(code):
    """获取个股实时详情"""
    try:
        data = fetcher.get_stock_detail(code)
        resp = api_response(True, data, "获取个股详情成功")
        resp_data = resp.get_json()
        resp_data["data_source"] = fetcher.data_source
        return jsonify(resp_data)
    except Exception as e:
        return api_response(False, None, f"获取个股详情失败: {e}", 500)


@app.route("/api/stock/<code>/kline", methods=["GET"])
def api_stock_kline(code):
    """
    获取 K 线数据
    参数: klt(101日K/102周K/103月K), count(数量)
    """
    try:
        klt = int(request.args.get("klt", 101))
        count = int(request.args.get("count", 120))
        data = fetcher.get_kline_data(code, klt, count)
        resp = api_response(True, data, "获取K线数据成功")
        resp_data = resp.get_json()
        resp_data["data_source"] = fetcher.data_source
        return jsonify(resp_data)
    except Exception as e:
        return api_response(False, None, f"获取K线数据失败: {e}", 500)


@app.route("/api/stock/search", methods=["GET"])
def api_stock_search():
    """搜索股票"""
    try:
        keyword = request.args.get("keyword", "")
        if not keyword:
            return api_response(True, [], "请输入搜索关键词")
        data = fetcher.search_stock(keyword)
        return api_response(True, data, "搜索成功")
    except Exception as e:
        return api_response(False, None, f"搜索失败: {e}", 500)


@app.route("/api/dragon-tiger", methods=["GET"])
def api_dragon_tiger():
    """获取龙虎榜数据"""
    try:
        data = fetcher.get_dragon_tiger()
        resp = api_response(True, data, "获取龙虎榜成功")
        resp_data = resp.get_json()
        resp_data["data_source"] = fetcher.data_source
        return jsonify(resp_data)
    except Exception as e:
        return api_response(False, None, f"获取龙虎榜失败: {e}", 500)


@app.route("/api/news", methods=["GET"])
def api_news():
    """获取实时财经热点新闻"""
    try:
        count = int(request.args.get("count", 15))
        data = fetcher.get_news(count)
        resp = api_response(True, data, "获取热点讯息成功")
        resp_data = resp.get_json()
        resp_data["market_open"] = fetcher._is_market_open()
        return jsonify(resp_data)
    except Exception as e:
        return api_response(False, None, f"获取新闻失败: {e}", 500)


# ==================== 自选股 API ====================

@app.route("/api/watchlist", methods=["GET"])
def api_watchlist_list():
    """获取自选股列表"""
    try:
        rows = db.execute_query(
            "SELECT * FROM watchlist WHERE is_deleted = 0 ORDER BY sort_order DESC, created_at DESC"
        )
        # 补充实时行情
        result = []
        for row in rows:
            stock_data = fetcher.get_stock_detail(row["stock_code"])
            row["current_price"] = stock_data.get("price", 0)
            row["change_pct"] = stock_data.get("change_pct", 0)
            row["change"] = stock_data.get("change", 0)
            result.append(row)
        return api_response(True, result, "获取自选股成功")
    except Exception as e:
        return api_response(False, None, f"获取自选股失败: {e}", 500)


@app.route("/api/watchlist", methods=["POST"])
def api_watchlist_add():
    """添加自选股"""
    try:
        data = request.get_json()
        code = data.get("stock_code", "").strip()
        name = data.get("stock_name", "").strip()
        if not code:
            return api_response(False, None, "股票代码不能为空", 400)
        # 如果没有名称，自动获取
        if not name:
            detail = fetcher.get_stock_detail(code)
            name = detail.get("name", code)
        # 检查是否已存在
        existing = db.execute_query(
            "SELECT * FROM watchlist WHERE stock_code = ? AND is_deleted = 0", (code,)
        )
        if existing:
            return api_response(False, None, "该股票已在自选列表中", 400)
        # 插入
        new_id = db.execute_insert(
            "INSERT INTO watchlist (stock_code, stock_name, market, add_price, note, sort_order) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (code, name, data.get("market", ""), data.get("add_price", 0),
             data.get("note", ""), data.get("sort_order", 0)),
        )
        if new_id > 0:
            return api_response(True, {"id": new_id}, "添加自选成功")
        return api_response(False, None, "添加自选失败", 500)
    except Exception as e:
        return api_response(False, None, f"添加自选失败: {e}", 500)


@app.route("/api/watchlist/<int:item_id>", methods=["DELETE"])
def api_watchlist_remove(item_id):
    """删除自选股（逻辑删除）"""
    try:
        affected = db.execute_update(
            "UPDATE watchlist SET is_deleted = 1, updated_at = datetime('now','localtime') WHERE id = ?",
            (item_id,),
        )
        if affected > 0:
            return api_response(True, None, "删除自选成功")
        return api_response(False, None, "未找到该自选记录", 404)
    except Exception as e:
        return api_response(False, None, f"删除自选失败: {e}", 500)


@app.route("/api/watchlist/<int:item_id>", methods=["PUT"])
def api_watchlist_update(item_id):
    """更新自选股信息（备注等）"""
    try:
        data = request.get_json()
        affected = db.execute_update(
            "UPDATE watchlist SET note = ?, sort_order = ?, updated_at = datetime('now','localtime') WHERE id = ?",
            (data.get("note", ""), data.get("sort_order", 0), item_id),
        )
        if affected > 0:
            return api_response(True, None, "更新自选成功")
        return api_response(False, None, "未找到该自选记录", 404)
    except Exception as e:
        return api_response(False, None, f"更新自选失败: {e}", 500)


# ==================== 持仓 & 交易 API ====================

@app.route("/api/portfolio", methods=["GET"])
def api_portfolio_list():
    """获取当前持仓"""
    try:
        rows = db.execute_query(
            "SELECT * FROM portfolio WHERE is_deleted = 0 ORDER BY created_at DESC"
        )
        # 补充实时行情
        result = []
        for row in rows:
            stock_data = fetcher.get_stock_detail(row["stock_code"])
            current_price = stock_data.get("price", 0)
            row["current_price"] = current_price
            row["market_value"] = round(current_price * row["quantity"], 2)
            row["profit"] = round((current_price - row["avg_cost"]) * row["quantity"], 2)
            row["profit_pct"] = round(
                (current_price - row["avg_cost"]) / row["avg_cost"] * 100, 2
            ) if row["avg_cost"] > 0 else 0
            row["name"] = stock_data.get("name", row["stock_name"])
            row["change_pct"] = stock_data.get("change_pct", 0)
            result.append(row)
        return api_response(True, result, "获取持仓成功")
    except Exception as e:
        return api_response(False, None, f"获取持仓失败: {e}", 500)


@app.route("/api/account", methods=["GET"])
def api_account():
    """获取账户信息"""
    try:
        rows = db.execute_query("SELECT * FROM account ORDER BY id DESC LIMIT 1")
        if rows:
            account = rows[0]
            # 计算持仓总市值
            holdings = db.execute_query(
                "SELECT * FROM portfolio WHERE is_deleted = 0"
            )
            total_market_value = 0
            total_cost = 0
            for h in holdings:
                stock_data = fetcher.get_stock_detail(h["stock_code"])
                current_price = stock_data.get("price", 0)
                total_market_value += current_price * h["quantity"]
                total_cost += h["total_cost"]
            account["total_market_value"] = round(total_market_value, 2)
            account["total_assets"] = round(account["balance"] + total_market_value, 2)
            account["total_cost"] = round(total_cost, 2)
            account["total_profit"] = round(total_market_value - total_cost, 2)
            account["total_profit_pct"] = round(
                (total_market_value - total_cost) / total_cost * 100, 2
            ) if total_cost > 0 else 0
            return api_response(True, account, "获取账户信息成功")
        return api_response(False, None, "账户不存在", 404)
    except Exception as e:
        return api_response(False, None, f"获取账户失败: {e}", 500)


@app.route("/api/trade", methods=["POST"])
def api_trade():
    """
    模拟交易（买入/卖出）
    参数: stock_code, stock_name, trade_type(buy/sell), quantity, price
    """
    try:
        data = request.get_json()
        code = data.get("stock_code", "").strip()
        name = data.get("stock_name", "").strip()
        trade_type = data.get("trade_type", "")
        quantity = int(data.get("quantity", 0))
        price = float(data.get("price", 0))

        # 边界校验
        if not code or not name:
            return api_response(False, None, "股票代码和名称不能为空", 400)
        if trade_type not in ("buy", "sell"):
            return api_response(False, None, "交易类型必须为 buy 或 sell", 400)
        if quantity <= 0 or quantity % 100 != 0:
            return api_response(False, None, "交易数量必须为 100 的正整数倍", 400)
        if price <= 0:
            return api_response(False, None, "交易价格必须大于 0", 400)

        total_amount = round(price * quantity, 2)
        fee = round(total_amount * 0.0003, 2)  # 模拟手续费 0.03%
        if fee < 5:
            fee = 5  # 最低手续费 5 元

        # 获取账户
        account = db.execute_query("SELECT * FROM account ORDER BY id DESC LIMIT 1")
        if not account:
            return api_response(False, None, "账户不存在", 500)
        account = account[0]

        if trade_type == "buy":
            # 买入：检查资金是否充足
            needed = total_amount + fee
            if account["balance"] < needed:
                return api_response(False, None, f"资金不足，需要 {needed:.2f} 元，可用 {account['balance']:.2f} 元", 400)
            # 扣减资金
            db.execute_update(
                "UPDATE account SET balance = balance - ?, updated_at = datetime('now','localtime') WHERE id = ?",
                (needed, account["id"]),
            )
            # 更新持仓
            existing = db.execute_query(
                "SELECT * FROM portfolio WHERE stock_code = ? AND is_deleted = 0", (code,)
            )
            if existing:
                old = existing[0]
                new_qty = old["quantity"] + quantity
                new_cost = old["total_cost"] + total_amount
                new_avg = round(new_cost / new_qty, 4) if new_qty > 0 else 0
                db.execute_update(
                    "UPDATE portfolio SET quantity = ?, avg_cost = ?, total_cost = ?, "
                    "updated_at = datetime('now','localtime') WHERE id = ?",
                    (new_qty, new_avg, new_cost, old["id"]),
                )
            else:
                db.execute_insert(
                    "INSERT INTO portfolio (stock_code, stock_name, market, quantity, avg_cost, total_cost) "
                    "VALUES (?, ?, '', ?, ?, ?)",
                    (code, name, quantity, price, total_amount),
                )
        else:
            # 卖出：检查持仓是否充足
            existing = db.execute_query(
                "SELECT * FROM portfolio WHERE stock_code = ? AND is_deleted = 0", (code,)
            )
            if not existing:
                return api_response(False, None, "无该股票持仓，无法卖出", 400)
            old = existing[0]
            if old["quantity"] < quantity:
                return api_response(False, None, f"持仓不足，当前持有 {old['quantity']} 股", 400)
            # 增加资金
            income = total_amount - fee
            db.execute_update(
                "UPDATE account SET balance = balance + ?, updated_at = datetime('now','localtime') WHERE id = ?",
                (income, account["id"]),
            )
            # 更新持仓
            new_qty = old["quantity"] - quantity
            if new_qty == 0:
                db.execute_update(
                    "UPDATE portfolio SET quantity = 0, is_deleted = 1, "
                    "updated_at = datetime('now','localtime') WHERE id = ?",
                    (old["id"],),
                )
            else:
                new_cost = round(old["avg_cost"] * new_qty, 2)
                db.execute_update(
                    "UPDATE portfolio SET quantity = ?, total_cost = ?, "
                    "updated_at = datetime('now','localtime') WHERE id = ?",
                    (new_qty, new_cost, old["id"]),
                )

        # 记录交易
        db.execute_insert(
            "INSERT INTO transactions (stock_code, stock_name, trade_type, quantity, price, total_amount, fee) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (code, name, trade_type, quantity, price, total_amount, fee),
        )
        return api_response(
            True,
            {"trade_type": trade_type, "stock_code": code, "quantity": quantity,
             "price": price, "total_amount": total_amount, "fee": fee},
            f"{'买入' if trade_type == 'buy' else '卖出'}{name}({code}) {quantity}股 @ {price}元 成功",
        )
    except Exception as e:
        return api_response(False, None, f"交易失败: {e}", 500)


@app.route("/api/transactions", methods=["GET"])
def api_transactions():
    """获取交易记录"""
    try:
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))
        offset = (page - 1) * page_size
        rows = db.execute_query(
            "SELECT * FROM transactions ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (page_size, offset),
        )
        total_rows = db.execute_query("SELECT COUNT(*) as cnt FROM transactions")
        total = total_rows[0]["cnt"] if total_rows else 0
        return api_response(
            True,
            {"list": rows, "total": total, "page": page, "page_size": page_size},
            "获取交易记录成功",
        )
    except Exception as e:
        return api_response(False, None, f"获取交易记录失败: {e}", 500)


# ==================== 配置 API ====================

@app.route("/api/status", methods=["GET"])
def api_status():
    """健康检查 + 数据源状态"""
    try:
        return api_response(True, {
            "status": "running",
            "data_source": fetcher.data_source,
            "market_open": fetcher._is_market_open(),
            "version": "2.1",
            "api_base": Config.EASTMONEY_PUSH_URL,
        }, "应用运行正常")
    except Exception as e:
        return api_response(False, None, str(e), 500)


@app.route("/api/settings", methods=["GET"])
def api_settings_get():
    """获取应用配置"""
    try:
        rows = db.execute_query("SELECT * FROM settings")
        settings = {row["key"]: row["value"] for row in rows}
        return api_response(True, settings, "获取配置成功")
    except Exception as e:
        return api_response(False, None, f"获取配置失败: {e}", 500)


@app.route("/api/settings", methods=["PUT"])
def api_settings_update():
    """更新应用配置"""
    try:
        data = request.get_json()
        for k, v in data.items():
            db.execute_update(
                "UPDATE settings SET value = ?, updated_at = datetime('now','localtime') WHERE key = ?",
                (str(v), k),
            )
        return api_response(True, None, "配置更新成功")
    except Exception as e:
        return api_response(False, None, f"配置更新失败: {e}", 500)


# ==================== 错误处理 ====================

@app.errorhandler(404)
def not_found(e):
    """404 错误处理"""
    if request.path.startswith("/api/"):
        return api_response(False, None, "接口不存在", 404)
    return render_template("index.html", active_page="index"), 404


@app.errorhandler(500)
def server_error(e):
    """500 错误处理"""
    if request.path.startswith("/api/"):
        return api_response(False, None, "服务器内部错误", 500)
    return api_response(False, None, "服务器内部错误", 500)


# ==================== 启动入口 ====================

if __name__ == "__main__":
    print("=" * 60)
    print("  投资分析应用 - 多巴胺风格 Web 版")
    if Config.IS_CLOUD:
        print(f"  云端部署模式 | 端口: {Config.PORT}")
    else:
        print(f"  访问地址: http://127.0.0.1:{Config.PORT}")
    print("  API Token: " + Config.API_TOKEN)
    print("=" * 60)

    # PyInstaller 打包后关闭 debug 模式，提高稳定性
    is_frozen = getattr(sys, 'frozen', False)
    debug_mode = Config.DEBUG if not is_frozen else False

    if is_frozen and not Config.IS_CLOUD:
        # 本地打包后启动浏览器（云端不打开浏览器）
        print("  正在打开浏览器...")
        import threading
        def open_browser():
            import time
            time.sleep(1.5)
            webbrowser.open(f"http://127.0.0.1:{Config.PORT}")
        threading.Thread(target=open_browser, daemon=True).start()

    # 云端用 gunicorn 启动（通过 Procfile），本地用 Flask 内置服务器
    if not Config.IS_CLOUD:
        app.run(host="0.0.0.0", port=Config.PORT, debug=debug_mode, use_reloader=not is_frozen)
