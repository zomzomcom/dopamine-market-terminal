# -*- coding: utf-8 -*-
"""
文件名: db_helper.py
功能说明: 数据库操作工具类，封装增删改查通用方法
          支持 SQLite（本地 EXE 开箱即用）和 MySQL（HeidiSQL 管理 / 云端部署）
          两种模式接口完全一致，通过 Config.DB_TYPE 切换
作者: Investment App Team
创建日期: 2024-01-01
最后更新: 2026-07-17（新增 MySQL 支持和 users 表）
"""

import os
import logging
from datetime import datetime
from typing import Any, Optional

from config import Config

# 日志配置
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class DBHelper:
    """数据库操作工具类（SQLite / MySQL 双模式）"""

    def __init__(self):
        """初始化数据库连接，根据 Config.DB_TYPE 选择引擎"""
        self.db_type = Config.DB_TYPE
        self._init_connection()
        self._init_tables()

    # ==================== 连接管理 ====================

    def _init_connection(self):
        """根据数据库类型初始化连接"""
        if self.db_type == "mysql":
            self._init_mysql()
        else:
            self._init_sqlite()

    def _init_sqlite(self):
        """初始化 SQLite 连接"""
        self.db_path = Config.DB_PATH
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        logger.info(f"数据库引擎: SQLite | 路径: {self.db_path}")

    def _init_mysql(self):
        """初始化 MySQL 连接"""
        try:
            import pymysql
            self._pymysql = pymysql
            logger.info(
                f"数据库引擎: MySQL | {Config.MYSQL_HOST}:{Config.MYSQL_PORT}/{Config.MYSQL_DATABASE}"
            )
        except ImportError:
            logger.error("PyMySQL 未安装，请运行: pip install PyMySQL")
            raise

    def _get_conn(self):
        """获取数据库连接"""
        if self.db_type == "mysql":
            return self._get_mysql_conn()
        return self._get_sqlite_conn()

    def _get_sqlite_conn(self):
        """获取 SQLite 连接"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _get_mysql_conn(self):
        """获取 MySQL 连接"""
        conn = self._pymysql.connect(
            host=Config.MYSQL_HOST,
            port=Config.MYSQL_PORT,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DATABASE,
            charset="utf8mb4",
            cursorclass=self._pymysql.cursors.DictCursor,
            autocommit=False,
        )
        return conn

    # ==================== 表初始化 ====================

    def _init_tables(self):
        """初始化所有数据库表结构"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            if self.db_type == "sqlite":
                self._init_tables_sqlite(cursor)
            else:
                self._init_tables_mysql(cursor)

            conn.commit()
            logger.info("数据库表初始化完成")
        except Exception as e:
            logger.error(f"数据库表初始化失败: {e}")
            raise
        finally:
            if "conn" in dir():
                conn.close()

    def _init_tables_sqlite(self, cursor):
        """SQLite 建表语句"""
        # 用户表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                email TEXT DEFAULT '',
                role TEXT DEFAULT 'user',
                is_active INTEGER DEFAULT 1,
                last_login TEXT DEFAULT NULL,
                last_ip TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)

        # 自选股表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                stock_code TEXT NOT NULL,
                stock_name TEXT NOT NULL,
                market TEXT DEFAULT '',
                add_price REAL DEFAULT 0,
                note TEXT DEFAULT '',
                sort_order INTEGER DEFAULT 0,
                is_deleted INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)

        # 持仓表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                stock_code TEXT NOT NULL,
                stock_name TEXT NOT NULL,
                market TEXT DEFAULT '',
                quantity INTEGER NOT NULL DEFAULT 0,
                avg_cost REAL NOT NULL DEFAULT 0,
                total_cost REAL NOT NULL DEFAULT 0,
                is_deleted INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)

        # 交易记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                stock_code TEXT NOT NULL,
                stock_name TEXT NOT NULL,
                trade_type TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                total_amount REAL NOT NULL,
                fee REAL DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)

        # 账户表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS account (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                balance REAL NOT NULL DEFAULT 1000000,
                frozen REAL DEFAULT 0,
                initial_balance REAL DEFAULT 1000000,
                updated_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)

        # 应用配置表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL UNIQUE,
                value TEXT DEFAULT '',
                updated_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)

        # 初始化账户
        cursor.execute("SELECT COUNT(*) as cnt FROM account")
        if cursor.fetchone()["cnt"] == 0:
            cursor.execute(
                "INSERT INTO account (balance, frozen, initial_balance) VALUES (?, ?, ?)",
                (Config.INITIAL_BALANCE, 0, Config.INITIAL_BALANCE),
            )

        # 初始化默认配置
        default_settings = {
            "theme": "dopamine",
            "refresh_interval": "5",
            "chart_type": "candlestick",
            "ma_periods": "5,10,20,60",
        }
        for k, v in default_settings.items():
            cursor.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v)
            )

        # 索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_watchlist_code ON watchlist(stock_code)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_portfolio_code ON portfolio(stock_code)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_code ON transactions(stock_code)")

    def _init_tables_mysql(self, cursor):
        """MySQL 建表语句"""
        tables = [
            # 用户表
            """CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY COMMENT '用户ID',
                username VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
                password_hash VARCHAR(255) NOT NULL COMMENT '密码哈希值',
                email VARCHAR(100) DEFAULT '' COMMENT '邮箱',
                role VARCHAR(20) DEFAULT 'user' COMMENT '角色',
                is_active TINYINT(1) DEFAULT 1 COMMENT '是否启用',
                last_login DATETIME DEFAULT NULL COMMENT '最后登录',
                last_ip VARCHAR(45) DEFAULT '' COMMENT '最后登录IP',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '注册时间',
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                INDEX idx_username (username)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表'""",

            # 自选股表
            """CREATE TABLE IF NOT EXISTS watchlist (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT DEFAULT 1,
                stock_code VARCHAR(10) NOT NULL,
                stock_name VARCHAR(50) NOT NULL,
                market VARCHAR(10) DEFAULT '',
                add_price DECIMAL(10,3) DEFAULT 0,
                note VARCHAR(200) DEFAULT '',
                sort_order INT DEFAULT 0,
                is_deleted TINYINT(1) DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_code (stock_code),
                INDEX idx_user (user_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='自选股表'""",

            # 持仓表
            """CREATE TABLE IF NOT EXISTS portfolio (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT DEFAULT 1,
                stock_code VARCHAR(10) NOT NULL,
                stock_name VARCHAR(50) NOT NULL,
                market VARCHAR(10) DEFAULT '',
                quantity INT NOT NULL DEFAULT 0,
                avg_cost DECIMAL(10,4) NOT NULL DEFAULT 0,
                total_cost DECIMAL(18,2) NOT NULL DEFAULT 0,
                is_deleted TINYINT(1) DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_code (stock_code),
                INDEX idx_user (user_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='持仓表'""",

            # 交易记录表
            """CREATE TABLE IF NOT EXISTS transactions (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_id INT DEFAULT 1,
                stock_code VARCHAR(10) NOT NULL,
                stock_name VARCHAR(50) NOT NULL,
                trade_type VARCHAR(10) NOT NULL,
                quantity INT NOT NULL,
                price DECIMAL(10,3) NOT NULL,
                total_amount DECIMAL(18,2) NOT NULL,
                fee DECIMAL(10,2) DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_code (stock_code),
                INDEX idx_time (created_at),
                INDEX idx_user (user_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='交易记录表'""",

            # 账户表
            """CREATE TABLE IF NOT EXISTS account (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT DEFAULT 1,
                balance DECIMAL(18,2) NOT NULL DEFAULT 1000000,
                frozen DECIMAL(18,2) DEFAULT 0,
                initial_balance DECIMAL(18,2) DEFAULT 1000000,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_user (user_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='账户表'""",

            # 配置表
            """CREATE TABLE IF NOT EXISTS settings (
                id INT AUTO_INCREMENT PRIMARY KEY,
                `key` VARCHAR(50) NOT NULL UNIQUE,
                `value` TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='配置表'""",
        ]

        for sql in tables:
            cursor.execute(sql)

        # 初始化账户（MySQL 用 INSERT IGNORE）
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM account"
        )
        if cursor.fetchone()["cnt"] == 0:
            cursor.execute(
                "INSERT INTO account (balance, frozen, initial_balance) VALUES (%s, %s, %s)",
                (Config.INITIAL_BALANCE, 0, Config.INITIAL_BALANCE),
            )

        # 初始化配置
        default_settings = {
            "theme": "dopamine",
            "refresh_interval": "5",
            "chart_type": "candlestick",
            "ma_periods": "5,10,20,60",
        }
        for k, v in default_settings.items():
            cursor.execute(
                "INSERT IGNORE INTO settings (`key`, `value`) VALUES (%s, %s)", (k, v)
            )

    # ==================== 基础操作 ====================

    def _get_placeholder(self):
        """获取 SQL 占位符：SQLite 用 ?，MySQL 用 %s"""
        return "%s" if self.db_type == "mysql" else "?"

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
            # 自动适配占位符
            if self.db_type == "sqlite":
                cursor.execute(sql, params)
            else:
                cursor.execute(sql.replace("?", "%s"), params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"查询失败: {sql[:100]} | 错误: {e}")
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
            if self.db_type == "sqlite":
                cursor.execute(sql, params)
            else:
                cursor.execute(sql.replace("?", "%s"), params)
            conn.commit()
            return cursor.rowcount
        except Exception as e:
            logger.error(f"更新失败: {sql[:100]} | 错误: {e}")
            try:
                conn.rollback()
            except Exception:
                pass
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
            if self.db_type == "sqlite":
                cursor.execute(sql, params)
            else:
                cursor.execute(sql.replace("?", "%s"), params)
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"插入失败: {sql[:100]} | 错误: {e}")
            try:
                conn.rollback()
            except Exception:
                pass
            return -1
        finally:
            if "conn" in dir():
                conn.close()


# 全局数据库实例（单例模式）
db = DBHelper()
