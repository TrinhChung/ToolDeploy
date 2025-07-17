#!/bin/bash

set -e  # Stop script khi có lỗi
#Cấu hình cập nhật an toàn — KHÔNG force, KHÔNG hỏi
export DEBIAN_FRONTEND=noninteractive
echo "🟢 Bắt đầu cài đặt môi trường cho Ubuntu 22.04..."
#Update đang có vài hộp thoại mở lên cần chú ý xử lí vì khi chạy bash thì sẽ k thể chọn như làm thủ công
# Cập nhật hệ thống
sudo apt update && sudo apt upgrade -y -o Dpkg::Options::="--force-confdef"

# Cài các công cụ cơ bản
sudo apt install -y python3 python3-pip python3-venv git nginx ufw curl gnupg lsb-release ca-certificates software-properties-common

# Kích hoạt firewall & mở cổng web
sudo ufw allow 'Nginx Full'
sudo ufw --force enable

# ----------------------------
# Cài Docker & Docker Compose
# ----------------------------
echo "🐳 Đang cài Docker CE & Docker Compose..."

# Thêm key Docker chính thức
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Thêm repo Docker
echo \
  "deb [arch=$(dpkg --print-architecture) \
  signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Cài Docker Engine + Plugin Compose v2
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io \
                    docker-buildx-plugin docker-compose-plugin

# Cho phép chạy Docker không cần sudo
sudo usermod -aG docker $USER

# Khởi động Docker
sudo systemctl enable docker
sudo systemctl start docker

# ----------------------------
echo "✅ Hoàn tất cài đặt:"
echo "   - Python 3, pip, venv"
echo "   - Git"
echo "   - NGINX"
echo "   - Docker + Docker Compose (plugin v2)"
echo ""
echo "🔁 Hãy đăng xuất và đăng nhập lại để Docker chạy không cần sudo."
