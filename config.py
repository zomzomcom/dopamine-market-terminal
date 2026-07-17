# -*- coding: utf-8 -*-
"""
文件名: config.py
功能说明: 投资分析应用全局配置文件，包含数据库、API、安全等配置项
作者: Investment App Team
创建日期: 2024-01-01
"""

import os

# 项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    """应用全局配置类"""

    # Flask 基础配置
    SECRET_KEY = os.environ.get("SECRET_KEY", "dopamine-investment-app-2024-secure-key")

    # Session 配置（用户登录态）
    SESSION_COOKIE_NAME = "dopamine_session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 86400 * 7  # 7 天免登录

    # ==================== 数据库配置 ====================

    # 是否为云端部署（Render/Heroku 等平台）
    IS_CLOUD = "RENDER" in os.environ or "DYNO" in os.environ

    # 数据库类型: "sqlite"（本地 EXE 开箱即用）或 "mysql"（HeidiSQL 管理 / 云端）
    DB_TYPE = os.environ.get("DB_TYPE", "mysql" if IS_CLOUD else "sqlite")

    # SQLite 数据库路径（DB_TYPE = sqlite 时使用）
    DB_PATH = os.path.join(BASE_DIR, "database", "investment.db")
    DB_URI = f"sqlite:///{DB_PATH}"

    # MySQL 配置（DB_TYPE = mysql 时使用，HeidiSQL 也连接这里）
    MYSQL_HOST = os.environ.get("MYSQL_HOST", "127.0.0.1")
    MYSQL_PORT = int(os.environ.get("MYSQL_PORT", 3306))
    MYSQL_USER = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "root")
    MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "investment_app")
    MYSQL_URI = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@"
        f"{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"
    )

    # API 鉴权 Token（简易鉴权，防止接口被随意调用）
    API_TOKEN = "demo-token-2024"

    # 行情数据刷新间隔（秒）
    REFRESH_INTERVAL = 5

    # 东方财富 API 基础地址
    EASTMONEY_PUSH_URL = "http://push2.eastmoney.com/api/qt"
    EASTMONEY_PUSHHIS_URL = "http://push2his.eastmoney.com/api/qt"
    EASTMONEY_DATACENTER_URL = "http://datacenter-web.eastmoney.com/api/data/v1/get"

    # 请求超时时间（秒）
    REQUEST_TIMEOUT = 10

    # 请求重试次数
    MAX_RETRIES = 3

    # 请求间隔（秒），防止高频请求触发风控
    REQUEST_INTERVAL = 0.5

    # 模拟账户初始资金（元）
    INITIAL_BALANCE = 1000000.00

    # 应用端口（云端部署时通过环境变量 PORT 传入，本地默认 5000）
    PORT = int(os.environ.get("PORT", 5000))

    # 调试模式（云端自动关闭）
    DEBUG = os.environ.get("FLASK_ENV", "development") != "production"
