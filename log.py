import logging
from logging.handlers import RotatingFileHandler

# Thiết lập logging vào file
def setup_logging():
    # Cấu hình logger chính (Flask app)
    app_logger = logging.getLogger()
    app_logger.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()  # Hiển thị log ra console
    console_handler.setLevel(logging.INFO)
    app_logger.addHandler(console_handler)
    
    # Cấu hình logger riêng cho cronjob
    cronjob_logger = logging.getLogger('cronjob')
    cronjob_logger.setLevel(logging.INFO)
    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # File log với dung lượng tối đa 10MB và giữ lại tối đa 5 file
    log_file = './static/app.log'
    file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
    file_handler.setFormatter(log_formatter)
    cronjob_logger.addHandler(file_handler)