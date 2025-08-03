import logging
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from database_init import db
from models.domain import Domain
from models.template import Template
from models.server import Server
from util.dns_helper import create_dns_record_if_needed
from models.website import Website
from models.company import Company
from util.cloud_flare import (
    check_dns_record_exists,
    get_record_id_by_name,
    update_dns_record,
)

from service.genweb_service import (
    get_random_logo_url,
    create_company_from_form,
    create_website_from_form,
    get_websites_list,
    get_website_detail,
)
from service.nginx_deploy_service import (
    start_nginx_certbot_deploy_bg,
)

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
        template_id = request.form.get("template_id")
        domain = Domain.query.get(domain_id)
        server = Server.query.get(server_id)
        template = Template.query.get(template_id) if template_id else None

        # --- Check exist on Cloudflare (not in DB) ---
        if subdomain:
            cf_account = domain.cloudflare_account
            record_name = f"{subdomain}.{domain.name}"
            try:
                exists = check_dns_record_exists(
                    zone_id=domain.zone_id, subdns=record_name, cf_account=cf_account
                )
                if exists:
                    flash("❌ Subdomain này đã tồn tại trên Cloudflare!", "danger")
                    logger.warning(
                        f"Phát hiện subdomain trùng (Cloudflare): zone_id={domain.zone_id}, subdomain={record_name}"
                    )
                    return redirect(url_for("genweb.create_website"))
            except Exception as e:
                flash("Không kiểm tra được trạng thái DNS, thử lại!", "danger")
                logger.error(f"Lỗi check DNS Cloudflare: {e}")
                return redirect(url_for("genweb.create_website"))

        if not domain or not server:
            flash("Thiếu thông tin domain hoặc server!", "danger")
            logger.error("Thiếu thông tin domain hoặc server khi tạo website.")
            return redirect(url_for("genweb.create_website"))

        # Create DNS record if needed
        if not create_dns_record_if_needed(subdomain, domain, server):
            logger.error("Lỗi khi tạo DNS record.")
            return redirect(url_for("genweb.create_website"))

        # Get logo or random logo
        logo_url = request.form.get("logo_url") or get_random_logo_url()
        company = create_company_from_form(request.form, logo_url, user_id)
        website = create_website_from_form(request.form, company.id, user_id)

        # ====== Auto deploy nginx/certbot after website creation ======
        if subdomain:
            domain_full = f"{subdomain}.{domain.name}"
        else:
            domain_full = domain.name

        # Get port from template or default 3000
        deploy_port = getattr(template, "port", None) or 3000

        # Deploy nginx/certbot via SSH (background)
        start_nginx_certbot_deploy_bg(website.id, domain_full, port=deploy_port)

        # ====== Update DNS Cloudflare: Enable proxy ======
        try:
            if subdomain:
                cf_account = domain.cloudflare_account
                zone_id = domain.zone_id
                record_id = get_record_id_by_name(
                    zone_id, record_name, "A", cf_account=cf_account
                )
                if record_id:
                    update_dns_record(
                        zone_id=zone_id,
                        record_id=record_id,
                        record_name=record_name,
                        record_content=server.ip,
                        record_type="A",
                        proxied=True,
                        cf_account=cf_account,
                    )
                    logger.info(f"Đã bật proxy cho record: {record_name}")
                else:
                    logger.warning(
                        f"Không tìm thấy record để update proxy: {record_name}"
                    )
        except Exception as e:
            logger.error(f"Lỗi khi update proxied Cloudflare: {str(e)}")

        flash("✅ Website và công ty đã được tạo thành công!", "success")
        logger.info(
            f"Đã tạo website mới: company_id={company.id}, server_id={server_id}, domain_id={domain_id}, template_id={template_id}, domain_full={domain_full}"
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


@genweb_bp.route("/detail/<int:website_id>", methods=["GET", "POST"])
@login_required
def view_website(website_id):
    if request.method == "POST":
        company_name = request.form.get("company_name", "").strip()
        address = request.form.get("address", "").strip()
        hotline = request.form.get("hotline", "").strip()
        email = request.form.get("email", "").strip()
        google_map_embed = request.form.get("google_map_embed", "").strip()

        website = Website.query.get(website_id)
        if not website:
            flash("Không tìm thấy website!", "danger")
            return redirect(url_for("genweb.list_website"))

        company = Company.query.get(website.company_id)
        if company:
            company.name = company_name
            company.address = address
            company.hotline = hotline
            company.email = email
            company.google_map_embed = google_map_embed
            db.session.commit()
            flash("Đã cập nhật thông tin công ty!", "success")
        else:
            flash("Không tìm thấy thông tin công ty!", "danger")

        return redirect(url_for("genweb.view_website", website_id=website_id))

    w = get_website_detail(website_id)
    if not w:
        flash("Website không tồn tại!", "danger")
        return redirect(url_for("genweb.list_website"))

    return render_template("genweb/detail_website.html", w=w)


@genweb_bp.route("/delete/<int:website_id>", methods=["POST"])
@login_required
def delete_website(website_id):
    website = Website.query.get(website_id)
    if not website:
        flash("Không tìm thấy website!", "danger")
        return redirect(url_for("genweb.list_website"))

    # --- Lấy domain và subdomain để xóa DNS ---
    domain = Domain.query.get(website.domain_id)
    if not domain:
        flash("Không tìm thấy domain!", "danger")
        return redirect(url_for("genweb.list_website"))
    cf_account = domain.cloudflare_account
    zone_id = domain.zone_id

    # Subdomain và tên bản ghi
    static_link = website.static_page_link  # VD: abc.example.com
    record_name = static_link  # nếu lưu full subdomain.domain.com

    # --- Xóa record A ---
    try:
        a_record_id = get_record_id_by_name(zone_id, record_name, "A", cf_account)
        if a_record_id:
            update_dns_record(
                zone_id,
                a_record_id,
                record_name,
                "",
                "A",
                proxied=False,
                cf_account=cf_account,
                delete=True,
            )
    except Exception as e:
        logger.error(f"Lỗi khi xóa record A: {e}")

    # --- Xóa record TXT ---
    try:
        txt_record_id = get_record_id_by_name(zone_id, record_name, "TXT", cf_account)
        if txt_record_id:
            update_dns_record(
                zone_id,
                txt_record_id,
                record_name,
                "",
                "TXT",
                proxied=False,
                cf_account=cf_account,
                delete=True,
            )
    except Exception as e:
        logger.error(f"Lỗi khi xóa record TXT: {e}")

    # --- Xóa website (và company nếu muốn) ---
    company = Company.query.get(website.company_id)
    db.session.delete(website)
    # Nếu muốn xóa cả công ty liên quan (cẩn thận chỉ xóa khi không còn website nào dùng chung công ty này!)
    if company:
        db.session.delete(company)
    db.session.commit()

    flash("✅ Đã xóa website và DNS thành công!", "success")
    return redirect(url_for("genweb.list_website"))
