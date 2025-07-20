# routes/domain.py
from flask import Blueprint, render_template, redirect, url_for, flash, abort, request
from flask_login import login_required, current_user
from database_init import db
from util.cloud_flare import sync_domains_from_cf, add_dns_record, get_dns_records
from models.domain import Domain
from Form.domain_form import DomainForm      # form chỉ cho admin

domain_bp = Blueprint("domain", __name__, url_prefix="/domain")


# Danh sách domain – ai đăng nhập cũng xem được
@domain_bp.route("/list")
@login_required
def list_domain():
    domains = Domain.query.all()
    return render_template("domain/domain_list.html",
                           domains=domains,
                           is_admin=current_user.is_admin)

# Thêm domain – chỉ admin
@domain_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_domain():
    if not current_user.is_admin:
        abort(403)
    form = DomainForm()
    if form.validate_on_submit():
        # Gọi util tạo zone + lưu DB
        res = sync_domains_from_cf()  # hoặc create_cloudflare_zone(form.name.data)
        flash("Đã thêm domain!", "success")
        return redirect(url_for("domain.list_domain"))
    return render_template("domain/domain_add.html", form=form)


# routes/domain.py
@domain_bp.route("/sync")
@login_required
def sync_cf():
    if not current_user.is_admin:
        abort(403)
    try:
        sync_domains_from_cf()
        flash("Đã đồng bộ domain từ Cloudflare.", "success")
    except Exception as e:
        flash(str(e), "danger")
    return redirect(url_for("domain.list_domain"))
