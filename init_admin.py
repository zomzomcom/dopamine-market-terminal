# -*- coding: utf-8 -*-
"""
文件名: init_admin.py
功能说明: 为 SQLite 模式创建默认管理员账号
         首次启动应用后运行一次即可
使用方式: python init_admin.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from werkzeug.security import generate_password_hash
from config import Config
from db_helper import db

DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin123"
DEFAULT_EMAIL = "admin@dopamine.app"

def main():
    print("=" * 50)
    print("  创建默认管理员账号")
    print(f"  数据库: {Config.DB_TYPE} | {Config.DB_PATH if Config.DB_TYPE == 'sqlite' else Config.MYSQL_DATABASE}")
    print("=" * 50)

    # 检查是否已存在
    existing = db.execute_query("SELECT id FROM users WHERE username = ?", (DEFAULT_USERNAME,))
    if existing:
        print(f"\n  用户 {DEFAULT_USERNAME} 已存在，跳过创建")
        return

    # 创建管理员
    password_hash = generate_password_hash(DEFAULT_PASSWORD)
    user_id = db.execute_insert(
        "INSERT INTO users (username, password_hash, email, role) VALUES (?, ?, ?, ?)",
        (DEFAULT_USERNAME, password_hash, DEFAULT_EMAIL, "admin"),
    )

    if user_id > 0:
        # 创建关联账户
        db.execute_insert(
            "INSERT INTO account (user_id, balance, initial_balance) VALUES (?, ?, ?)",
            (user_id, Config.INITIAL_BALANCE, Config.INITIAL_BALANCE),
        )
        print(f"\n  ✓ 管理员账号创建成功！")
        print(f"    用户名: {DEFAULT_USERNAME}")
        print(f"    密码:   {DEFAULT_PASSWORD}")
    else:
        print("\n  ✗ 创建失败")


if __name__ == "__main__":
    main()
