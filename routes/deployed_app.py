import secrets
import logging
import requests
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
from models.cloudflare_acc import CloudflareAccount
from Form.deploy_app_form import DeployAppForm
from bash_script.remote_deploy import remote_turn_off, do_sync
from util.cloud_flare import add_or_update_txt_record, build_cf_headers
from service.deployed_app_service import (
    start_background_deploy,
    create_deployed_app,
    build_env_text,
    create_dns_record_if_needed,
    remove_deployed_app,
    migrate_deployed_app,
)
from util.facebook import genTokenForApp
from models.domain_verification import DomainVerification
from util.constant import DEPLOYED_APP_STATUS
from models.facebook_api_status import FacebookApiStatus
from models.facebook_api_type import FacebookApiType
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, SQLAlchemyError  

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
    servers = db.session.query(Server).all()
    for server in servers:
        try:
            do_sync(server.ip, server.admin_username, server.admin_password, server.id)
        except Exception as e:
            flash(f"Lỗi sync: {e}")
            return redirect(url_for("deployed_app.list_app"))
    flash("Đồng bộ thành công port và status", "success")
    return redirect(url_for("deployed_app.list_app"))


@deployed_app_bp.route("/sync-dns-txt")
@login_required
def sync_dns_txt():
    """Đồng bộ trạng thái xác minh TXT của các app từ Cloudflare."""
    BASE_URL = "https://api.cloudflare.com/client/v4"
    try:
        db.session.expire_all()

        apps = (
            db.session.query(DeployedApp, Domain)
            .join(Domain, DeployedApp.domain_id == Domain.id)
            .all()
        )
        app_map = {}
        for app, domain in apps:
            full_domain = (
                f"{app.subdomain}.{domain.name}" if app.subdomain else domain.name
            )
            txt_value = app.verification.txt_value if app.verification else None
            app_map[full_domain] = (app, txt_value)

        cf_accounts = CloudflareAccount.query.all()
        for cf_acc in cf_accounts:
            headers = build_cf_headers(cf_acc)
            zones_resp = requests.get(f"{BASE_URL}/zones", headers=headers)
            zones = zones_resp.json().get("result", [])
            for zone in zones:
                zone_id = zone.get("id")
                records_resp = requests.get(
                    f"{BASE_URL}/zones/{zone_id}/dns_records?type=TXT", headers=headers
                )
                records = records_resp.json().get("result", [])
                for record in records:
                    name = record.get("name")
                    content = record.get("content")
                    if name in app_map:
                        app, txt_val = app_map[name]
                        verification = app.verification

                        if app.status != DEPLOYED_APP_STATUS.add_txt.value:
                            if txt_val is None or txt_val == content:
                                app.status = DEPLOYED_APP_STATUS.add_txt.value

                        if verification is None or not verification.txt_value:
                            if verification:
                                verification.txt_value = content
                                verification.create_count = (
                                    verification.create_count or 0
                                ) + 1
                            else:
                                db.session.add(
                                    DomainVerification(
                                        deployed_app_id=app.id,
                                        txt_value=content,
                                        create_count=1,
                                    )
                                )

        db.session.commit()
        db.session.expire_all()
        flash("Đã đồng bộ trạng thái xác minh TXT từ Cloudflare!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Lỗi đồng bộ TXT: {e}", "danger")
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
    try:
        data = request.get_json(force=True)
        short = data.get("shortLivedUserToken")
        app_id = data.get("appId")
        app_secret = data.get("appSecret")

        if not all([short, app_id, app_secret]):
            return jsonify({"status": "failed", "message": "Thiếu dữ liệu"}), 400

        # Tìm app (KHÔNG tạo/ghi gì ở session hiện tại để tránh autoflush)
        app_row = (
            db.session.query(DeployedApp.id, DeployedApp.env)
            .filter(DeployedApp.env.like(f"%{app_id}%"))
            .first()
        )
        if not app_row:
            return (
                jsonify(
                    {"status": "failed", "message": f"Không tồn tại app id {app_id}"}
                ),
                404,
            )

        # Đổi token
        long_token = genTokenForApp(short, app_id, app_secret)
        if not long_token:
            return jsonify({"status": "failed", "message": "Tạo token thất bại"}), 500

        # ---- Seed facebook_api_status bằng session riêng + INSERT IGNORE (tránh lock/autoflush) ----
        now = datetime.utcnow()
        ins_stmt = text(
            """
            INSERT IGNORE INTO facebook_api_status
                (deployed_app_id, api_type_id,
                 last_checked_at, total_calls, total_success_calls, total_errors,
                 daily_calls, daily_success_calls, daily_reset_at, mode,
                 reduced_mode_start, reduced_days_count,
                 cooldown_until, next_eligible_at,
                 last_rate_limit_at, last_error_code, last_error_subcode)
            VALUES
                (:app_id, :type_id,
                 NULL, 0, 0, 0,
                 0, 0, :now, 'normal',
                 NULL, 0,
                 NULL, NULL,
                 NULL, NULL, NULL)
        """
        )

        # dùng session tách biệt để không ảnh hưởng transaction hiện tại
        with Session(bind=db.engine, expire_on_commit=False) as s:
            # rút ngắn thời gian đợi lock để không treo request
            s.execute(text("SET SESSION innodb_lock_wait_timeout = 3"))
            # duyệt list id kiểu API trực tiếp trên session mới
            type_ids = [
                row[0]
                for row in s.execute(text("SELECT id FROM facebook_api_type")).all()
            ]

            for t_id in type_ids:
                try:
                    s.execute(
                        ins_stmt, {"app_id": app_row.id, "type_id": t_id, "now": now}
                    )
                except OperationalError as e:
                    # nếu vẫn dính lock ở 1 row nào đó thì bỏ qua row đó, tiếp tục
                    if "1205" in str(getattr(e, "orig", e)):
                        logger.warning(
                            f"[seed-status] Bỏ qua api_type={t_id} do lock-wait."
                        )
                        s.rollback()
                        continue
                    s.rollback()
                    raise
            s.commit()

        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Tạo token dài hạn thành công",
                    "longLivedUserToken": long_token,
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Lỗi /appinfo/update: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({"status": "failed", "message": f"Lỗi hệ thống: {str(e)}"}), 500
