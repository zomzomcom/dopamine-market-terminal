# -*- coding: utf-8 -*-
"""
文件名: init_mysql.py
功能说明: MySQL 数据库一键初始化脚本
         自动创建数据库、导入表结构、创建管理员账号
使用方式: python init_mysql.py
HeidiSQL 连接信息:
   主机: 127.0.0.1  端口: 3306  用户: root
   密码: root（如已修改请更新 config.py）  数据库: investment_app
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pymysql
from werkzeug.security import generate_password_hash
from config import Config

# 连接信息
HOST = Config.MYSQL_HOST
PORT = Config.MYSQL_PORT
USER = Config.MYSQL_USER
PASSWORD = Config.MYSQL_PASSWORD
DATABASE = Config.MYSQL_DATABASE

# 默认管理员账号
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
ADMIN_EMAIL = "admin@dopamine.app"


def main():
    print("=" * 60)
    print("  多巴胺行情终端 - MySQL 数据库初始化")
    print("=" * 60)

    # 1. 连接 MySQL（不指定数据库）
    print(f"\n[1/4] 连接 MySQL {HOST}:{PORT} ...")
    try:
        conn = pymysql.connect(
            host=HOST, port=PORT, user=USER, password=PASSWORD,
            charset="utf8mb4", autocommit=True,
        )
        cursor = conn.cursor()
        print("  连接成功！")
    except Exception as e:
        print(f"  连接失败: {e}")
        print("\n  请检查:")
        print("  1. MySQL 服务是否已启动")
        print("  2. config.py 中 MYSQL_PASSWORD 是否正确")
        return

    # 2. 创建数据库
    print(f"\n[2/4] 创建数据库 {DATABASE} ...")
    cursor.execute(
        f"CREATE DATABASE IF NOT EXISTS `{DATABASE}` "
        "DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_unicode_ci"
    )
    cursor.execute(f"USE `{DATABASE}`")
    print("  数据库就绪！")

    # 3. 导入表结构
    print("\n[3/4] 创建表结构 ...")
    schema_file = os.path.join(os.path.dirname(__file__), "database", "schema_mysql.sql")
    if not os.path.exists(schema_file):
        print(f"  错误: 找不到 {schema_file}")
        return

    with open(schema_file, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    # 只执行 CREATE TABLE 语句（跳过注释和初始化数据）
    statements = []
    for stmt in schema_sql.split(";"):
        stmt = stmt.strip()
        if not stmt or stmt.startswith("--") or stmt.startswith("/*"):
            continue
        # 跳过 CREATE DATABASE / USE（已执行）
        if stmt.upper().startswith("CREATE DATABASE") or stmt.upper().startswith("USE "):
            continue
        statements.append(stmt)

    for stmt in statements:
        if "CREATE TABLE" in stmt.upper():
            table_name = stmt.split("`")[1] if "`" in stmt else "?"
            try:
                cursor.execute(stmt)
                print(f"  ✓ {table_name}")
            except Exception as e:
                print(f"  ✗ {table_name}: {e}")

    # 初始化配置和账户数据
    init_data = [
        # 初始化账户
        f"INSERT IGNORE INTO `{DATABASE}`.`account` (`balance`, `frozen`, `initial_balance`) VALUES (1000000.00, 0, 1000000.00)",
        # 初始化配置
        f"INSERT IGNORE INTO `{DATABASE}`.`settings` (`key`, `value`) VALUES ('theme', 'dopamine')",
        f"INSERT IGNORE INTO `{DATABASE}`.`settings` (`key`, `value`) VALUES ('refresh_interval', '5')",
        f"INSERT IGNORE INTO `{DATABASE}`.`settings` (`key`, `value`) VALUES ('chart_type', 'candlestick')",
        f"INSERT IGNORE INTO `{DATABASE}`.`settings` (`key`, `value`) VALUES ('ma_periods', '5,10,20,60')",
    ]
    for sql in init_data:
        try:
            cursor.execute(sql)
        except Exception:
            pass

    print("  表结构创建完成！")

    # 4. 创建管理员账号
    print(f"\n[4/4] 创建管理员账号 ...")
    password_hash = generate_password_hash(ADMIN_PASSWORD)

    try:
        cursor.execute(
            "INSERT INTO users (username, password_hash, email, role) VALUES (%s, %s, %s, %s)",
            (ADMIN_USERNAME, password_hash, ADMIN_EMAIL, "admin"),
        )
        print(f"  ✓ 管理员账号创建成功！")
    except pymysql.err.IntegrityError:
        # 已存在则更新密码
        cursor.execute(
            "UPDATE users SET password_hash = %s, email = %s WHERE username = %s",
            (password_hash, ADMIN_EMAIL, ADMIN_USERNAME),
        )
        print(f"  ✓ 管理员账号已存在，密码已更新！")

    cursor.close()
    conn.close()

    # 打印结果
    print("\n" + "=" * 60)
    print("  初始化完成！")
    print("=" * 60)
    print(f"""
  HeidiSQL 连接信息:
    ┌──────────────────────────┐
    │ 主机: {HOST}            │
    │ 端口: {PORT}                       │
    │ 用户: {USER}                      │
    │ 密码: {PASSWORD}                  │
    │ 数据库: {DATABASE}           │
    └──────────────────────────┘

  登录账号:
    用户名: {ADMIN_USERNAME}
    密码:   {ADMIN_PASSWORD}

  下次启动前请设置环境变量切换为 MySQL:
    set DB_TYPE=mysql
    python app.py
""")


if __name__ == "__main__":
    main()
