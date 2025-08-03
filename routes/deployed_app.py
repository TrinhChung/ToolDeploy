import secrets
import threading
import logging
from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    current_app,
)
from flask_login import login_required
from database_init import db
from models.deployed_app import DeployedApp
from models.server import Server
from models.domain import Domain
from Form.deploy_app_form import DeployAppForm
from bash_script.remote_deploy import run_remote_deploy, remote_turn_off, do_sync
from util.cloud_flare import (
    check_dns_record_exists,
    add_dns_record,
    get_record_id_by_name,
    update_dns_record,
    add_or_update_txt_record,
)
from models.domain_verification import DomainVerification

deployed_app_bp = Blueprint("deployed_app", __name__, url_prefix="/deployed_app")
logger = logging.getLogger("deploy_logger")


import logging
from database_init import db
  # đảm bảo có Session = scoped_session(sessionmaker(bind=engine))


def background_deploy(app, deployed_app_id, server_id, form_data, input_dir, dns_web):
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

            try:
                log = run_remote_deploy(
                    host=server.ip,
                    user=server.admin_username,
                    password=server.admin_password,
                    input_dir=input_dir,
                    appId=form_data["APP_ID"],
                    appSecret=form_data["APP_SECRET"],
                    appName=form_data["APP_NAME"],
                    email=form_data["EMAIL"],
                    address=form_data["ADDRESS"],
                    phoneNumber=form_data["PHONE_NUMBER"],
                    dnsWeb=dns_web,
                    companyName=form_data["COMPANY_NAME"],
                    taxNumber=form_data["TAX_NUMBER"],
                )
                logger.info(f"Deploy thành công: {log}")
                deployed_app.status = "active"
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
                deployed_app.status = "failed"
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
    form.EMAIL.data = "chungtrinh2k2@gmail.com"
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
        status="deploying",
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
            logger.warning(f"⚠️ Bản ghi A {record_name} đã tồn tại.")
            flash(f"⚠️ Bản ghi A {record_name} đã tồn tại.", "danger")
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
        logger.info(f"✅ Đã tạo bản ghi A: {record_name} → {server.ip}")
        return True
    except Exception as e:
        logger.error(f"❌ Lỗi khi tạo bản ghi A: {str(e)}")
        flash(f"Lỗi tạo bản ghi DNS: {e}", "danger")
        return False


def start_background_deploy(deployed_app, form, server, dns_web):
    input_dir = deployed_app.subdomain or f"app_{deployed_app.id}"
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
        ),
        daemon=True,
    )
    thread.start()


@deployed_app_bp.route("/deploy", methods=["GET", "POST"])
@login_required
def deploy_app():
    form = DeployAppForm()
    form.server_id.choices = [(s.id, s.name) for s in Server.query.all()]
    form.domain_id.choices = [(d.id, d.name) for d in Domain.query.all()]

    if form.validate_on_submit():
        domain_name = dict(form.domain_id.choices).get(form.domain_id.data)
        if not domain_name:
            flash("Domain không hợp lệ.", "danger")
            return redirect(url_for("deployed_app.deploy_app"))

        app_secret = secrets.token_hex(16)
        subdomain = form.subdomain.data.strip() or None
        dns_web = f"{subdomain}.{domain_name}" if subdomain else domain_name
        env_text = build_env_text(form, dns_web, app_secret)
        deployed_app = create_deployed_app(form, dns_web, env_text)

        domain = Domain.query.get(form.domain_id.data)
        server = Server.query.get(form.server_id.data)

        if not create_dns_record_if_needed(subdomain, domain_name, domain, server):
            return redirect(url_for("deployed_app.deploy_app"))

        start_background_deploy(deployed_app, form, server, dns_web)

        flash("🚀 Đang deploy... Vui lòng kiểm tra lại sau!", "info")
        return redirect(url_for("deployed_app.list_app"))

    return render_template("deployed_app/deploy_app.html", form=form)


@deployed_app_bp.route("/list")
@login_required
def list_app():
    # Luôn expire session để lấy dữ liệu mới nhất từ DB (tránh cache)
    db.session.expire_all()
    deployed_apps = (
        db.session.query(DeployedApp, Server, Domain)
        .join(Server, DeployedApp.server_id == Server.id)
        .join(Domain, DeployedApp.domain_id == Domain.id)
        .order_by(DeployedApp.created_at.desc())
        .all()
    )
    return render_template("deployed_app/list_app.html", deployed_apps=deployed_apps)

