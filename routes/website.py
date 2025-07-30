from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from database_init import db
from models.website import Website
from models.company import Company
from models.dns_record import DNSRecord
from models.template import Template
from models.domain import Domain

website_bp = Blueprint("website", __name__, url_prefix="/website")


@website_bp.route("/")
@login_required
def list_websites():
    """Hiển thị danh sách website của người dùng hiện tại."""
    websites = Website.query.filter_by(user_id=current_user.id).all()
    return render_template("website/list.html", websites=websites)


@website_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_website():
    companies = Company.query.filter_by(user_id=current_user.id).all()
    domains = Domain.query.filter_by().all()
    templates = Template.query.all()

    if request.method == "POST":
        company_id = request.form.get("company_id", type=int)
        domain_id = request.form.get("domain_id", type=int)
        subdomain = request.form.get("subdomain", "").strip().lower()
        template_id = request.form.get("template_id", type=int)
        static_page_link = request.form.get("static_page_link", "")
        note = request.form.get("note", "")

        if not company_id or not domain_id or not subdomain:
            flash("Vui lòng chọn công ty, domain và nhập subdomain.", "danger")
            return render_template(
                "website/add.html",
                companies=companies,
                domains=domains,
                templates=templates,
            )

        # Tìm domain
        domain = Domain.query.filter_by(id=domain_id).first()
        if not domain:
            flash("Domain không hợp lệ.", "danger")
            return render_template(
                "website/add.html",
                companies=companies,
                domains=domains,
                templates=templates,
            )

        # Tìm hoặc tạo mới DNSRecord
        # domain là object domain đã lấy từ db (theo domain_id)
        full_domain_name = f"{subdomain}.{domain.name}".lower()

        # Tìm xem đã tồn tại chưa TODO
        dns_record = DNSRecord.query.filter_by(name=full_domain_name, domain_id=domain.id).first()
        if not dns_record:
            dns_record = DNSRecord(
                name=full_domain_name,
                domain_id=domain.id,
                record_type="A",
                content="",  # Hoặc IP mặc định, hoặc để admin cập nhật sau
                ttl=3600
            )
            db.session.add(dns_record)
            db.session.commit()

        website = Website(
            company_id=company_id,
            dns_record_id=dns_record.id,
            template_id=template_id,
            static_page_link=static_page_link,
            note=note,
            user_id=current_user.id,
        )
        db.session.add(website)
        db.session.commit()
        flash("Đã tạo website thành công.", "success")
        return redirect(url_for("website.list_websites"))

    return render_template(
        "website/add.html",
        companies=companies,
        domains=domains,
        templates=templates,
    )

@website_bp.route("/delete/<int:website_id>", methods=["POST"])
@login_required
def delete_website(website_id):
    """Xóa website thuộc quyền sở hữu của người dùng."""
    website = Website.query.filter_by(id=website_id, user_id=current_user.id).first_or_404()
    db.session.delete(website)
    db.session.commit()
    flash("Đã xóa website.", "success")
    return redirect(url_for("website.list_websites"))
