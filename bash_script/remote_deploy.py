"""
/bash_script/remote_deploy.py
remote_deploy.py  ―  Tiện ích SSH cho quá trình deploy / bật-tắt Flask app
────────────────────────────────────────────────────────────────────────────
✓ Copy & chạy init.sh, stream log không nghẽn
✓ Bật / tắt service Flask theo sub-folder
✓ Ghi log xoay vòng vào static/app.log  (RotatingFileHandler)
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from database_init import db
import json

import paramiko
import select   # dùng cho Linux; trên Windows channel.recv_ready() đã OK


# ──────────────────────────────── Logging ──────────────────────────────── #

def setup_logging(log_dir: Optional[str] = None) -> None:
    """
    Cấu hình logger “deploy_logger” + console + file (static/app.log).
    Gọi 1 lần ở entry-point (app.py) hoặc tự động khi import module này.
    """
    if getattr(setup_logging, "_configured", False):
        return

    # ── vị trí lưu ─────────────────────────────────────────────────────── #
    base_dir = Path(__file__).resolve().parent
    log_dir = Path(log_dir) if log_dir else base_dir / "static"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "app.log"

    # ── format chung ──────────────────────────────────────────────────── #
    fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(fmt)

    # ── logger gốc: INFO → console & file ─────────────────────────────── #
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        sh = logging.StreamHandler()
        sh.setFormatter(formatter)
        root.addHandler(sh)

    if not any(isinstance(h, RotatingFileHandler) and h.baseFilename == str(log_file)
               for h in root.handlers):
        fh = RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5
        )
        fh.setFormatter(formatter)
        root.addHandler(fh)

    # không in quá nhiều log Flask werkzeug
    logging.getLogger("werkzeug").setLevel(logging.INFO)

    setup_logging._configured = True


setup_logging()                              # tự cấu hình khi import
logger = logging.getLogger("deploy_logger")  # dùng chung trong module


# ──────────────────────────── SSH Helper ───────────────────────────────── #

def _connect_ssh(host: str, user: str, password: str) -> paramiko.SSHClient:
    """Khởi tạo client Paramiko đã trust host-key & timeout."""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        hostname=host,
        username=user,
        password=password,
        timeout=20,
        allow_agent=False,
        look_for_keys=False,
    )
    return ssh


# ───────────────────────────── Turn ON/OFF ─────────────────────────────── #

def remote_turn_on(
    host: str, user: str, *,
    password: str,
    fullDomain: str,
    port: int | str = 5000,
) -> str:
    """Khởi động Flask app (flask run) trong /home/<domain>."""
    ssh = _connect_ssh(host, user, password)

    cmd = rf"""
        FOLDER="/home/{fullDomain}";
        cd "$FOLDER";
        source /home/myenv/bin/activate
        pm2 start "flask run --host=0.0.0.0 --port={port}" --name="{fullDomain}"
        source /home/myenv/bin/deactivate
    """
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)

    pid = stdout.readline().strip()
    err = stderr.read().decode()

    ssh.close()

    if not pid.isdigit():
        raise RuntimeError(f"Start failed:\n{err}")
    return f"Started Flask (PID {pid})  →  /home/{subdomain}/flask.log"


def remote_turn_off(
    host: str, user: str, *,
    password: str,
    fullDomain: str,
) -> str:
    """Tắt các tiến trình flask run đúng thư mục đó."""
    ssh = _connect_ssh(host, user, password)

    cmd = f"pm2 delete {fullDomain}"
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)

    out, err = stdout.read().decode(), stderr.read().decode()
    ssh.close()

    if err.strip():
        raise RuntimeError(f"Stop failed:\n{err}")
    return out or "No matching Flask process found."


# ───────────────────────────── Deploy ──────────────────────────────────── #

def run_remote_deploy(
    host: str, user: str, *,
    password: str,
    input_dir: str,
    appId: str, appSecret: str,
    appName: str, email: str,
    address: str, phoneNumber: str,
    dnsWeb: str, companyName: str, taxNumber: str, port: int,
    local_script_path: str = "./init.sh",
    remote_path: str = "/home/init.sh",
    max_runtime: int = 1800,     # tổng thời gian (s)
    idle_timeout: int = 300,     # không log mới (s)
) -> str:
    """
    Copy init.sh → chạy trên server → stream log tới logger.
    Thành công khi exit code = 0, ngược lại raise RuntimeError/TimeoutError.
    """
    logger.info("===> Thread deploy START")
    logger.info(f"Deploy tại port {port}")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    remote_path = remote_path.format(user=user)  # phòng trường hợp dùng {user}
    log_file = f"/home/log/{stamp}_{input_dir}.log"

    ssh = _connect_ssh(host, user, password)

    # 1️⃣  Copy script
    with ssh.open_sftp() as sftp:
        sftp.put(local_script_path, remote_path)
    logger.info("Copied init.sh to server")

    # 2️⃣  Build command
    cmd = (
    f"bash -c 'mkdir -p /home/log && chmod +x {remote_path} && "
    f"{remote_path} {input_dir} {appId} {appSecret} {dnsWeb} "
    f"\"{appName}\" {email} \"{address}\" {phoneNumber} "
    f"\"{companyName}\" {taxNumber} {port} 2>&1 | ts \"[%Y-%m-%d %H:%M:%S]\" "
    f">> {log_file}'"
    )

    # 3️⃣  Thực thi + stream
    chan = ssh.get_transport().open_session()
    chan.get_pty()                   # phòng lệnh cần TTY
    chan.exec_command(cmd)

    start = last_read = time.time()
    buffer: list[str] = []

    while True:
        # xả log
        if chan.recv_ready():
            chunk = chan.recv(4096).decode(errors="replace")
            buffer.append(chunk)
            logger.info(chunk.rstrip())
            last_read = time.time()

        # hoàn tất
        if chan.exit_status_ready():
            break

        now = time.time()
        if now - start > max_runtime:
            chan.close()
            ssh.close()
            raise TimeoutError("Deploy quá thời gian quy định")
        if now - last_read > idle_timeout:
            chan.close()
            ssh.close()
            raise TimeoutError("Không nhận log mới trong 5 phút")

        # tránh busy-loop
        time.sleep(0.2)

    exit_code = chan.recv_exit_status()
    ssh.close()

    log_text = "".join(buffer)

    if exit_code != 0:
        raise RuntimeError(f"Remote script exit {exit_code}")
    return log_text

def do_sync(
    host: str, user: str,
    password: str, server_id: int
) -> str:
    """Tắt các tiến trình flask run đúng thư mục đó."""
    ssh = _connect_ssh(host, user, password)

    cmd = r'''echo -n "{"; first=1
ps -eo pid,cmd | grep "flask run" | grep -vE "bash -c|grep" | awk '{print $1}' | while read pid; do
    cwd="/proc/$pid/cwd"
    [ -d "$cwd" ] || continue
    cmdline=$(tr '\0' ' ' < /proc/$pid/cmdline)
    echo "$cmdline" | grep -qiE "/usr/local/bin/" && continue
    port=$(echo "$cmdline" | grep -oP -- '--port=\K[0-9]*')
    [ -z "$port" ] && port='""'
    pwd=$(readlink -f "$cwd")
    [ $first -eq 1 ] && first=0 || echo -n ", "
    echo -n "\"$pwd\": $port"
done
echo "}"
'''
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)

    out, err = stdout.read().decode(), stderr.read().decode()
    ssh.close()
    print("start")
    print(out)
    print("end")
    if err.strip():
        raise RuntimeError(f"Sync failed:\n{err}")
    data = json.loads(out)
    if not data:
        print(f"Không có thư mục nào trên server số {server_id}")
        return f"Không có thư mục nào trên server số {server_id}"
    try:
        now = datetime.utcnow()
        case_sql = "\n".join(
            f"    WHEN CONCAT(da.subdomain, '.', d.name) = :dir_{i} THEN :port_{i}"
            for i, _ in enumerate(data)
        )
        in_clause = ", ".join(f":dir_{i}" for i in range(len(data)))

        sql = f"""
        UPDATE deployed_app da
        JOIN domain d ON d.id = da.domain_id
        SET da.port = CASE   
        {case_sql}
            ELSE da.port
        END,
        da.status = CASE
            WHEN da.status NOT IN ('active', 'add_txt') AND CONCAT(da.subdomain, '.', d.name) IN ({in_clause})  THEN 'active'
            WHEN da.status IN ('active', 'add_txt') AND CONCAT(da.subdomain, '.', d.name) NOT IN ({in_clause})  THEN 'inactive'
            ELSE da.status
        END,
        da.activated_at = CASE
            WHEN da.status NOT IN ('active', 'add_txt') AND CONCAT(da.subdomain, '.', d.name) IN ({in_clause})  THEN :now
            ELSE da.activated_at
        END,
        da.deactivated_at = CASE
            WHEN da.status IN ('active', 'add_txt') AND CONCAT(da.subdomain, '.', d.name) NOT IN ({in_clause})  THEN :now
            ELSE da.deactivated_at
        END,
        da.sync_at = :now
        WHERE da.server_id = :server_id
        """

        params = {"now": now, "server_id": server_id}
        for i, (directory, port) in enumerate(data.items()):
            
            params[f"dir_{i}"] = directory.split('/home/')[-1]
            params[f"port_{i}"] = port
        print(sql)
        db.session.execute(text(sql), params)
        db.session.commit()
        return "Đồng bộ thành công, reload để cập nhật"
    except SQLAlchemyError as e:
        db.session.rollback()
        print("Error:   Error during bulk update:", str(e))
        raise RuntimeError(f"Sync failed: Lỗi chạy lệnh mysql {e}")