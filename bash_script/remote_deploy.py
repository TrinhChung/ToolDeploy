import paramiko
from typing import Optional
import os

def run_remote_deploy(
    host: str,
    user: str,
    *,
    password: str,
    input_dir: str,
    appId: str,
    appSecret: str,
    appName: str,
    email: str,
    address: str,
    phoneNumber: str,
    dnsWeb: str,
    companyName: str,
    taxNumber: str,
    local_script_path: str = "./init.sh",
    remote_path: str = "/home/init.sh",
) -> str:
    """
    Copy file init.sh lên server qua SSH và thực thi nó.
    """

    remote_path = remote_path.format(user=user)

    # 🧠 Mở kết nối SSH
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

    # 📤 Dùng SFTP để copy file lên
    sftp = ssh.open_sftp()
    try:
        sftp.put(local_script_path, remote_path)
    finally:
        sftp.close()

    # 🛠️ Cấp quyền thực thi và chạy file
    cmd = f"chmod +x {remote_path} && bash {remote_path}"
    stdin, stdout, stderr = ssh.exec_command(cmd)

    exit_status = stdout.channel.recv_exit_status()
    out, err = stdout.read().decode(), stderr.read().decode()
    
    ssh.close()

    #File log nằm đâu?, quản lý thế nào
    local_log_path=""

    with open(local_log_path, "w", encoding="utf-8") as f:
        f.write("=== STDOUT ===\n")
        f.write(out)
        f.write("\n\n=== STDERR ===\n")
        f.write(err)

    if exit_status != 0:
        raise RuntimeError(f"Remote script execution failed:\n{err}")
    return out
