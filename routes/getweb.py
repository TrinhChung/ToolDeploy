import logging
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from database_init import db
from models.domain import Domain
from models.template import Template
from models.server import Server
from util.dns_helper import create_dns_record_if_needed
from service.genweb_service import (
    get_random_logo_url,
    create_company_from_form,
    create_website_from_form,
    get_websites_list,
    get_website_detail,
)
from service.nginx_deploy_service import (
    start_nginx_certbot_deploy_bg,
)  # <-- Import hàm deploy nginx

genweb_bp = Blueprint("genweb", __name__, url_prefix="/genweb")
logger = logging.getLogger("genweb_logger")


@genweb_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_website():
    if request.method == "POST":
        user_id = getattr(current_user, "id", None)
        subdomain = request.form.get("subdomain", "").strip()
        domain_id = request.form.get("domain_id")
        server_id = request.form.get("server_id")
        domain = Domain.query.get(domain_id)
        server = Server.query.get(server_id)

        if not domain or not server:
            flash("Thiếu thông tin domain hoặc server!", "danger")
            return redirect(url_for("genweb.create_website"))

        # Tạo DNS record nếu cần
        if not create_dns_record_if_needed(subdomain, domain, server):
            return redirect(url_for("genweb.create_website"))

        # Random logo nếu chưa upload
        logo_url = request.form.get("logo_url") or get_random_logo_url()
        # Tạo Company & Website
        company = create_company_from_form(request.form, logo_url, user_id)
        website = create_website_from_form(request.form, company.id, user_id)

        # ====== Tự động deploy nginx/certbot sau khi tạo website ======
        if subdomain:
            domain_full = f"{subdomain}.{domain.name}"
        else:
            domain_full = domain.name

        # Nếu bạn muốn lấy port động theo server, có thể truyền server.port thay cho 3000
        deploy_port = 3000

        # Gọi deploy nginx/certbot qua SSH (background, không block)
        start_nginx_certbot_deploy_bg(website.id, domain_full, port=deploy_port)

        flash("✅ Website và công ty đã được tạo thành công!", "success")
        logger.info(
            f"Website created: company_id={company.id}, server_id={server_id}, domain_id={domain_id}, template_id={request.form.get('template_id')}"
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
    websites = get_websites_list()
    return render_template("genweb/list_website.html", websites=websites)


@genweb_bp.route("/detail/<int:website_id>")
@login_required
def view_website(website_id):
    w = get_website_detail(website_id)
    if not w:
        flash("Website không tồn tại!", "danger")
        return redirect(url_for("genweb.list_website"))
    return render_template("genweb/detail_website.html", w=w)
