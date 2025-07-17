# Sử dụng Python 3.10 làm base image tối ưu (hỗ trợ Slim và Debian Bookworm)
FROM python:3.10-slim-bookworm

# Đặt thư mục làm việc
WORKDIR /app

# Cài đặt các gói hệ thống cần thiết và làm sạch bộ nhớ cache sau khi cài đặt
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    libmariadb-dev \
    pkg-config \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Sao chép và cài đặt các thư viện Python trước để tận dụng cache layer
COPY requirements.txt requirements.txt

# Cài đặt các thư viện Python từ file requirements.txt với tối ưu hóa
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Sao chép toàn bộ mã nguồn vào container (sau khi đã cài đặt dependencies)
COPY . .

# Cài đặt môi trường runtime cho Flask
ENV FLASK_ENV=development \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Thiết lập cổng chạy ứng dụng
EXPOSE 5000

# Lệnh chạy ứng dụng Flask với auto-reload cho môi trường phát triển
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
