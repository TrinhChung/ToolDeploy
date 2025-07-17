## 🐍 1. Tạo môi trường ảo `myenv`

```bash
python3 -m venv myenv
```

## ▶️ 2. Kích hoạt môi trường ảo

* **Linux / macOS:**

```bash
source myenv/bin/activate
```

* **Windows (CMD):**

```cmd
myenv\Scripts\activate.bat
```

* **Windows (PowerShell):**

```powershell
myenv\Scripts\Activate.ps1
```

## ❌ 3. Tắt môi trường ảo
```bash
deactivate
```

---

## 📦 4. Cài Flask

```bash
pip install Flask
```

---
## 🚀 6. Chạy ứng dụng Flask

* **Cách 1: Chạy trực tiếp bằng Python**

```bash
python app.py
```

* **Cách 2: Dùng lệnh `flask run`**
```bash
# Linux/macOS
export FLASK_APP=app.py

# Windows CMD
set FLASK_APP=app.py

# PowerShell
$env:FLASK_APP = "app.py"

flask run
```

> Mặc định chạy ở: [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## 🔥 7. Bật chế độ debug (nếu cần)

```bash
# Linux/macOS
export FLASK_DEBUG=1

# Windows CMD
set FLASK_DEBUG=1

# PowerShell
$env:FLASK_DEBUG = "1"
```
pip freeze > requirements.txt

pip install -r requirements.txt

Tạo SECRET_KEY
python3 -c "import secrets; print(secrets.token_hex(32))"
