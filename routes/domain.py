from flask import Blueprint, render_template, redirect, url_for, flash, abort, request
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import SelectField
from database_init import db
from models.domain import Domain
from models.cloudflare_acc import CloudflareAccount
from Form.domain_form import DomainForm  # form chỉ cho admin
from util.cloud_flare import create_cloudflare_zone

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
class AddDomainForm(DomainForm):
    cloudflare_account_id = SelectField("Cloudflare Account", coerce=int, validators=[], render_kw={"class": "form-select"})

@domain_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_domain():
    accounts = CloudflareAccount.query.all()
    form = AddDomainForm()
    # Gán choices cho select
    form.cloudflare_account_id.choices = [(a.id, f"{a.name} ({a.email})") for a in accounts]
    if form.validate_on_submit():
        domain_name = form.name.data.strip().lower()
        cloudflare_account_id = form.cloudflare_account_id.data
        # Kiểm tra trùng domain
        if Domain.query.filter_by(name=domain_name).first():
            flash("Domain này đã tồn tại trong hệ thống.", "danger")
            return render_template("domain/domain_add.html", form=form)
        # Lấy thông tin tài khoản Cloudflare
        cf_account = CloudflareAccount.query.get(cloudflare_account_id)
        if not cf_account:
            flash("Cloudflare Account không tồn tại!", "danger")
            return render_template("domain/domain_add.html", form=form)
        # Gọi Cloudflare API tạo zone (theo tài khoản đã chọn)
        response = create_cloudflare_zone(domain_name, cf_account)
        if response.get("success"):
            zone_id = response["result"]["id"]
            status = response["result"].get("status", "pending")
            domain = Domain(
                name=domain_name,
                zone_id=zone_id,
                status=status,
                cloudflare_account_id=cf_account.id
            )
            db.session.add(domain)
            db.session.commit()
            flash("Đã thêm domain mới và tạo zone trên Cloudflare thành công!", "success")
            return redirect(url_for("domain.list_domain"))
        else:
            error_msgs = []
            if "errors" in response:
                for e in response["errors"]:
                    error_msgs.append(f"Mã {e.get('code')}: {e.get('message')}")
            flash(
                "Không thể tạo domain trên Cloudflare: " + " | ".join(error_msgs),
                "danger",
            )
    return render_template("domain/domain_add.html", form=form)

# ====== Xác thực domain (chỉ admin) ======
@domain_bp.route("/verify/<int:domain_id>", methods=["GET", "POST"])
@login_required
def verify_domain(domain_id):
    if not current_user.is_admin:
        abort(403)
    domain = Domain.query.get_or_404(domain_id)
    nameservers = []
    if domain.cloudflare_account:
        # Lấy nameserver từ account nếu có
        nameservers = [domain.cloudflare_account.ns1, domain.cloudflare_account.ns2]
    else:
        # fallback mặc định
        nameservers = ["hank.ns.cloudflare.com", "karsyn.ns.cloudflare.com"]

    # Nameserver mặc định ở VN (ví dụ Tenten, có thể đổi lấy từ DB nếu muốn)
    current_nameservers = [
        "ns-b1.tenten.vn",
        "ns-b2.tenten.vn",
        "ns-b3.tenten.vn",
    ]
    form = DummyDeleteForm()  # Có CSRF cho nút xác thực nếu cần

    if request.method == "POST":
        # TODO: Có thể gọi hàm sync cho đúng account ở đây (nếu cần)
        flash("Chức năng đồng bộ domain đã chuyển sang trang quản lý Cloudflare Account.", "info")
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
