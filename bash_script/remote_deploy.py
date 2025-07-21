# bash_script/remote_deploy.py
import paramiko
from typing import Optional


def run_remote_deploy(
    host: str,
    user: str,
    *,
    password: str,  # ✅ chỉ cần password
    input_dir: str,
    app_id: str,
    app_secret: str,
    dns_web: str,
    app_name: str,
    repo_url: str = "https://github.com/bach-long/getvideo-public.git",
    email: str = "admin@example.com",
    script_path: str = "./bash_script/deploy_installer.py",
) -> str:
    """SSH tới server bằng user/password và chạy deploy_installer.py"""

    cmd = (
        f"sudo python3 {script_path} "
        f"{input_dir} {app_id} {app_secret} {dns_web} '{app_name}' "
        f"--email {email} --repo {repo_url}"
    )

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    # 🔐 dùng password
    client.connect(
        hostname=host,
        username=user,
        password=password,
        timeout=20,
        allow_agent=False,
        look_for_keys=False,  # không thử key
    )

    stdin, stdout, stderr = client.exec_command(cmd)
    exit_status = stdout.channel.recv_exit_status()
    out, err = stdout.read().decode(), stderr.read().decode()
    client.close()

    if exit_status != 0:
        raise RuntimeError(f"Remote deploy failed:\n{err}")
    return out
