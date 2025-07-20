from flask import Blueprint, render_template, redirect, url_for, flash, abort, request
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from database_init import db
from util.cloud_flare import (
    sync_domains_from_cf,
    create_cloudflare_zone,
)
from models.domain import Domain
from Form.domain_form import DomainForm  # form chỉ cho admin


class DummyDeleteForm(FlaskForm):
    pass


domain_bp = Blueprint("domain", __name__, url_prefix="/domain")


# ====== Danh sách domain – ai đăng nhập cũng xem được ======
@domain_bp.route("/list")
@login_required
def list_domain():
    domains = Domain.query.all()
    form = DummyDeleteForm()  # 1 form duy nhất cho các nút xóa
    return render_template(
        "domain/domain_list.html",
        domains=domains,
        is_admin=current_user.is_admin,
        form=form,
    )


# ====== Thêm domain mới (chỉ admin) ======
@domain_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_domain():
    if not current_user.is_admin:
        abort(403)
    form = DomainForm()
    if form.validate_on_submit():
        domain_name = form.name.data.strip().lower()
        # Kiểm tra trùng domain
        if Domain.query.filter_by(name=domain_name).first():
            flash("Domain này đã tồn tại trong hệ thống.", "danger")
            return render_template("domain/domain_add.html", form=form)
        # Gọi Cloudflare API tạo zone
        response = create_cloudflare_zone(domain_name)
        if response.get("success"):
            zone_id = response["result"]["id"]
            status = response["result"].get("status", "pending")
            domain = Domain(name=domain_name, zone_id=zone_id, status=status)
            db.session.add(domain)
            db.session.commit()
            flash(
                "Đã thêm domain mới và tạo zone trên Cloudflare thành công!", "success"
            )
            return redirect(url_for("domain.list_domain"))
        else:
            # Hiện lỗi chi tiết từ Cloudflare
            error_msgs = []
            if "errors" in response:
                for e in response["errors"]:
                    error_msgs.append(f"Mã {e.get('code')}: {e.get('message')}")
            flash(
                "Không thể tạo domain trên Cloudflare: " + " | ".join(error_msgs),
                "danger",
            )
    return render_template("domain/domain_add.html", form=form)


# ====== Đồng bộ toàn bộ domain từ Cloudflare (chỉ admin) ======
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


# ====== Xác thực domain (chỉ admin) ======
@domain_bp.route("/verify/<int:domain_id>", methods=["GET", "POST"])
@login_required
def verify_domain(domain_id):
    if not current_user.is_admin:
        abort(403)
    domain = Domain.query.get_or_404(domain_id)
    # Nameserver Cloudflare (fix cứng, không cần API)
    nameservers = ["hank.ns.cloudflare.com", "karsyn.ns.cloudflare.com"]
    # Nameserver mặc định ở VN (ví dụ Tenten, có thể đổi lấy từ DB nếu muốn)
    current_nameservers = [
        "ns-b1.tenten.vn",
        "ns-b2.tenten.vn",
        "ns-b3.tenten.vn",
    ]
    form = DummyDeleteForm()  # Có CSRF cho nút xác thực nếu cần

    if request.method == "POST":
        # Đồng bộ lại status domain từ Cloudflare
        sync_domains_from_cf()
        domain = Domain.query.get(domain_id)
        if domain.status == "active":
            flash(f"✅ Domain {domain.name} đã được xác thực thành công!", "success")
        else:
            flash(
                f"⚠️ Domain {domain.name} vẫn đang ở trạng thái {domain.status.upper()}. Hãy kiểm tra lại nameserver và đợi vài phút!",
                "warning",
            )
        # Reload lại trang xác thực (giúp tránh submit lại)
        return redirect(url_for("domain.verify_domain", domain_id=domain.id))

    return render_template(
        "domain/domain_verify.html",
        domain=domain,
        nameservers=nameservers,
        current_nameservers=current_nameservers,
        form=form,
        status=domain.status,
    )


# ====== Xóa domain (chỉ admin) ======
@domain_bp.route("/delete/<int:domain_id>", methods=["POST"])
@login_required
def delete_domain(domain_id):
    if not current_user.is_admin:
        abort(403)
    domain = Domain.query.get_or_404(domain_id)
    # Xóa kèm DNS records nếu cascade chưa thiết lập
    for rec in domain.dns_records:
        db.session.delete(rec)
    db.session.delete(domain)
    db.session.commit()
    flash(f"Đã xóa domain {domain.name}!", "success")
    return redirect(url_for("domain.list_domain"))
