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
    logging.getLogger("werkzeug").setLevel(logging.WARNING)

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
    subdomain: str,
    port: int | str = 5000,
) -> str:
    """Khởi động Flask app (flask run) trong /home/<subdomain>."""
    ssh = _connect_ssh(host, user, password)

    cmd = rf"""
        FOLDER="/home/{subdomain}";
        cd "$FOLDER";
        nohup bash -c 'stdbuf -oL -eL flask run --host=0.0.0.0 --port {port} \
            2>&1 | ts "[%Y-%m-%d %H:%M:%S]"' >> flask.log & echo $!
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
    subdomain: str,
) -> str:
    """Tắt các tiến trình flask run đúng thư mục đó."""
    ssh = _connect_ssh(host, user, password)

    cmd = rf"""
        FOLDER="/home/{subdomain}";
        for pid in $(pgrep -f "flask run"); do
            pwd_env=$(tr '\0' '\n' < /proc/$pid/environ 2>/dev/null |
                      grep '^PWD=' | cut -d= -f2);
            if [ "$pwd_env" = "$FOLDER" ]; then
                echo "Killing PID $pid in $FOLDER";
                kill $pid;
            fi;
        done
    """
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
    dnsWeb: str, companyName: str, taxNumber: str,
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
    f"\"{companyName}\" {taxNumber} 2>&1 | ts \"[%Y-%m-%d %H:%M:%S]\" "
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
