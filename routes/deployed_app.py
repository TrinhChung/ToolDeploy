import secrets
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from database_init import db
from models.deployed_app import DeployedApp
from models.server import Server
from models.domain import Domain
from Form.deploy_app_form import DeployAppForm

deployed_app_bp = Blueprint("deployed_app", __name__, url_prefix="/deployed_app")


@deployed_app_bp.route("/deploy", methods=["GET", "POST"])
@login_required
def deploy_app():
    form = DeployAppForm()
    form.server_id.choices = [(s.id, s.name) for s in Server.query.all()]
    form.domain_id.choices = [(d.id, d.name) for d in Domain.query.all()]

    if request.method == "POST" and "default_env" in request.form:
        # Đề giá trị mặc định cho các trường ENV
        form.EMAIL.data = "chungtrinh2k2@gmail.com"
        form.ADDRESS.data = "147 Thái Phiên, Phường 9, Quận 11, TP.HCM, Việt Nam"
        form.PHONE_NUMBER.data = "07084773586"
        form.DNS_WEB.data = "noirsteed.bmapp.com"
        form.COMPANY_NAME.data = "CÔNG TY TNHH NOIR STEED"
        form.TAX_NUMBER.data = "0318728792"

    if form.validate_on_submit():
        # Sinh APP_SECRET random
        app_secret = secrets.token_hex(16)
        # Lấy tất cả env thành text
        env_text = (
            f"APP_ID={form.APP_ID.data}\n"
            f"APP_SECRET={app_secret}\n"
            f"SECRET_KEY={app_secret}\n"
            f"APP_NAME={form.APP_NAME.data}\n"
            f"EMAIL={form.EMAIL.data}\n"
            f"ADDRESS={form.ADDRESS.data}\n"
            f"PHONE_NUMBER={form.PHONE_NUMBER.data}\n"
            f"DNS_WEB={form.DNS_WEB.data}\n"
            f"COMPANY_NAME={form.COMPANY_NAME.data}\n"
            f"TAX_NUMBER={form.TAX_NUMBER.data}"
        )

        deployed_app = DeployedApp(
            server_id=form.server_id.data,
            domain_id=form.domain_id.data,
            subdomain=form.subdomain.data.strip() or None,
            env=env_text,
            note=form.note.data,
            status="active",
        )
        db.session.add(deployed_app)
        db.session.commit()
        flash("Deploy app thành công! (Batch giả lập)", "success")
        return redirect(url_for("deployed_app.list_app"))

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
