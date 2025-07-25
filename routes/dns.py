from flask import Blueprint, render_template, redirect, url_for, flash, abort, request
from flask_login import login_required, current_user
from database_init import db
from models.domain import Domain
from models.dns_record import DNSRecord
from util.cloud_flare import (
    add_dns_record,
    get_dns_records,
    delete_dns_record_cf,
)

dns_bp = Blueprint("dns", __name__, url_prefix="/dns")

# Xem DNS record của domain
@dns_bp.route("/<int:domain_id>")
@login_required
def dns_records(domain_id):
    domain = Domain.query.get_or_404(domain_id)
    records = DNSRecord.query.filter_by(domain_id=domain.id).all()
    return render_template(
        "dns/dns_list.html",
        domain=domain,
        records=records,
        is_admin=current_user.is_admin,
    )

# Đồng bộ DNS record từ Cloudflare (chỉ admin)
@dns_bp.route("/sync/<int:domain_id>")
@login_required
def sync_dns(domain_id):
    if not current_user.is_admin:
        abort(403)
    domain = Domain.query.get_or_404(domain_id)
    cf_account = domain.cloudflare_account
    if not cf_account:
        flash("Domain này chưa được liên kết với Cloudflare Account.", "danger")
        return redirect(url_for("dns.dns_records", domain_id=domain.id))
    try:
        get_dns_records(domain.zone_id, cf_account)
        flash("Đã đồng bộ bản ghi DNS từ Cloudflare.", "success")
    except Exception as e:
        flash(f"Lỗi khi đồng bộ DNS: {e}", "danger")
    return redirect(url_for("dns.dns_records", domain_id=domain.id))

# Thêm DNS record (chỉ admin)
@dns_bp.route("/add/<int:domain_id>", methods=["GET", "POST"])
@login_required
def add_dns(domain_id):
    if not current_user.is_admin:
        abort(403)
    domain = Domain.query.get_or_404(domain_id)
    cf_account = domain.cloudflare_account
    if not cf_account:
        flash("Domain này chưa được liên kết với Cloudflare Account.", "danger")
        return redirect(url_for("dns.dns_records", domain_id=domain.id))
    if request.method == "POST":
        record_type = request.form["record_type"]
        name = request.form["name"]
        content = request.form["content"]
        ttl = int(request.form.get("ttl", 3600))
        proxied = "proxied" in request.form
        try:
            add_dns_record(domain.zone_id, name, content, record_type, ttl, proxied, cf_account)
            # Sau khi thêm, đồng bộ lại để cập nhật DB local
            get_dns_records(domain.zone_id, cf_account)
            flash("Đã thêm bản ghi DNS!", "success")
        except Exception as e:
            flash(f"Lỗi khi thêm DNS: {e}", "danger")
        return redirect(url_for("dns.dns_records", domain_id=domain.id))
    return render_template("dns/dns_add.html", domain=domain)

# Xóa DNS record (chỉ admin)
@dns_bp.route("/delete/<int:record_id>", methods=["POST"])
@login_required
def delete_dns(record_id):
    if not current_user.is_admin:
        abort(403)
    record = DNSRecord.query.get_or_404(record_id)
    domain = Domain.query.get_or_404(record.domain_id)
    cf_account = domain.cloudflare_account
    if not cf_account:
        flash("Domain này chưa được liên kết với Cloudflare Account.", "danger")
        return redirect(url_for("dns.dns_records", domain_id=domain.id))
    try:
        # Xóa ở Cloudflare
        if record.record_id:
            delete_dns_record_cf(domain.zone_id, record.record_id, cf_account)
        # Xóa ở local DB
        db.session.delete(record)
        db.session.commit()
        get_dns_records(domain.zone_id, cf_account)
        flash("Đã xóa bản ghi DNS!", "success")
    except Exception as e:
        flash(f"Lỗi khi xóa DNS: {e}", "danger")
    return redirect(url_for("dns.dns_records", domain_id=domain.id))
