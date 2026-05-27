#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

source .venv/bin/activate

# 确保本机 MySQL 已启动（端口 3307，避免与 /usr/local/mysql 的 3306 冲突）
MYSQL_PORT=3307
MYSQL_SOCKET=/tmp/mysql_brew.sock

if ! mysqladmin ping -u root --socket="$MYSQL_SOCKET" --silent 2>/dev/null; then
    echo "==> 启动 MySQL（端口 $MYSQL_PORT）..."
    pkill -f "homebrew.*mysqld" 2>/dev/null || true
    pkill -f mysqld_safe 2>/dev/null || true
    sleep 2
    brew services start mysql 2>/dev/null || true
    # brew MySQL 默认绑定 3306，若端口被占则手动启动到 3307
    if ! mysqladmin ping -u root --socket="$MYSQL_SOCKET" --silent 2>/dev/null; then
        mysqld_safe \
            --datadir=/opt/homebrew/var/mysql \
            --port="$MYSQL_PORT" \
            --socket="$MYSQL_SOCKET" \
            --skip-mysqlx &
        # 等待 MySQL 就绪（最多 30 秒）
        for i in $(seq 1 15); do
            sleep 2
            if mysqladmin ping -u root --socket="$MYSQL_SOCKET" --silent 2>/dev/null; then
                echo "==> MySQL 就绪"
                break
            fi
        done
    fi
fi

echo "==> 安装依赖..."
pip install -q -r requirements.txt

echo "==> 启动 FastAPI 服务 (http://127.0.0.1:8000)..."
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
