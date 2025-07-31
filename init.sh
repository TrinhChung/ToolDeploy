#!/bin/bash

set -e
set -o pipefail
trap 'echo "❌ Đã xảy ra lỗi tại dòng $LINENO. Dừng cài đặt."' ERR

INPUT_DIR="$1"
APP_ID="$2"
APP_SECRET="$3"
DNS_WEB="$4"
APP_NAME="$5"
EMAIL="$6"
ADDRESS="$7"
PHONE_NUMBER="$8"
COMPANY_NAME="$9"
TAX_NUMBER="${10}"
TARGET_DIR="/home/$INPUT_DIR"

# ---------- Hàm tìm cổng trống ----------
find_free_port() {
  local base=${1:-5000}
  local port=$base
  while ss -lnt sport = :$port 2>/dev/null | grep -q LISTEN; do
    port=$((port + 1))
  done
  echo "$port"
}

echo "📦 Cập nhật gói và cài ca-certificates, curl, gnupg, lsb-release..."
sudo DEBIAN_FRONTEND=noninteractive apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y ca-certificates curl gnupg lsb-release

# --- Git ---
if ! dpkg -s git &> /dev/null; then
  echo "🧰 Cài đặt Git..."
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y git
else
  echo "✅ Git đã được cài."
fi

# --- Moreutils ---
if ! command -v ts >/dev/null 2>&1; then
  echo "Cài đặt moreutils..."
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y moreutils
else
  echo "moreutils đã được cài."
fi

# --- Nginx ---
if ! dpkg -s nginx &> /dev/null; then
  echo "🌐 Cài đặt Nginx..."
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y nginx
else
  echo "✅ Nginx đã được cài."
fi

sudo ufw allow 80
sudo ufw allow 443

# --- Python ---
if ! command -v python3 &> /dev/null; then
  echo "🐍 Cài đặt Python3..."
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python3
else
  echo "✅ Python3 đã được cài."
fi

# --- Pip ---
if ! command -v pip3 &> /dev/null; then
  echo "🐍 Cài đặt PIP..."
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python3-pip
else
  echo "✅ PIP đã được cài."
fi

if ! dpkg -s python3-venv &> /dev/null; then
  echo "🐍 Cài đặt Virtual env..."
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python3-venv
else
  echo "✅ Virtual env đã được cài."
fi

SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(24))")

# --- yq ---
if ! command -v yq &> /dev/null; then
  echo "📝 Cài đặt yq (xử lý YAML)..."
  sudo wget -qO /usr/local/bin/yq https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64
  sudo chmod +x /usr/local/bin/yq
else
  echo "✅ yq đã được cài."
fi

# --- Docker ---
if ! dpkg -s docker-ce &> /dev/null; then
  echo "🐳 Cài đặt Docker..."

  sudo install -m 0755 -d /etc/apt/keyrings
  sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  sudo chmod a+r /etc/apt/keyrings/docker.asc

  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
    $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | \
    sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

  sudo DEBIAN_FRONTEND=noninteractive apt-get update
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
else
  echo "✅ Docker đã được cài."
fi

if ! command -v nc &> /dev/null; then
  echo "📡 Cài đặt netcat..."
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y netcat
else
  echo "✅ netcat đã được cài."
fi

# --- Kiểm tra ---
echo
echo "Kiểm tra package"
echo "🔍 Phiên bản kiểm tra:"
git --version || echo "Git ❌"
nginx -v || echo "Nginx ❌"
yq --version || echo "yq ❌"
docker --version || echo "Docker ❌"
docker compose version || echo "Compose plugin ❌"
python3 --version || echo "Python ❌"

# --- xử lý pull code ---
echo
echo "Pull code"
REPO_URL="https://github.com/bach-long/getvideo-public.git"

if [ ! -d "$TARGET_DIR" ]; then
  echo "📥 Thư mục chưa tồn tại, đang clone từ git..."
  git clone "$REPO_URL" "$TARGET_DIR"
else
  echo "✅ Thư mục đã tồn tại, bỏ qua git clone."
fi

# --- xử lý port ---
echo
echo "Chọn cổng cho ứng dụng Flask"
cd "$TARGET_DIR" || { echo "Thư mục không tồn tại!"; exit 1; }

PORT_FILE="$TARGET_DIR/port.conf"
if [[ -f "$PORT_FILE" ]]; then
  NEW_PORT=$(cat "$PORT_FILE")
  echo "Đọc lại cổng đã lưu: $NEW_PORT"
else
  NEW_PORT=$(find_free_port 5000)
  echo "$NEW_PORT" > "$PORT_FILE"
  echo "Lưu cổng $NEW_PORT vào $PORT_FILE"
fi

if [ -z "$NEW_PORT" ]; then
  echo "❌ Không tìm được port phù hợp!"
  exit 1
fi

echo
echo "Nhập thông tin env"
cat > "$TARGET_DIR/.env" <<EOF
ACCESS_TOKEN=
USER_TOKEN=
APP_TOKEN=
APP_ID=$APP_ID
APP_SECRET=$APP_SECRET
SECRET_KEY=$SECRET_KEY
TOKEN_TELEGRAM_BOT=
APP_NAME=$APP_NAME
PASSWORD_DB=password123456
NAME_DB=video
USER_DB=admin
ADDRESS_DB=127.0.0.1
EMAIL=chungtrinh2k2@gmail.com
ADDRESS=147 Thái Phiên, Phường 9, Quận 11, TP.HCM, Việt Nam
PHONE_NUMBER=07084773586
DNS_WEB=$DNS_WEB
COMPANY_NAME=CÔNG TY TNHH NOIR STEED
TAX_NUMBER=0318728792
EOF

