PORT="$1"
DNS_WEB="$2"
#!/bin/bash

set -e  # Dừng nếu có lỗi
set -o pipefail

trap 'echo "❌ Đã xảy ra lỗi tại dòng $LINENO. Dừng cài đặt."' ERR

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

# --- Certbot ---
if ! dpkg -s certbot python3-certbot-nginx &> /dev/null; then
  echo "🔒 Cài đặt Certbot + plugin Nginx..."
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y certbot python3-certbot-nginx
else
  echo "✅ Certbot đã được cài."
fi

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
        if (\$query_string ~* "union.*select.*\(") {
                return 403;
        }
        if (\$query_string ~* "select.+from") {
                return 403;
        }
        if (\$query_string ~* "insert\s+into") {
                return 403;
        }
        if (\$query_string ~* "drop\s+table") {
                return 403;
        }
        if (\$query_string ~* "information_schema") {
                return 403;
        }
        if (\$query_string ~* "sleep\((\s*)(\d*)(\s*)\)") {
                return 403;
        }
        proxy_pass http://127.0.0.1:$PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

echo
echo "Cấu hình certbot"
if [ -f "$CONFIG_FILE" ]; then
  echo "⚙️ File cấu hình $CONFIG_FILE tồn tại, chạy Certbot..."
  sudo certbot --nginx -d "$DNS_WEB" --non-interactive --agree-tos --email nguyenbach19122002@gmail.com
  sudo certbot renew
	echo "🚀 Cấu hình đã được triển khai."
else
  echo "❌ File cấu hình $CONFIG_FILE không tồn tại, bỏ qua Certbot."
fi