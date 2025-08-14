import secrets
import logging
from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    jsonify,
)
from extensions import csrf
from flask_login import login_required
from database_init import db
from sqlalchemy import exists
from models.deployed_app import DeployedApp
from models.server import Server
from models.domain import Domain
from Form.deploy_app_form import DeployAppForm
from bash_script.remote_deploy import remote_turn_off, do_sync
from util.cloud_flare import add_or_update_txt_record
from service.deployed_app_service import (
    start_background_deploy,
    create_deployed_app,
    build_env_text,
    create_dns_record_if_needed,
    remove_deployed_app,
    migrate_deployed_app,
)
from service.faceBookApi import genTokenForApp
from models.domain_verification import DomainVerification
from util.constant import DEPLOYED_APP_STATUS

deployed_app_bp = Blueprint("deployed_app", __name__, url_prefix="/deployed_app")
logger = logging.getLogger("deploy_logger")

# đảm bảo có Session = scoped_session(sessionmaker(bind=engine))
# đảm bảo có Session = scoped_session(sessionmaker(bind=engine))


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
    db.session.expire_all()
    deployed_apps = (
        db.session.query(DeployedApp, Server, Domain)
        .join(Server, DeployedApp.server_id == Server.id)
        .join(Domain, DeployedApp.domain_id == Domain.id)
        .order_by(DeployedApp.created_at.desc())  # để phụ sort created_at
        .all()
    )

    # Soft lại theo status ưu tiên (order) trong Enum
    def get_status_order(app_tuple):
        app = app_tuple[0]  # vì mỗi phần tử là (DeployedApp, Server, Domain)
        try:
            return DEPLOYED_APP_STATUS[app.status].order
        except KeyError:
            return 999  # status lạ cho xuống cuối

    # Có thể phụ thêm sort theo thời gian nếu cùng trạng thái
    deployed_apps = sorted(
        deployed_apps,
        key=lambda tup: (get_status_order(tup), -tup[0].created_at.timestamp()),
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
            flash(f"Lỗi sync: {e}")
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
        domain = app.domain
        flash(f"Đã gửi yêu cầu dừng app #{app_id}", "warning")
        out = remote_turn_off(
            host=server.ip,
            user=server.admin_username,
            password=server.admin_password,
            fullDomain=f"{app.subdomain}.{domain.name}",
        )
        app.status = DEPLOYED_APP_STATUS.inactive.value
        app.log = out
        logger.info(f"Tắt app thành công:\n{out}")
    except Exception as e:
        app.status = DEPLOYED_APP_STATUS.failed.value
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
    servers = Server.query.all()
    return render_template(
        "deployed_app/app_detail.html",
        app=app,
        server=server,
        domain=domain,
        verification=verification,
        servers=servers,
    )


@deployed_app_bp.route("/delete/<int:app_id>", methods=["POST"])
@login_required
def delete_app(app_id):
    try:
        remove_deployed_app(app_id)
        flash("Đã xóa app và các DNS liên quan", "success")
    except Exception as e:
        flash(f"Lỗi khi xóa app: {e}", "danger")

    return redirect(url_for("deployed_app.list_app"))


@deployed_app_bp.route("/migrate/<int:app_id>", methods=["POST"])
@login_required
def migrate_app(app_id):
    new_server_id = request.form.get("server_id", type=int)
    try:
        migrate_deployed_app(app_id, new_server_id)
        flash("Đang chuyển app sang server mới...", "info")
    except Exception as e:
        flash(f"Lỗi chuyển server: {e}", "danger")
    return redirect(url_for("deployed_app.detail_app", app_id=app_id))

@deployed_app_bp.route("/appinfo/update", methods=["POST"])
@csrf.exempt
def update_token():
    data = request.get_json()
    shortLivedUserToken = data.get("shortLivedUserToken", None)
    appId = data.get("appId", None)
    appSecret = data.get("appSecret", None)
    is_exist = db.session.query(
    exists().where(DeployedApp.env.like(f"%{appId}%"))).scalar()
    if is_exist:
        check = genTokenForApp(shortLivedUserToken, appId, appSecret)
        if check is None:
            return jsonify({"status": "failed", "message": "Lỗi xảy ra khi tạo token mới cho app"})
        else:
            return jsonify({"status": "success", "message": "Tạo token dài hạn thành công"})
    else:
        return jsonify({"status": "failed", "message": "Không tồn tại app tương ứng với id"})
