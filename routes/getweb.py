import logging
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from database_init import db
from models.company import Company
from models.website import Website
from models.domain import Domain
from models.template import Template
from models.server import Server
import os
import random
from util.dns_helper import (
    create_dns_record_if_needed,
)  # <-- Import helper DNS đã chuẩn hoá

genweb_bp = Blueprint("genweb", __name__, url_prefix="/genweb")
logger = logging.getLogger("genweb_logger")


@genweb_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_website():
    if request.method == "POST":
        # --- Lấy thông tin công ty ---
        company_name = request.form.get("company_name")
        address = request.form.get("address")
        hotline = request.form.get("hotline")
        email = request.form.get("email")
        license_no = request.form.get("license_no", "")
        google_map_embed = request.form.get("google_map_embed", "")
        logo_url = request.form.get("logo_url", "")
        footer_text = request.form.get("footer_text", "")
        description = request.form.get("description", "")
        note = request.form.get("company_note", "")
        user_id = getattr(current_user, "id", None)

        # --- Thông tin Website ---
        server_id = request.form.get("server_id")
        dns_record_id = request.form.get("dns_record_id")
        template_id = request.form.get("template_id")
        static_page_link = request.form.get("static_page_link", "")
        website_note = request.form.get("website_note", "")
        subdomain = request.form.get("subdomain", "").strip()  # <-- cần cho DNS
        
        # --- Random logo SVG (nếu chưa upload từ form) ---
        logo_dir = os.path.join(os.getcwd(), 'static', 'images', 'logo')
        logo_files = [f for f in os.listdir(logo_dir) if f.lower().endswith('.svg')]
        logo_url = request.form.get("logo_url", "")
        if not logo_url and logo_files:
            random_logo = random.choice(logo_files)
            logo_url = f"/static/images/logo/{random_logo}"

        # --- Check thông tin domain/server ---
        domain = Domain.query.get(dns_record_id)
        server = Server.query.get(server_id)
        if not domain or not server:
            flash("Thiếu thông tin domain hoặc server!", "danger")
            return redirect(url_for("genweb.create_website"))

        # --- Tạo DNS record trên Cloudflare nếu có subdomain ---
        if not create_dns_record_if_needed(subdomain, domain, server):
            # Hàm sẽ tự flash thông báo lỗi
            return redirect(url_for("genweb.create_website"))

        # --- Tạo Company ---
        company = Company(
            name=company_name,
            address=address,
            hotline=hotline,
            email=email,
            license_no=license_no,
            google_map_embed=google_map_embed,
            logo_url=logo_url,
            footer_text=footer_text,
            description=description,
            note=note,
            user_id=user_id,
        )
        db.session.add(company)
        db.session.commit()

        # --- Tạo Website ---
        website = Website(
            company_id=company.id,
            dns_record_id=dns_record_id,
            template_id=template_id,
            static_page_link=static_page_link,
            note=website_note,
            server_id=server_id,
            user_id=user_id,
        )
        db.session.add(website)
        db.session.commit()
        flash("✅ Website và công ty đã được tạo thành công!", "success")
        logger.info(
            f"Website created: company_id={company.id}, server_id={server_id}, domain_id={dns_record_id}, template_id={template_id}"
        )
        return redirect(url_for("genweb.list_website"))

    dns_records = Domain.query.all()
    templates = Template.query.all()
    servers = Server.query.all()
    return render_template(
        "genweb/create_website.html",
        dns_records=dns_records,
        templates=templates,
        servers=servers,
    )


@genweb_bp.route("/list")
@login_required
def list_website():
    db.session.expire_all()
    # Lấy các trường cần hiển thị (id, company_name, static_page_link, server_name, server_ip)
    websites = (
        db.session.query(
            Website.id,
            Company.name.label("company_name"),
            Website.static_page_link.label("static_page_link"),
            Server.name.label("server_name"),
            Server.ip.label("server_ip"),
        )
        .join(Company, Website.company_id == Company.id)
        .join(Server, Website.server_id == Server.id)
        .order_by(Website.id.desc())
        .all()
    )
    # websites = [(id, company_name, static_page_link, server_name, server_ip), ...]
    return render_template("genweb/list_website.html", websites=websites)


@genweb_bp.route("/detail/<int:website_id>")
@login_required
def view_website(website_id):
    # Query JOIN các bảng liên quan, chỉ lấy đúng website_id
    w = (
        db.session.query(
            Website.id,
            Company.name.label("company_name"),
            Company.address,
            Company.hotline,
            Company.email,
            Company.license_no,
            Company.description,
            Company.footer_text,
            Company.google_map_embed,
            Website.static_page_link,
            Website.note,
            Domain.name.label("domain_name"),
            Template.name.label("template_name"),
            Server.name.label("server_name"),
            Server.ip.label("server_ip"),
        )
        .join(Company, Website.company_id == Company.id)
        .join(Domain, Website.dns_record_id == Domain.id)
        .join(Template, Website.template_id == Template.id)
        .join(Server, Website.server_id == Server.id)
        .filter(Website.id == website_id)
        .first()
    )
    if not w:
        flash("Website không tồn tại!", "danger")
        return redirect(url_for("genweb.list_website"))
    return render_template("genweb/detail_website.html", w=w)
