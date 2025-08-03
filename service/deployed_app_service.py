# service/deployed_app_service.py

import secrets
from database_init import db
from models.deployed_app import DeployedApp
from models.server import Server
from models.domain import Domain
from models.domain_verification import DomainVerification
from util.cloud_flare import (
    check_dns_record_exists,
    add_dns_record,
    get_record_id_by_name,
    update_dns_record,
    add_or_update_txt_record,
)
from bash_script.remote_deploy import run_remote_deploy, remote_turn_off


def build_env_text(form, dns_web, app_secret):
    return (
        f"APP_ID={form.APP_ID.data}\n"
        f"APP_SECRET={form.APP_SECRET.data}\n"
        f"SECRET_KEY={app_secret}\n"
        f"APP_NAME={form.APP_NAME.data}\n"
        f"EMAIL={form.EMAIL.data}\n"
        f"ADDRESS={form.ADDRESS.data}\n"
        f"PHONE_NUMBER={form.PHONE_NUMBER.data}\n"
        f"DNS_WEB={dns_web}\n"
        f"COMPANY_NAME={form.COMPANY_NAME.data}\n"
        f"TAX_NUMBER={form.TAX_NUMBER.data}"
    )


def create_deployed_app(form, dns_web, env_text):
    subdomain = form.subdomain.data.strip() or None
    deployed_app = DeployedApp(
        server_id=form.server_id.data,
        domain_id=form.domain_id.data,
        subdomain=subdomain,
        env=env_text,
        note=form.note.data,
        status="deploying",
    )
    db.session.add(deployed_app)
    db.session.commit()
    db.session.refresh(deployed_app)
    return deployed_app


def create_dns_record_if_needed(subdomain, domain, server, logger, flash):
    if not subdomain:
        return True
    cf_account = domain.cloudflare_account
    record_name = f"{subdomain}.{domain.name}"
    try:
        exists = check_dns_record_exists(
            zone_id=domain.zone_id, subdns=record_name, cf_account=cf_account
        )
        if exists:
            logger.warning(f"Warning:  Bản ghi A {record_name} đã tồn tại.")
            flash(f"Warning:  Bản ghi A {record_name} đã tồn tại.", "danger")
            return False
        add_dns_record(
            zone_id=domain.zone_id,
            record_name=record_name,
            record_content=server.ip,
            record_type="A",
            ttl=3600,
            proxied=False,
            cf_account=cf_account,
        )
        logger.info(f"Success:  Đã tạo bản ghi A: {record_name} → {server.ip}")
        return True
    except Exception as e:
        logger.error(f"Error:   Lỗi khi tạo bản ghi A: {str(e)}")
        flash(f"Lỗi tạo bản ghi DNS: {e}", "danger")
        return False


def add_or_update_domain_verification(app, txt_value):
    verification = DomainVerification.query.filter_by(deployed_app_id=app.id).first()
    if verification:
        verification.txt_value = txt_value
        verification.create_count += 1
    else:
        verification = DomainVerification(
            deployed_app_id=app.id,
            txt_value=txt_value,
            create_count=1,
        )
        db.session.add(verification)
    app.status = "add_txt"
    db.session.commit()
    db.session.refresh(app)
    db.session.expire_all()
    return verification


def stop_app_and_update(app, server, logger):
    out = remote_turn_off(
        host=server.ip,
        user=server.admin_username,
        password=server.admin_password,
        subdomain=app.subdomain,
    )
    app.status = "inactive"
    app.log = out
    logger.info(f"Tắt app thành công:\n{out}")
    db.session.commit()
    db.session.refresh(app)
    db.session.expire_all()
    return out
