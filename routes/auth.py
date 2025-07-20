from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from database_init import db
from models.user import User
from Form.forms import RegisterForm
from Form.login import LoginForm

auth_bp = Blueprint("auth", __name__)


# Đăng ký
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        # Kiểm tra trùng username/email
        if User.query.filter_by(username=form.username.data).first():
            flash("Tên đăng nhập đã tồn tại!", "danger")
            return render_template("register.html", form=form)
        if User.query.filter_by(email=form.email.data).first():
            flash("Email đã được sử dụng!", "danger")
            return render_template("register.html", form=form)
        # Hash password
        hashed_password = generate_password_hash(form.password.data)
        # Tài khoản đăng ký mới, chờ duyệt (is_active=False), is_admin=False mặc định
        new_user = User(
            username=form.username.data,
            email=form.email.data,
            password=hashed_password,
            is_active=False,  # Chờ admin duyệt
            is_admin=False,  # Mặc định không phải admin
        )
        db.session.add(new_user)
        db.session.commit()
        flash(
            "Đăng ký thành công! Vui lòng chờ quản trị viên duyệt tài khoản.", "success"
        )
        return redirect(url_for("auth.login"))
    return render_template("register.html", form=form)


# Đăng nhập
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            # Kiểm tra trạng thái duyệt tài khoản
            if not user.is_active:
                flash("Tài khoản của bạn chưa được duyệt bởi quản trị viên.", "warning")
                return render_template("login.html", form=form)
            login_user(user, remember=form.remember_me.data)
            flash("Đăng nhập thành công!", "success")
            # Tùy bạn muốn chuyển admin sang trang quản trị riêng
            # if user.is_admin:
            #     return redirect(url_for('admin.dashboard'))
            return redirect(url_for("home.home"))  # Chỉnh lại URL trang chính của bạn
        else:
            flash("Tên đăng nhập hoặc mật khẩu không đúng.", "danger")
    return render_template("login.html", form=form)


# Đăng xuất
@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Đã đăng xuất.", "success")
    return redirect(url_for("auth.login"))
