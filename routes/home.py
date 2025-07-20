from flask import Blueprint, render_template

home_bp = Blueprint('home', __name__)

from flask import Blueprint, render_template
from flask_login import current_user

home_bp = Blueprint("home", __name__)


@home_bp.route("/")
def home():
    # List section cho trang chủ, dễ maintain và refactor
    home_sections = [
        {
            "title": "Quản lý Hệ Thống Server",
            "icon": "fa-server text-primary",
            "features": [
                {
                    "title": "Danh sách Server",
                    "desc": "Xem và quản lý các server đã có trong hệ thống.",
                    "icon": "fa-server",
                    "btn": "Quản lý Server",
                    "url": "/server/servers",
                    "btn_icon": "fa-database",
                    "admin_only": False,
                },
                {
                    "title": "Thêm Server mới",
                    "desc": "Thêm server mới vào hệ thống (Admin).",
                    "icon": "fa-plus-circle",
                    "btn": "Thêm Server",
                    "url": "/server/server/add",
                    "btn_icon": "fa-plus",
                    "admin_only": True,
                },
                {
                    "title": "App đã Deploy",
                    "desc": "Xem, quản lý và truy cập các app đã deploy.",
                    "icon": "fa-th-list",
                    "btn": "Danh sách App",
                    "url": "/deployed_app/list",
                    "btn_icon": "fa-list",
                    "admin_only": False,
                },
            ],
        },
        {
            "title": "Quản lý Domain & DNS",
            "icon": "fa-globe text-success",
            "features": [
                {
                    "title": "Danh sách Domain",
                    "desc": "Quản lý domain, cấu hình DNS từng domain.",
                    "icon": "fa-globe",
                    "btn": "Quản lý Domain",
                    "url": "/domain/list",
                    "btn_icon": "fa-cogs",
                    "admin_only": False,
                },
                {
                    "title": "Quản lý DNS",
                    "desc": "Thêm, sửa, xóa bản ghi DNS cho domain đã đăng ký.",
                    "icon": "fa-random",
                    "btn": "Quản lý DNS",
                    "url": "/dns/records",
                    "btn_icon": "fa-edit",
                    "admin_only": False,
                },
                {
                    "title": "Đồng bộ Domain Cloudflare",
                    "desc": "Admin đồng bộ domain hệ thống với Cloudflare.",
                    "icon": "fa-sync-alt",
                    "btn": "Đồng bộ domain",
                    "url": "/domain/sync",
                    "btn_icon": "fa-sync-alt",
                    "admin_only": True,
                },
            ],
        },
        {
            "title": "Quản lý Người Dùng & Quyền",
            "icon": "fa-users text-info",
            "features": [
                {
                    "title": "Quản lý User",
                    "desc": "Xem, chỉnh sửa, phân quyền người dùng (Admin).",
                    "icon": "fa-user-cog",
                    "btn": "Quản lý User",
                    "url": "/admin/manage_users",
                    "btn_icon": "fa-users-cog",
                    "admin_only": True,
                },
                {
                    "title": "Thông tin tài khoản",
                    "desc": "Quản lý thông tin tài khoản cá nhân.",
                    "icon": "fa-user",
                    "btn": "Thông tin cá nhân",
                    "url": "/profile",
                    "btn_icon": "fa-id-badge",
                    "admin_only": False,
                },
                {
                    "title": "Xem Logs",
                    "desc": "Xem nhật ký hoạt động hệ thống.",
                    "icon": "fa-list-alt",
                    "btn": "Xem Logs",
                    "url": "/admin/logs",
                    "btn_icon": "fa-clipboard-list",
                    "admin_only": True,
                },
            ],
        },
        {
            "title": "Legal & Policy",
            "icon": "fas fa-balance-scale text-success",
            "features": [
                {
                    "title": "Privacy Policy",
                    "desc": "Xem chính sách bảo mật và xử lý dữ liệu.",
                    "icon": "fas fa-shield-alt",
                    "btn": "View Policy",
                    "url": "/polices",
                    "btn_icon": "fas fa-file-contract",
                    "admin_only": False,
                },
                {
                    "title": "Permissions",
                    "desc": "Xem và quản lý quyền ứng dụng.",
                    "icon": "fas fa-key",
                    "btn": "View Permissions",
                    "url": "/permissions",
                    "btn_icon": "fas fa-lock",
                    "admin_only": False,
                },
            ],
        },
        {
            "title": "YouTube Tools",
            "icon": "fab fa-youtube text-danger",
            "features": [
                {
                    "title": "Download Video",
                    "desc": "Download video YouTube theo URL.",
                    "icon": "fas fa-download",
                    "btn": "Download Video",
                    "url": "/download-url",
                    "btn_icon": "fas fa-arrow-down",
                    "admin_only": False,
                },
                # Thêm các tool khác nếu cần...
            ],
        },
    ]

    return render_template("home.html", home_sections=home_sections)


@home_bp.route('/terms')
def terms():
    return "<h1>Terms and Conditions</h1>"

@home_bp.route('/polices')
def polices():
    return "<h1>Privacy Policies</h1>"
