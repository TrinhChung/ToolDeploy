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
from bash_script.remote_deploy import run_remote_deploy
from util.cloud_flare import check_dns_record_exists, add_dns_record

deployed_app_bp = Blueprint("deployed_app", __name__, url_prefix="/deployed_app")
logger = logging.getLogger("deploy_logger")


def background_deploy(app, deployed_app_id, server_id, form_data, input_dir, dns_web):
    """
    Hàm chạy trong thread để deploy trên remote server.
    Cần truyền `app` vào và dùng `with app.app_context():` để có context Flask.
    """
    with app.app_context():
        deployed_app = DeployedApp.query.get(deployed_app_id)
        server = Server.query.get(server_id)

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
            deployed_app.status = "active"
            deployed_app.log = log
            logger.info(f"Deploy thành công:\n{log}")
        except Exception as e:
            deployed_app.status = "failed"
            deployed_app.log = str(e)
            logger.error(f"Deploy lỗi:\n{str(e)}")
        finally:
            db.session.commit()


@deployed_app_bp.route("/deploy", methods=["GET", "POST"])
@login_required
def deploy_app():
    """
    1. Hiển thị form chọn server / domain và khai báo ENV.
    2. Khi submit:
       • Tạo bản ghi DeployedApp (status=deploying).
       • Tạo DNS record (Cloudflare) nếu có subdomain.
       • Chạy deploy ở background thread (không block request).
       • Khi xong: cập nhật status = active / failed + log.
    """
    form = DeployAppForm()
    form.server_id.choices = [(s.id, s.name) for s in Server.query.all()]
    form.domain_id.choices = [(d.id, d.name) for d in Domain.query.all()]

    # Gán ENV mặc định nếu bấm nút "default_env"
    if request.method == "POST" and "default_env" in request.form:
        form.EMAIL.data = "chungtrinh2k2@gmail.com"
        form.ADDRESS.data = "147 Thái Phiên, Phường 9, Quận 11, TP.HCM, Việt Nam"
        form.PHONE_NUMBER.data = "07084773586"
        form.COMPANY_NAME.data = "CÔNG TY TNHH NOIR STEED"
        form.TAX_NUMBER.data = "0318728792"

    # Submit form deploy
    if form.validate_on_submit():
        # An toàn: lấy domain_name từ choices
        domain_name = dict(form.domain_id.choices).get(form.domain_id.data)
        if not domain_name:
            flash("Domain không hợp lệ.", "danger")
            return redirect(url_for("deployed_app.deploy_app"))

        app_secret = secrets.token_hex(16)
        subdomain = form.subdomain.data.strip() or None
        dns_web = f"{subdomain}.{domain_name}" if subdomain else domain_name

        # ENV lưu trong DB (script remote sẽ tự sinh .env)
        env_text = (
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

        # 1) Tạo bản ghi DB với trạng thái "deploying"
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

        # 1.5) Tạo DNS record cho subdomain nếu có
        domain = Domain.query.get(form.domain_id.data)
        server = Server.query.get(form.server_id.data)
        if subdomain:
            try:
                record_name = f"{subdomain}.{domain_name}"
                exists = check_dns_record_exists(
                    zone_id=domain.zone_id, subdns=record_name
                )
                if not exists:
                    add_dns_record(
                        zone_id=domain.zone_id,
                        record_name=record_name,
                        record_content=server.ip,
                        record_type="A",
                        ttl=3600,
                        proxied=False,
                    )
                    logger.info(f"✅ Đã tạo bản ghi A: {record_name} → {server.ip}")
                else:
                    logger.info(f"⚠️ Bản ghi A {record_name} đã tồn tại.")
            except Exception as e:
                logger.error(f"❌ Lỗi khi tạo bản ghi A: {str(e)}")
                flash(f"Lỗi tạo bản ghi DNS: {e}", "danger")

        # 2) Khởi động thread background deploy
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

        flash("🚀 Đang deploy... Vui lòng kiểm tra lại sau!", "info")
        return redirect(url_for("deployed_app.list_app"))

    # GET hoặc form lỗi
    return render_template("deployed_app/deploy_app.html", form=form)


@deployed_app_bp.route("/list")
@login_required
def list_app():
    """
    Danh sách các app đã deploy (hoặc đang deploy), join với server/domain để hiển thị đầy đủ.
    """
    deployed_apps = (
        db.session.query(DeployedApp, Server, Domain)
        .join(Server, DeployedApp.server_id == Server.id)
        .join(Domain, DeployedApp.domain_id == Domain.id)
        .order_by(DeployedApp.created_at.desc())
        .all()
    )
    return render_template("deployed_app/list_app.html", deployed_apps=deployed_apps)