echo
echo "Tạo mạng dùng chung giữa các container"
if ! docker network ls --format '{{.Name}}' | grep -q '^shared-net$'; then
  echo "🔧 Mạng shared-net chưa tồn tại, tạo mới..."
  docker network create shared-net
else
  echo "✅ Mạng shared-net đã tồn tại."
fi

echo
echo "Tạo file docker compose cho mysql"
cat > "/home/docker-compose.yml" <<EOF
version: "3"
services:
  db:
    image: mysql:8.0
    container_name: mysql_db
    restart: always
    environment:
      MYSQL_ROOT_PASSWORD: password123456
      MYSQL_DATABASE: video
      MYSQL_USER: admin
      MYSQL_PASSWORD: password123456
    expose:
      - 3306
    ports:
      - "3306:3306"
    volumes:
      - /tmp/app/mysqld:/run/mysqld
      - db_data:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      timeout: 20s
      retries: 10
    networks:
      - shared-net

volumes:
  db_data:

networks:
  shared-net:
    external: true
EOF

echo "✅ File docker-compose.yml đã được tạo tại: /home/docker-compose.yml"

echo
echo "Tạo file cấu hình nginx"
CONFIG_FILE="/etc/nginx/sites-enabled/$DNS_WEB"
cat > "$CONFIG_FILE" <<EOF
server {
    server_name $DNS_WEB;

    location / {
        if (\$query_string ~* "union.*select.*\\(") {
                return 403;
        }
        if (\$query_string ~* "select.+from") {
                return 403;
        }
        if (\$query_string ~* "insert\\s+into") {
                return 403;
        }
        if (\$query_string ~* "drop\\s+table") {
                return 403;
        }
        if (\$query_string ~* "information_schema") {
                return 403;
        }
        if (\$query_string ~* "sleep\\((\\s*)(\\d*)(\\s*)\\)") {
                return 403;
        }
        proxy_pass http://127.0.0.1:$NEW_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# --- Certbot ---
if [ -d "/home/certbotEnv" ]; then
  echo "Folder tồn tại"
  source /home/certbotEnv/bin/activate
else
  python3 -m venv /home/certbotEnv
  source /home/certbotEnv/bin/activate
  pip install certbot-nginx
  pip install certbot
fi
echo "✅ Certbot đã được cài."

echo
echo "Cấu hình certbot"
if [ -f "$CONFIG_FILE" ]; then
  echo "⚙️ File cấu hình $CONFIG_FILE tồn tại, chạy Certbot..."
  sudo /home/certbotEnv/bin/certbot --nginx -d "$DNS_WEB" --non-interactive --agree-tos --email nguyenbach19122002@gmail.com
  sudo /home/certbotEnv/bin/certbot renew
else
  echo "❌ File cấu hình $CONFIG_FILE không tồn tại, bỏ qua Certbot."
fi

deactivate
echo "✅ Certbot đã kích hoạt"

echo
echo "Chạy docker"
echo "1 chạy mysql"
cd /home
db_container_count=$(docker ps -a --filter "name=mysql_db" --format "{{.Names}}" | wc -l)

if [ "$db_container_count" -eq 1 ] && nc -z 127.0.0.1 3306; then
  echo "✅ MySQL đang chạy trên port 3306."
else
  echo "🚀 Khởi động MySQL container..."
  docker compose up -d --build
fi

# Lặp cho đến khi MySQL sẵn sàng
while ! ( [ "$(docker ps -a --filter "name=mysql_db" --format "{{.Names}}" | wc -l)" -eq 1 ] && docker exec mysql_db mysqladmin ping -u root -p"password123456" --silent 2>/dev/null | grep -q "mysqld is alive" ); do
  echo "⏳ Đang chờ MySQL container khởi động và mở cổng 3306..."
  sleep 4
done

if nc -zv 127.0.0.1 "$NEW_PORT"; then
  echo "Đã có app chạy ở cổng này"
  exit 1
else
  echo "MySQL container đã sẵn sàng..."
  echo "🚀 Khởi động ứng dụng..."
  if [ -d "/home/myenv" ]; then
    echo "Folder tồn tại"
  else
    python3 -m venv /home/myenv
  fi
  echo "Tạo folder virtual env thành công"
  source /home/myenv/bin/activate
  if [ $? -eq 0 ]; then
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y pkg-config default-libmysqlclient-dev build-essential
    export TZ=Asia/Ho_Chi_Minh
    echo "Lệnh chạy thành công"
    cd "$TARGET_DIR"
    #pip install --upgrade pip
    pip install -r requirements.txt
    flask db upgrade &&
    nohup bash -c "stdbuf -oL -eL flask run --host=0.0.0.0 --port=$NEW_PORT 2>&1 | ts '[%Y-%m-%d %H:%M:%S]'" >> flask.log &
    disown
    echo "✅ Flask started trên port $NEW_PORT"
    exit 0
  else
    echo "Lệnh thất bại"
  fi

  sleep 5
  if ! nc -zv 127.0.0.1 "$NEW_PORT"; then
      echo "Flask app failed to start on port $NEW_PORT"
      exit 1
  fi
fi
