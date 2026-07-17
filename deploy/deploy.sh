#!/bin/bash
# ============================================================
# 多巴胺行情终端 — 国内云服务器一键部署脚本
# 适用: Ubuntu 20.04+ / Debian 11+
# 用法: chmod +x deploy.sh && sudo bash deploy.sh
# ============================================================

set -e

APP_NAME="dopamine-market"
APP_DIR="/opt/${APP_NAME}"
DOMAIN="${1:-localhost}"  # 第一个参数为域名，默认 localhost

echo "============================================"
echo "  多巴胺行情终端 - 服务器部署"
echo "  目标域名: ${DOMAIN}"
echo "============================================"

# 1. 系统更新 & 安装依赖
echo ""
echo "[1/6] 安装系统依赖..."
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip nginx supervisor sqlite3

# 2. 创建应用目录 & 复制代码
echo ""
echo "[2/6] 部署应用代码到 ${APP_DIR}..."
mkdir -p ${APP_DIR} ${APP_DIR}/logs ${APP_DIR}/database
cp -r ../* ${APP_DIR}/
cp -r ../.gitignore ${APP_DIR}/ 2>/dev/null || true

# 3. 创建 Python 虚拟环境 & 安装依赖
echo ""
echo "[3/6] 安装 Python 依赖..."
python3 -m venv ${APP_DIR}/venv
${APP_DIR}/venv/bin/pip install --upgrade pip -q
${APP_DIR}/venv/bin/pip install -r ${APP_DIR}/requirements.txt -q

# 4. 初始化数据库 & 管理员账号
echo ""
echo "[4/6] 初始化数据库和管理员账号..."
cd ${APP_DIR}
${APP_DIR}/venv/bin/python init_admin.py

# 5. 配置 Nginx
echo ""
echo "[5/6] 配置 Nginx..."
# 替换域名
sed "s/your-domain.com/${DOMAIN}/g" ${APP_DIR}/deploy/nginx.conf > /etc/nginx/sites-available/${APP_NAME}
ln -sf /etc/nginx/sites-available/${APP_NAME} /etc/nginx/sites-enabled/
# 删除默认站点
rm -f /etc/nginx/sites-enabled/default
# 测试配置
nginx -t
systemctl reload nginx

# 6. 配置 Supervisor
echo ""
echo "[6/6] 配置 Supervisor 进程守护..."
cp ${APP_DIR}/deploy/supervisor.conf /etc/supervisor/conf.d/${APP_NAME}.conf
supervisorctl reread
supervisorctl update
supervisorctl start ${APP_NAME}

# 完成
echo ""
echo "============================================"
echo "  部署完成！"
echo "============================================"
echo ""
echo "  访问地址: http://${DOMAIN}"
echo "  默认账号: admin / admin123"
echo ""
echo "  管理命令:"
echo "    查看状态: supervisorctl status ${APP_NAME}"
echo "    重启应用: supervisorctl restart ${APP_NAME}"
echo "    查看日志: tail -f ${APP_DIR}/logs/gunicorn_error.log"
echo ""
echo "  获取 SSL 证书 (推荐):"
echo "    apt-get install certbot python3-certbot-nginx"
echo "    certbot --nginx -d ${DOMAIN}"
echo "============================================"
