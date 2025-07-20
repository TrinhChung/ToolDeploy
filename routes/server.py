from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import current_user, login_required
from database_init import db
from models.server import Server
from Form.server_form import ServerForm 

server_bp = Blueprint("server", __name__, url_prefix="/server")


# Xem danh sách server (admin thấy tất cả, user thường chỉ thấy info cơ bản)
@server_bp.route("/servers")
@login_required
def server_list():
    servers = Server.query.all()
    return render_template(
        "server/server_list.html", servers=servers, is_admin=current_user.is_admin
    )


# Thêm server (chỉ admin)
@server_bp.route("/server/add", methods=["GET", "POST"])
@login_required
def add_server():
    if not current_user.is_admin:
        abort(403)
    # Gán giá trị mặc định cho các trường cố định
    default_values = {
        "admin_username": "root",
        "db_name": "video",
        "db_user": "chungtv",
        "db_password": "quantri8080",
    }
    form = ServerForm(
        admin_username=default_values["admin_username"],
        db_name=default_values["db_name"],
        db_user=default_values["db_user"],
        db_password=default_values["db_password"],
    )
    if form.validate_on_submit():
        server = Server(
            name=form.name.data,
            ip=form.ip.data,
            admin_username=default_values["admin_username"],
            admin_password=form.admin_password.data,  # Cho nhập riêng password SSH quản trị
            db_name=default_values["db_name"],
            db_user=default_values["db_user"],
            db_password=default_values["db_password"],
            note=form.note.data,
        )
        db.session.add(server)
        db.session.commit()
        flash("Thêm server thành công!", "success")
        return redirect(url_for("server.server_list"))
    return render_template(
        "server/server_add.html", form=form, default_values=default_values
    )


# Sửa server (chỉ admin, không cho sửa trường nhạy cảm qua giao diện này)
@server_bp.route("/server/edit/<int:server_id>", methods=["GET", "POST"])
@login_required
def edit_server(server_id):
    if not current_user.is_admin:
        abort(403)
    server = Server.query.get_or_404(server_id)
    form = ServerForm(obj=server)
    if form.validate_on_submit():
        server.name = form.name.data
        server.ip = form.ip.data
        server.note = form.note.data
        db.session.commit()
        flash("Cập nhật server thành công!", "success")
        return redirect(url_for("server.server_list"))
    return render_template("server/server_edit.html", form=form, server=server)


# Xóa server (chỉ admin, không cho xóa nếu có app đã deploy)
@server_bp.route("/server/delete/<int:server_id>", methods=["POST"])
@login_required
def delete_server(server_id):
    if not current_user.is_admin:
        abort(403)
    server = Server.query.get_or_404(server_id)
    if server.deployed_apps:
        flash("Server đang có app đã deploy, không thể xóa.", "danger")
        return redirect(url_for("server.server_list"))
    db.session.delete(server)
    db.session.commit()
    flash("Đã xóa server!", "success")
    return redirect(url_for("server.server_list"))


# Xem chi tiết server (admin xem hết, user chỉ xem thông tin an toàn)
@server_bp.route("/server/<int:server_id>")
@login_required
def server_detail(server_id):
    server = Server.query.get_or_404(server_id)
    return render_template(
        "server/server_detail.html", server=server, is_admin=current_user.is_admin
    )
