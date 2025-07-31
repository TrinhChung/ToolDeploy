# Cấu trúc dự án

Dưới đây là mô tả chi tiết các thư mục và file chính trong repository.

| Đường dẫn | Mô tả |
|-----------|------|
| `app.py` | Điểm khởi tạo ứng dụng Flask, cấu hình và đăng ký blueprint |
| `database_init.py` | Tạo đối tượng `SQLAlchemy` dùng chung |
| `models/` | Chứa các model định nghĩa bảng dữ liệu |
| `routes/` | Các blueprint xử lý request và trả về template/API |
| `Form/` | Định nghĩa form với Flask‑WTF |
| `templates/` | Thư mục giao diện Jinja2 |
| `static/` | Tài nguyên tĩnh (CSS, JS, hình ảnh) |
| `seeder/` | Script tạo dữ liệu mẫu ban đầu |
| `bash_script/` | Script triển khai và thao tác từ xa |
| `Dockerfile`, `docker-compose.yml` | File container hóa và cấu hình chạy bằng Docker |

Ngoài ra repository còn có các file cấu hình như `.env.example`, `requirements.txt` để cài đặt thư viện cần thiết.
