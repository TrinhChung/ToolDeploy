# service/deployed_app_service.py
import threading
import logging
from flask import (
    flash,
    current_app,
)
from sqlalchemy import and_
from database_init import db
from models.deployed_app import DeployedApp
from models.server import Server
from models.domain import Domain
from bash_script.remote_deploy import run_remote_deploy
from util.cloud_flare import (
    check_dns_record_exists,
    add_dns_record,
    get_record_id_by_name,
    update_dns_record,
)
from service.nginx_deploy_service import deploy_nginx_certbot_via_ssh
from util.constant import DEPLOYED_APP_STATUS

logger = logging.getLogger("deploy_logger")


def find_available_port(server_id: int) -> int:
    """Tìm port chưa được sử dụng trên server cụ thể."""
    selected_port = 5000
    used_ports = (
        DeployedApp.query
        .with_entities(DeployedApp.port)
        .filter(
            DeployedApp.server_id == server_id,
            DeployedApp.port.isnot(None),
        )
        .order_by(DeployedApp.port.asc())
        .all()
    )
    length = len(used_ports)
    if length > 0:
        if (used_ports[-1][0] - used_ports[0][0]) + 1 == length:
            selected_port = used_ports[-1][0] + 1
        else:
            for i in range(1, length):
                if used_ports[i][0] - used_ports[i - 1][0] > 1:
                    selected_port = used_ports[i - 1][0] + 1
                    break
    return selected_port


def background_deploy(
    app,
    deployed_app_id,
    server_id,
    form_data,
    input_dir,
    dns_web,
    selected_port=None,
):
    # Bắt mọi lỗi từ ngoài vào trong!
    try:
        with app.app_context():
            logger = logging.getLogger("deploy_logger")
            logger.info("===> Thread deploy START")

            # Tạo session mới cho thread (giải pháp triệt để nhất)
            session = (
                db.create_scoped_session()
                if hasattr(db, "create_scoped_session")
                else db.session
            )

            deployed_app = session.query(DeployedApp).get(deployed_app_id)
            server = session.query(Server).get(server_id)
            logger.info("Đã vào background_deploy, lấy được app và server")

            # Cập nhật port lên database trước khi deploy
            deployed_app.port = selected_port
            session.commit()
            session.refresh(deployed_app)
            print(f"Chọn port {selected_port}")
            try:
                log = deploy_nginx_certbot_via_ssh(
                    host=server.ip,
                    user=server.admin_username,
                    password=server.admin_password,
                    domain=dns_web,
                    port=selected_port,
                    local_script_path="./deploy_nginx.sh",
                    remote_script_path="/home/deploy_nginx.sh",
                )
                logger.info(f"Deploy thành công: {log}")
                deployed_app.status = DEPLOYED_APP_STATUS.active.value
                deployed_app.log = log

                if deployed_app.subdomain:
                    domain = session.query(Domain).get(deployed_app.domain_id)
                    cf_account = domain.cloudflare_account
                    zone_id = domain.zone_id
                    record_name = f"{deployed_app.subdomain}.{domain.name}"
                    record_id = get_record_id_by_name(
                        zone_id, record_name, "A", cf_account=cf_account
                    )
                    if record_id:
                        try:
                            update_dns_record(
                                zone_id=zone_id,
                                record_id=record_id,
                                record_name=record_name,
                                record_content=server.ip,
                                record_type="A",
                                proxied=True,
                                cf_account=cf_account,
                            )
                            logger.info(f"Đã cập nhật proxied=True cho {record_name}")
                        except Exception as e:
                            logger.error(f"Lỗi khi cập nhật proxied: {e}")

            except Exception as e:
                deployed_app.status = DEPLOYED_APP_STATUS.failed.value
                deployed_app.log = str(e)
                logger.error(f"Deploy lỗi: {str(e)}")
            finally:
                session.commit()
                session.refresh(deployed_app)
                session.close()
                logger.info(
                    f"App {deployed_app.id} đã được cập nhật trạng thái: {deployed_app.status}"
                )
    except Exception as e:
        # Print ra file riêng nếu logger chưa hoạt động!
        with open("/tmp/deploy_thread_fatal.log", "a") as f:
            f.write(f"Lỗi to nhất ở ngoài thread: {e}\n")
        import traceback

        traceback.print_exc()


def fill_default_env(form):
    form.EMAIL.data = "nguyenlieuxmdn@gmail.com"
    form.ADDRESS.data = "147 Thái Phiên, Phường 9, Quận 11, TP.HCM, Việt Nam"
    form.PHONE_NUMBER.data = "07084773586"
    form.COMPANY_NAME.data = "CÔNG TY TNHH NOIR STEED"
    form.TAX_NUMBER.data = "0318728792"


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
        status= DEPLOYED_APP_STATUS.deploying.value,
    )
    db.session.add(deployed_app)
    db.session.commit()
    db.session.refresh(deployed_app)
    return deployed_app


def create_dns_record_if_needed(subdomain, domain_name, domain, server):
    if not subdomain:
        return True
    cf_account = domain.cloudflare_account
    record_name = f"{subdomain}.{domain_name}"
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


def start_background_deploy(deployed_app, form, server, dns_web):
    input_dir = deployed_app.subdomain or f"app_{deployed_app.id}"
    selected_port = 8000
    deployed_app.port = selected_port
    
    db.session.commit()
    form_data = {
        "APP_ID": form.APP_ID.data,
        "APP_SECRET": form.APP_SECRET.data,
        "APP_NAME": form.APP_NAME.data,
        "EMAIL": form.EMAIL.data,
        "ADDRESS": form.ADDRESS.data,
        "PHONE_NUMBER": form.PHONE_NUMBER.data,
        "COMPANY_NAME": form.COMPANY_NAME.data,
        "TAX_NUMBER": form.TAX_NUMBER.data,
    }
    thread = threading.Thread(
        target=background_deploy,
        args=(
            current_app._get_current_object(),
            deployed_app.id,
            server.id,
            form_data,
            input_dir,
            dns_web,
            selected_port,
        ),
        daemon=True,
    )
    thread.start()
