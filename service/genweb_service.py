# service/genweb_service.py

import os
import random
from database_init import db
from models.company import Company
from models.website import Website
from models.domain import Domain
from models.template import Template
from models.server import Server


def get_random_logo_url():
    logo_dir = os.path.join(os.getcwd(), "static", "images", "logo")
    if not os.path.exists(logo_dir):
        return ""
    logo_files = [f for f in os.listdir(logo_dir) if f.lower().endswith(".svg")]
    if logo_files:
        random_logo = random.choice(logo_files)
        return f"/static/images/logo/{random_logo}"
    return ""


def create_company_from_form(form, logo_url, user_id):
    company = Company(
        name=form.get("company_name"),
        address=form.get("address"),
        hotline=form.get("hotline"),
        email=form.get("email"),
        license_no=form.get("license_no", ""),
        google_map_embed=form.get("google_map_embed", ""),
        logo_url=logo_url,
        footer_text=form.get("footer_text", ""),
        description=form.get("description", ""),
        note=form.get("company_note", ""),
        user_id=user_id,
    )
    db.session.add(company)
    db.session.commit()
    return company


def create_website_from_form(form, company_id, user_id):
    website = Website(
        company_id=company_id,
        dns_record_id=form.get("dns_record_id"),
        template_id=form.get("template_id"),
        static_page_link=form.get("static_page_link", ""),
        note=form.get("website_note", ""),
        server_id=form.get("server_id"),
        user_id=user_id,
    )
    db.session.add(website)
    db.session.commit()
    return website


def get_websites_list():
    return (
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


def get_website_detail(website_id):
    return (
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
