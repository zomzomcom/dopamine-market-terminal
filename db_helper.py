# -*- coding: utf-8 -*-
"""
文件名: db_helper.py
功能说明: SQLite 数据库操作工具类，封装增删改查通用方法
          支持 MySQL 迁移（提供 schema_mysql.sql 建表脚本）
作者: Investment App Team
创建日期: 2024-01-01
"""

import sqlite3
import os
import logging
from datetime import datetime
from typing import Any, Optional

from config import Config

# 日志配置
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class DBHelper:
    """SQLite 数据库操作工具类"""

    def __init__(self, db_path: str = None):
        """
        初始化数据库连接
        :param db_path: 数据库文件路径，默认使用配置中的路径
        """
        self.db_path = db_path or Config.DB_PATH
        self._ensure_dir()
        self._init_tables()

    def _ensure_dir(self) -> None:
        """确保数据库目录存在"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

    def _get_conn(self) -> sqlite3.Connection:
        """
        获取数据库连接
        :return: sqlite3.Connection 对象
        :raises Exception: 数据库连接失败时抛出异常
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # 使查询结果可通过列名访问
            conn.execute("PRAGMA foreign_keys = ON")  # 开启外键约束
            return conn
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise

    def _init_tables(self) -> None:
        """初始化所有数据库表结构"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            # 自选股表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS watchlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_code TEXT NOT NULL UNIQUE,    -- 股票代码
                    stock_name TEXT NOT NULL,            -- 股票名称
                    market TEXT DEFAULT '',              -- 市场(SH/SZ)
                    add_price REAL DEFAULT 0,            -- 加入时价格
                    note TEXT DEFAULT '',                -- 备注
                    sort_order INTEGER DEFAULT 0,        -- 排序权重
                    is_deleted INTEGER DEFAULT 0,        -- 逻辑删除标识(0正常/1删除)
                    created_at TEXT DEFAULT (datetime('now', 'localtime')),  -- 创建时间
                    updated_at TEXT DEFAULT (datetime('now', 'localtime'))   -- 更新时间
                )
            """)

            # 持仓表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS portfolio (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_code TEXT NOT NULL,            -- 股票代码
                    stock_name TEXT NOT NULL,            -- 股票名称
                    market TEXT DEFAULT '',              -- 市场
                    quantity INTEGER NOT NULL DEFAULT 0, -- 持仓数量(股)
                    avg_cost REAL NOT NULL DEFAULT 0,    -- 平均成本价
                    total_cost REAL NOT NULL DEFAULT 0,  -- 总成本
                    is_deleted INTEGER DEFAULT 0,        -- 逻辑删除
                    created_at TEXT DEFAULT (datetime('now', 'localtime')),
                    updated_at TEXT DEFAULT (datetime('now', 'localtime'))
                )
            """)

            # 交易记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_code TEXT NOT NULL,            -- 股票代码
                    stock_name TEXT NOT NULL,            -- 股票名称
                    trade_type TEXT NOT NULL,            -- 交易类型(buy/sell)
                    quantity INTEGER NOT NULL,           -- 交易数量
                    price REAL NOT NULL,                 -- 交易价格
                    total_amount REAL NOT NULL,          -- 交易总金额
                    fee REAL DEFAULT 0,                  -- 手续费
                    created_at TEXT DEFAULT (datetime('now', 'localtime'))  -- 交易时间
                )
            """)

            # 账户表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS account (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    balance REAL NOT NULL DEFAULT 1000000,  -- 可用资金
                    frozen REAL DEFAULT 0,                   -- 冻结资金
                    initial_balance REAL DEFAULT 1000000,    -- 初始资金
                    updated_at TEXT DEFAULT (datetime('now', 'localtime'))
                )
            """)

            # 应用配置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL UNIQUE,            -- 配置键
                    value TEXT DEFAULT '',               -- 配置值
                    updated_at TEXT DEFAULT (datetime('now', 'localtime'))
                )
            """)

            # 初始化账户记录（如果不存在）
            cursor.execute("SELECT COUNT(*) as cnt FROM account")
            if cursor.fetchone()["cnt"] == 0:
                cursor.execute(
                    "INSERT INTO account (balance, frozen, initial_balance) VALUES (?, ?, ?)",
                    (Config.INITIAL_BALANCE, 0, Config.INITIAL_BALANCE),
                )

            # 初始化默认配置
            default_settings = {
                "theme": "dopamine",          # 主题
                "refresh_interval": "5",       # 刷新间隔
                "chart_type": "candlestick",   # 图表类型
                "ma_periods": "5,10,20,60",    # 均线周期
            }
            for k, v in default_settings.items():
                cursor.execute(
                    "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                    (k, v),
                )

            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_watchlist_code ON watchlist(stock_code)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_portfolio_code ON portfolio(stock_code)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_code ON transactions(stock_code)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_time ON transactions(created_at)")

            conn.commit()
            logger.info("数据库表初始化完成")
        except Exception as e:
            logger.error(f"数据库表初始化失败: {e}")
            raise
        finally:
            if "conn" in dir():
                conn.close()

    def execute_query(self, sql: str, params: tuple = ()) -> list:
        """
        执行查询语句（SELECT）
        :param sql: SQL 查询语句
        :param params: 参数元组
        :return: 查询结果列表（字典格式）
        """
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute(sql, params)  # 参数化查询，防止 SQL 注入
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"查询失败: {sql} | 错误: {e}")
            return []
        finally:
            if "conn" in dir():
                conn.close()

    def execute_update(self, sql: str, params: tuple = ()) -> int:
        """
        执行更新/插入/删除语句
        :param sql: SQL 语句
        :param params: 参数元组
        :return: 受影响行数
        """
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute(sql, params)  # 参数化查询
            conn.commit()
            return cursor.rowcount
        except Exception as e:
            logger.error(f"更新失败: {sql} | 错误: {e}")
            conn.rollback()
            return 0
        finally:
            if "conn" in dir():
                conn.close()

    def execute_insert(self, sql: str, params: tuple = ()) -> int:
        """
        执行插入语句并返回自增 ID
        :param sql: INSERT SQL 语句
        :param params: 参数元组
        :return: 新插入记录的自增 ID，失败返回 -1
        """
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute(sql, params)
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"插入失败: {sql} | 错误: {e}")
            conn.rollback()
            return -1
        finally:
            if "conn" in dir():
                conn.close()


# 全局数据库实例（单例模式）
db = DBHelper()
