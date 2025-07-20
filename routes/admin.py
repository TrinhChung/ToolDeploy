from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from models.user import User
from database_init import db

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# Trang quản lý user
@admin_bp.route("/users")
@login_required
def manage_users():
    if not current_user.is_admin:
        flash("Bạn không có quyền truy cập trang này!", "danger")
        return redirect(url_for("home.home"))  # hoặc về trang chủ
    users = User.query.all()
    return render_template("admin/manage_users.html", users=users)


# Duyệt user (active user)
@admin_bp.route("/users/activate/<int:user_id>")
@login_required
def activate_user(user_id):
    if not current_user.is_admin:
        flash("Bạn không có quyền thực hiện hành động này!", "danger")
        return redirect(url_for("admin.manage_users"))
    user = User.query.get_or_404(user_id)
    user.is_active = True
    db.session.commit()
    flash(f"Đã duyệt tài khoản {user.username}.", "success")
    return redirect(url_for("admin.manage_users"))


# Xóa user
@admin_bp.route("/users/delete/<int:user_id>")
@login_required
def delete_user(user_id):
    if not current_user.is_admin:
        flash("Bạn không có quyền thực hiện hành động này!", "danger")
        return redirect(url_for("admin.manage_users"))
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash(f"Đã xóa tài khoản {user.username}.", "success")
    return redirect(url_for("admin.manage_users"))