@deployed_app_bp.route("/sync")
@login_required
def sync():
    # Luôn expire session để lấy dữ liệu mới nhất từ DB (tránh cache)
    db.session.expire_all()
    servers = (
        db.session.query(Server).all()
    )
    for server in servers:
        try:
            do_sync(server.ip, server.admin_username, server.admin_password, server.id)
        except Exception as e:
            flash(e)
            return redirect(url_for("deployed_app.list_app"))
    flash("Đồng bộ thành công port và status", "success")
    return redirect(url_for("deployed_app.list_app"))


@deployed_app_bp.route("/add-dns-txt/<int:app_id>", methods=["POST"])
@login_required
def add_dns_txt(app_id):
    txt_value = (request.form.get("txt_value") or "").strip()
    if not txt_value:
        flash("Vui lòng nhập nội dung TXT xác minh!", "warning")
        return redirect(url_for("deployed_app.list_app"))
    try:
        app = DeployedApp.query.get_or_404(app_id)
        domain = Domain.query.get_or_404(app.domain_id)
        cf_account = domain.cloudflare_account
        subdomain = app.subdomain or ""
        result = add_or_update_txt_record(
            zone_id=domain.zone_id,
            subdns=subdomain,
            dns=domain.name,
            new_txt=txt_value,
            ttl=3600,
            cf_account=cf_account,
        )

        # ==== Cập nhật vào bảng DomainVerification ====
        verification = DomainVerification.query.filter_by(
            deployed_app_id=app.id
        ).first()
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
        # ==============================================

        app.status = "add_txt"
        db.session.commit()
        db.session.refresh(app)
        db.session.expire_all()
        flash("Đã thêm/cập nhật bản ghi TXT thành công!", "success")
    except Exception as e:
        flash(f"Lỗi khi thêm/cập nhật bản ghi TXT: {e}", "danger")
    return redirect(url_for("deployed_app.list_app"))


@deployed_app_bp.route("/stop-app/<int:app_id>", methods=["POST"])
@login_required
def stop_app(app_id):
    print(f"[ACTION] Dừng app ID: {app_id}")
    # TODO: xử lý dừng app thực tế
    try:
        app = DeployedApp.query.get_or_404(app_id)
        server = app.server
        flash(f"Đã gửi yêu cầu dừng app #{app_id}", "warning")
        out = remote_turn_off(
            host=server.ip,
            user=server.admin_username,
            password=server.admin_password,
            subdomain=app.subdomain,
        )
        app.status = "inactive"
        app.log = out
        logger.info(f"Tắt app thành công:\n{out}")
    except Exception as e:
        app.status = "failed"
        app.log = str(e)
        logger.error(f"Lỗi dừng app:\n{str(e)}")
    finally:
        db.session.commit()
        db.session.refresh(app)
        db.session.expire_all()
    return redirect(url_for("deployed_app.list_app"))


@deployed_app_bp.route("/confirm-facebook/<int:app_id>", methods=["POST"])
@login_required
def confirm_facebook(app_id):
    print(f"[ACTION] Xác nhận liên kết Facebook cho app ID: {app_id}")
    flash(f"Đã gửi yêu cầu xác minh Facebook cho app #{app_id}", "success")
    return redirect(url_for("deployed_app.list_app"))


@deployed_app_bp.route("/redeploy/<int:app_id>", methods=["POST"])
@login_required
def redeploy_app(app_id):
    print(f"[ACTION] Deploy lại app ID: {app_id}")
    flash(f"Đang thực hiện lại deploy app #{app_id}", "danger")
    # TODO: thực hiện lại thao tác deploy nếu muốn
    return redirect(url_for("deployed_app.list_app"))


@deployed_app_bp.route("/detail/<int:app_id>")
@login_required
def detail_app(app_id):
    db.session.expire_all()
    app = DeployedApp.query.get_or_404(app_id)
    server = Server.query.get_or_404(app.server_id)
    domain = Domain.query.get_or_404(app.domain_id)
    verification = DomainVerification.query.filter_by(deployed_app_id=app.id).first()
    return render_template(
        "deployed_app/app_detail.html",
        app=app,
        server=server,
        domain=domain,
        verification=verification,
    )
