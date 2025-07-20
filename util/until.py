from urllib.parse import urlparse, parse_qs
from datetime import datetime
import urllib.parse
import re
import random
import string
import os
import nltk
from nltk.corpus import stopwords

# Tải stopwords lần đầu (chỉ cần chạy một lần)
nltk.download("stopwords")

# Tập hợp các từ nên bỏ qua
custom_blacklist = {
    "co",
    "co.",
    "company",
    "ltd",
    "ltd.",
    "inc",
    "inc.",
    "llc",
    "group",
    "&",
}

# Kết hợp stopwords của NLTK và blacklist tùy chỉnh
stop_words = set(stopwords.words("english")).union(custom_blacklist)


def generate_acronym(text):
    # Loại bỏ dấu câu và chuyển về chữ thường
    clean_text = text.translate(str.maketrans("", "", string.punctuation)).lower()
    words = clean_text.split()

    # Loại bỏ các từ nằm trong stop_words
    filtered = [word for word in words if word not in stop_words]

    # Tạo chữ cái đầu từ các từ còn lại
    acronym = "".join(word[0].upper() for word in filtered)
    return acronym


def extract_facebook_video_id(url):
    """
    Trích xuất ID video từ URL Facebook.
    :param url: URL video Facebook (ví dụ: https://www.facebook.com/watch/?v=919627969714758)
    :return: ID của video nếu tìm thấy, ngược lại trả về None.
    """
    try:
        # Phân tích URL
        parsed_url = urlparse(url)
        # Trích xuất các tham số truy vấn
        query_params = parse_qs(parsed_url.query)
        # Lấy giá trị tham số `v`
        video_id = query_params.get("v", [None])[0]
        return video_id
    except Exception as e:
        print(f"Đã xảy ra lỗi: {e}")
        return None


def extract_playlist_id(url):
    """
    Trích xuất ID playlist từ URL YouTube.
    Args:
        url: URL của playlist YouTube (ví dụ: https://www.youtube.com/playlist?list=PLE4UtJLkLkg9lAIX3PqBmpVT-NiuXfgx9)
    Returns:
        ID của playlist nếu tìm thấy, ngược lại trả về None
    """
    try:
        # Phân tích URL
        parsed_url = urlparse(url)
        # Trích xuất các tham số truy vấn
        query_params = parse_qs(parsed_url.query)
        # Lấy giá trị tham số 'list'
        playlist_id = query_params.get("list", [None])[0]
        return playlist_id
    except Exception as e:
        print(f"Đã xảy ra lỗi khi trích xuất playlist ID: {e}")
        return None


def generate_playlist_url(playlist_id):
    """
    Tạo URL playlist từ playlist ID.
    Args:
        playlist_id: ID của playlist YouTube (ví dụ: PLE4UtJLkLkg9lAIX3PqBmpVT-NiuXfgx9)
    Returns:
        URL của playlist.
    """
    try:
        # Tạo URL từ playlist_id
        url = f"https://www.youtube.com/playlist?list={playlist_id}"
        return url
    except Exception as e:
        print(f"Đã xảy ra lỗi khi tạo URL từ playlist ID: {e}")
        return None


def format_datetime(value, format="%Y-%m-%d %H:%M:%S"):
    if isinstance(value, datetime):
        return value.strftime(format)
    return value


def convert_to_mysql_datetime(dt):
    if dt:
        # Remove timezone information (if any) and format as string for MySQL
        return dt.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
    return None


def ensure_quoted(txt_value):
    if txt_value is None:
        return txt_value
    if not (txt_value.startswith('"') and txt_value.endswith('"')):
        return f'"{txt_value}"'
    return txt_value


def extract_base_domain(full_domain):
    """Lấy domain chính từ tên miền đầy đủ (FQDN)"""
    parts = full_domain.split(".")
    if len(parts) > 2:
        return ".".join(parts[-3:])  # Lấy phần cuối, giữ lại domain chính
    return full_domain


def fix_google_map_iframe(iframe_code, width="100%", height="200px"):
    """
    Chỉnh sửa width & height của iframe Google Maps để phù hợp với giao diện.
    - Mặc định width="100%" để fit vào cột footer.
    - Mặc định height="200px" để không chiếm quá nhiều diện tích.
    """
    if not iframe_code or "<iframe" not in iframe_code:
        return ""

    # Thay thế width và height trong iframe
    iframe_code = re.sub(r'width="\d+"', f'width="{width}"', iframe_code)
    iframe_code = re.sub(r'height="\d+"', f'height="{height}"', iframe_code)

    return iframe_code


def generate_google_maps_embed(address):
    base_url = "https://www.google.com/maps/embed/v1/place?q="
    encoded_address = urllib.parse.quote(address)
    return f'<iframe width="100%" height="200px" style="border:0" loading="lazy" allowfullscreen referrerpolicy="no-referrer-when-downgrade" src="{base_url}{encoded_address}"></iframe>'


def generate_random_string(length=8):
    """Tạo chuỗi ngẫu nhiên gồm chữ và số, mặc định 4 ký tự"""
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def get_random_images(folder_path, folder_name, num_images=4):
    """Hàm lấy ngẫu nhiên `num_images` ảnh từ thư mục `folder_path` và trả về đường dẫn dạng `images/folder/image`."""
    if not os.path.exists(folder_path):
        return []

    # Lọc danh sách file ảnh (đuôi mở rộng phổ biến)
    image_extensions = (".jpg", ".jpeg", ".png", ".gif", ".webp")
    images = [
        img for img in os.listdir(folder_path) if img.lower().endswith(image_extensions)
    ]

    # Nếu số ảnh ít hơn yêu cầu, lấy toàn bộ
    if len(images) <= num_images:
        return [f"images/{folder_name}/{img}" for img in images]

    # Chọn ngẫu nhiên `num_images` ảnh và định dạng đường dẫn
    return [f"images/{folder_name}/{img}" for img in random.sample(images, num_images)]


nltk.download("stopwords")

# Tập hợp các từ nên bỏ qua
custom_blacklist = {
    "co",
    "co.",
    "company",
    "ltd",
    "ltd.",
    "inc",
    "inc.",
    "llc",
    "group",
    "&",
}

# Kết hợp stopwords của NLTK và blacklist tùy chỉnh
stop_words = set(stopwords.words("english")).union(custom_blacklist)


def generate_acronym(text):
    # Loại bỏ dấu câu và chuyển về chữ thường
    clean_text = text.translate(str.maketrans("", "", string.punctuation)).lower()
    words = clean_text.split()

    # Loại bỏ các từ nằm trong stop_words
    filtered = [word for word in words if word not in stop_words]

    # Tạo chữ cái đầu từ các từ còn lại
    acronym = "".join(word[0].upper() for word in filtered)
    return acronym
