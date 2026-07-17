# Gunicorn 生产配置
# 使用: gunicorn -c deploy/gunicorn.conf.py app:app

import multiprocessing
import os

# 绑定地址和端口
bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"

# Worker 进程数（推荐 CPU 核数 * 2 + 1）
workers = multiprocessing.cpu_count() * 2 + 1

# Worker 类型
worker_class = "sync"

# 每个 worker 的线程数
threads = 2

# 最大请求数（超过后自动重启 worker，防止内存泄漏）
max_requests = 1000
max_requests_jitter = 50

# 超时设置
timeout = 120
graceful_timeout = 30
keepalive = 5

# 日志
accesslog = "logs/gunicorn_access.log"
errorlog = "logs/gunicorn_error.log"
loglevel = "info"

# 进程命名
proc_name = "dopamine_market"

# 后台运行
daemon = False

# 环境变量
raw_env = [
    "FLASK_ENV=production",
    "DB_TYPE=sqlite",
]
