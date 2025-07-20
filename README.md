## 🐍 1. Tạo môi trường ảo `myenv`

```bash
python3 -m venv myenv
```

---

## ▶️ 2. Kích hoạt môi trường ảo

**Linux / macOS:**

```bash
source myenv/bin/activate
```

**Windows (CMD):**

```cmd
myenv\Scripts\activate
```

**Windows (PowerShell):**

```powershell
myenv\Scripts\Activate.ps1
```

---

## ❌ 3. Tắt môi trường ảo

```bash
deactivate
```

---

## 📦 4. Cài Flask và các package cần thiết

```bash
pip install -r requirements.txt
```

Nếu chưa có file `requirements.txt`, cài thủ công:

```bash
pip install Flask Flask-Login Flask-WTF Flask-Migrate Flask-SQLAlchemy python-dotenv
```

Sau đó lưu lại:

```bash
pip freeze > requirements.txt
```

---

## 🔑 5. Tạo SECRET\_KEY cho ứng dụng

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Copy kết quả và dán vào file `.env` (hoặc cấu hình Flask):

```env
SECRET_KEY=... # Dán key vừa sinh ra ở đây
```

---

## 🗄️ 6. Khởi tạo và migrate database

Lần đầu tiên khởi tạo migration:

```bash
flask db init
```

Mỗi lần thay đổi models:

```bash
flask db migrate -m "Mô tả thay đổi"
flask db upgrade
```

---

## 🚀 7. Chạy ứng dụng Flask

**Cách 1: Chạy trực tiếp bằng Python**

```bash
python app.py
```

**Cách 2: Dùng lệnh flask run**

```bash
# Linux/macOS
export FLASK_APP=app.py
# Windows CMD
set FLASK_APP=app.py
# PowerShell
$env:FLASK_APP = "app.py"

flask run
```

> Mặc định truy cập ở: [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## 🔥 8. Bật chế độ debug (tùy chọn)

```bash
# Linux/macOS
export FLASK_DEBUG=1
# Windows CMD
set FLASK_DEBUG=1
# PowerShell
$env:FLASK_DEBUG = "1"
```

---

## 📋 9. Lưu ý

* Thường xuyên cập nhật các thư viện đã cài vào `requirements.txt` bằng:

  ```bash
  pip freeze > requirements.txt
  ```
* Đảm bảo thư mục migrations/ tồn tại sau khi chạy `flask db init`.
* SECRET\_KEY phải giữ bí mật và không commit lên git/public repo.

