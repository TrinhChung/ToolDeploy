import secrets
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from database_init import db
from models.deployed_app import DeployedApp
from models.server import Server
from models.domain import Domain
from Form.deploy_app_form import DeployAppForm
from bash_script.remote_deploy import run_remote_deploy

deployed_app_bp = Blueprint("deployed_app", __name__, url_prefix="/deployed_app")


@deployed_app_bp.route("/deploy", methods=["GET", "POST"])
@login_required
def deploy_app():
    """
    1. Hiển thị form chọn server / domain và khai báo ENV.
    2. Khi submit:
       • Tạo bản ghi DeployedApp (status=pending).
       • SSH tới server được chọn bằng user/password,
         chạy bash_script/deploy_installer.py.
       • Cập nhật status = active / failed + lưu log.
    """
    form = DeployAppForm()
    form.server_id.choices = [(s.id, s.name) for s in Server.query.all()]
    form.domain_id.choices = [(d.id, d.name) for d in Domain.query.all()]

    # ── Gán ENV mặc định (khi ấn nút "default_env") ───────────────────────────
    if request.method == "POST" and "default_env" in request.form:
        form.EMAIL.data = "chungtrinh2k2@gmail.com"
        form.ADDRESS.data = "147 Thái Phiên, Phường 9, Quận 11, TP.HCM, Việt Nam"
        form.PHONE_NUMBER.data = "07084773586"
        form.DNS_WEB.data = "noirsteed.bmapp.com"
        form.COMPANY_NAME.data = "CÔNG TY TNHH NOIR STEED"
        form.TAX_NUMBER.data = "0318728792"

    # ── Submit triển khai ─────────────────────────────────────────────────────
    if form.validate_on_submit():
        app_secret = secrets.token_hex(16)

        # Chuẩn bị ENV text (lưu DB, không gửi lên server – script sẽ tự sinh .env)
        env_text = (
            f"APP_ID={form.APP_ID.data}\n"
            f"APP_SECRET={form.APP_SECRET.data}\n"
            f"SECRET_KEY={app_secret}\n"
            f"APP_NAME={form.APP_NAME.data}\n"
            f"EMAIL={form.EMAIL.data}\n"
            f"ADDRESS={form.ADDRESS.data}\n"
            f"PHONE_NUMBER={form.PHONE_NUMBER.data}\n"
            f"DNS_WEB={form.DNS_WEB.data}\n"
            f"COMPANY_NAME={form.COMPANY_NAME.data}\n"
            f"TAX_NUMBER={form.TAX_NUMBER.data}"
        )

        # 1) Lưu bản ghi với trạng thái pending
        deployed_app = DeployedApp(
            server_id=form.server_id.data,
            domain_id=form.domain_id.data,
            subdomain=form.subdomain.data.strip() or None,
            env=env_text,
            note=form.note.data,
            status="pending",
        )
        db.session.add(deployed_app)
        db.session.commit()

        # 2) Lấy thông tin server để SSH
        server = Server.query.get(form.server_id.data)

        try:
            # input_dir: nếu người dùng nhập subdomain thì dùng; ngược lại đặt tên cố định
            input_dir = deployed_app.subdomain or f"app_{deployed_app.id}"

            # Thực thi script trên remote host
            log = run_remote_deploy(
                host=server.ip,
                user=server.admin_username,
                password=server.admin_password
                input_dir=input_dir
                appId=form.APP_ID.data,
                appSecret=form.APP_SECRET.data,
                appName=form.APP_NAME.data,
                email=form.EMAIL.data,
                address=form.ADDRESS.data,
                phoneNumber=form.PHONE_NUMBER.data,
                dnsWeb=form.DNS_WEB.data,
                companyName=form.COMPANY_NAME.data,
                taxNumber=form.TAX_NUMBER.data
            )

            deployed_app.status = "active"
            deployed_app.log = log
            flash("🚀 Deploy thành công!", "success")

        except Exception as e:
            deployed_app.status = "failed"
            deployed_app.log = str(e)
            flash(f"❌ Deploy thất bại: {e}", "danger")

        finally:
            db.session.commit()

        return redirect(url_for("deployed_app.list_app"))

    # GET hoặc form lỗi validate
    return render_template("deployed_app/deploy_app.html", form=form)


@deployed_app_bp.route("/list")
@login_required
def list_app():
    # Load tất cả app, join với Server & Domain để show tên
    deployed_apps = (
        db.session.query(DeployedApp, Server, Domain)
        .join(Server, DeployedApp.server_id == Server.id)
        .join(Domain, DeployedApp.domain_id == Domain.id)
        .order_by(DeployedApp.created_at.desc())
        .all()
    )
    return render_template("deployed_app/list_app.html", deployed_apps=deployed_apps)
