import os
import threading
import logging
import paramiko
from flask import current_app
from database_init import db
from models.website import Website
from models.server import Server

# =============== Hàm SSH deploy nginx + certbot ===============


def deploy_nginx_certbot_via_ssh(
    host: str,
    user: str,
    password: str,
    domain: str,
    port: int = 3000,
    local_script_path: str = "./deploy_nginx.sh",
    remote_script_path: str = "/home/deploy_nginx.sh",
    timeout: int = 900,
) -> str:
    """
    SSH vào server, upload và thực thi script deploy_nginx.sh với domain+port.
    Trả về log stdout/stderr.
    """
    logger = logging.getLogger("genweb_logger")
    try:
        # Kết nối SSH
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, username=user, password=password, timeout=30)

        # Upload script nếu chưa có
        sftp = ssh.open_sftp()
        try:
            sftp.stat(remote_script_path)
        except FileNotFoundError:
            sftp.put(local_script_path, remote_script_path)
            sftp.chmod(remote_script_path, 0o755)
            logger.info(f"Đã upload script lên {host}:{remote_script_path}")
        sftp.close()

        # Thực thi script với domain và port
        cmd = f"bash {remote_script_path} {domain} {port}"
        logger.info(f"Thực thi: {cmd} trên {host}")

        stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True, timeout=timeout)
        out = stdout.read().decode()
        err = stderr.read().decode()
        ssh.close()

        full_log = f"{out}\n{'='*32}\n{err}"
        if err.strip():
            logger.warning(f"Lỗi khi deploy nginx/certbot trên {host}: {err}")
        else:
            logger.info(f"Deploy nginx/certbot hoàn tất trên {host}")
        return full_log

    except Exception as e:
        logger.error(f"Lỗi SSH deploy nginx/certbot: {e}")
        return str(e)


# =============== Hàm chạy background thread ===============


def start_nginx_certbot_deploy_bg(
    website_id: int,
    domain: str,
    port: int = 3000,
    local_script_path: str = "./deploy_nginx.sh",
    remote_script_path: str = "/home/deploy_nginx.sh",
):
    """
    Gọi deploy nginx/certbot cho website chạy ở background thread.
    """

    def _deploy(app):
        with app.app_context():
            website = Website.query.get(website_id)
            if not website:
                return
            server = Server.query.get(website.server_id)
            log = deploy_nginx_certbot_via_ssh(
                host=server.ip,
                user=server.admin_username,
                password=server.admin_password,
                domain=domain,
                port=port,
                local_script_path=local_script_path,
                remote_script_path=remote_script_path,
            )
            # Ghi log lại database
            website.note = (website.note or "") + f"\n[nginx deploy log]\n{log}"
            # Option: website.status = "nginx_deployed"
            db.session.commit()

    thread = threading.Thread(
        target=_deploy,
        args=(current_app._get_current_object(),),
        daemon=True,
    )
    thread.start()


# =============== Ví dụ sử dụng sau khi tạo website mới ===============

# website = create_website_from_form(form, company.id, user_id)
# domain_full = "abc.example.com"  # hoặc domain/subdomain
# start_nginx_certbot_deploy_bg(website.id, domain_full, port=3000)
