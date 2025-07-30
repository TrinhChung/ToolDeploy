import logging
from logging.handlers import RotatingFileHandler
import os


def setup_logging():
    # File log (nên dùng path tuyệt đối)
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "app.log")

    # Formatter cho cả file và console
    log_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # --- Logger gốc ---
    app_logger = logging.getLogger()
    app_logger.setLevel(logging.INFO)

    # Console handler (tránh add lặp)
    if not any(isinstance(h, logging.StreamHandler) for h in app_logger.handlers):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(log_formatter)
        app_logger.addHandler(console_handler)

    # --- Logger riêng cho cronjob (có thể dùng logger riêng nếu muốn phân loại) ---
    cronjob_logger = logging.getLogger("cronjob")
    cronjob_logger.setLevel(logging.INFO)

    # File handler (tránh add lặp)
    if not any(
        isinstance(h, RotatingFileHandler) and h.baseFilename == log_file
        for h in cronjob_logger.handlers
    ):
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5
        )
        file_handler.setFormatter(log_formatter)
        cronjob_logger.addHandler(file_handler)

    # Nếu muốn log cả Flask và blueprint vào file:
    if not any(
        isinstance(h, RotatingFileHandler) and h.baseFilename == log_file
        for h in app_logger.handlers
    ):
        file_handler_main = RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5
        )
        file_handler_main.setFormatter(log_formatter)
        app_logger.addHandler(file_handler_main)

    # Đảm bảo Flask không tự động double-log (nếu dùng Flask >2.3)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)


# --- Chạy hàm này 1 lần ở entrypoint (app.py/main.py) ---
# setup_logging()
