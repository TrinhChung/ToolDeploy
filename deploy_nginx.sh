DNS_WEB="$1"
PORT="$2"

#!/bin/bash
set -e
set -o pipefail
trap 'echo "❌ Đã xảy ra lỗi tại dòng $LINENO. Dừng cài đặt."' ERR

# --- Nginx ---
if ! dpkg -s nginx &> /dev/null; then
  echo "🌐 Cài đặt Nginx..."
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y nginx
else
  echo "✅ Nginx đã được cài."
fi

# --- Git ---
if ! dpkg -s git &> /dev/null; then
  echo "🧰 Cài đặt Git..."
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y git
else
  echo "✅ Git đã được cài."
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

# --- Node.js 18 ---
if ! command -v node &>/dev/null || [[ "$(node -v)" != v18* ]]; then
  echo "🟩 Đang cài đặt Node.js 18.x..."
  curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y nodejs
else
  echo "✅ Node.js $(node -v) đã được cài."
fi

# --- Certbot cài trong myenv ---
if [ -d "/home/myenv" ]; then
  echo "Virtual env đã tồn tại: /home/myenv"
else
  python3 -m venv /home/myenv
  echo "Tạo folder virtual env /home/myenv thành công"
fi

source /home/myenv/bin/activate
pip show certbot &>/dev/null || pip install certbot
pip show certbot-nginx &>/dev/null || pip install certbot-nginx
echo "✅ Certbot và certbot-nginx đã được cài trong myenv."

# --- Kiểm tra ---
echo
echo "Kiểm tra package"
echo "🔍 Phiên bản kiểm tra:"
nginx -v || echo "Nginx ❌"
certbot --version || echo "Certbot ❌"

echo
echo "Tạo file cấu hình nginx"
CONFIG_FILE="/etc/nginx/sites-enabled/$DNS_WEB"
cat > "$CONFIG_FILE" <<EOF
server {
    server_name $DNS_WEB;

    location / {
        if (\$query_string ~* "union.*select.*\\(") { return 403; }
        if (\$query_string ~* "select.+from") { return 403; }
        if (\$query_string ~* "insert\\s+into") { return 403; }
        if (\$query_string ~* "drop\\s+table") { return 403; }
        if (\$query_string ~* "information_schema") { return 403; }
        if (\$query_string ~* "sleep\\((\\s*)(\\d*)(\\s*)\\)") { return 403; }
        proxy_pass http://127.0.0.1:$PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

sudo nginx -t && sudo systemctl reload nginx

echo
echo "Cấu hình certbot"
if [ -f "$CONFIG_FILE" ]; then
  echo "⚙️ File cấu hình $CONFIG_FILE tồn tại, chạy Certbot..."
  certbot --nginx -d "$DNS_WEB" --non-interactive --agree-tos --email nguyenbach19122002@gmail.com
  certbot renew
else
  echo "❌ File cấu hình $CONFIG_FILE không tồn tại, bỏ qua Certbot."
fi

deactivate
echo "✅ Certbot đã kích hoạt"
