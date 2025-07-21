#!/usr/bin/env python3
"""deploy_installer.py
Python module to replace the previous Bash deployment script.

Key features
------------
* Can be **imported** and invoked as `deploy(...)` from any GUI / API layer.
* Still executable directly via command‑line (wrapper remains for convenience).
* Idempotent – only installs packages / creates resources if missing.
"""
from __future__ import annotations

import os
import secrets
import subprocess
import sys
import textwrap
import time
from pathlib import Path
from typing import Optional

import yaml  # pip install PyYAML

# ────────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────────


def run(
    cmd: list[str] | str, *, check: bool = True, cwd: Optional[Path] = None
) -> None:
    """Run a shell command and print it before execution."""
    printable = " ".join(cmd) if isinstance(cmd, list) else cmd
    print(f"$ {printable}")
    subprocess.run(cmd, shell=isinstance(cmd, str), check=check, text=True, cwd=cwd)


def dpkg_installed(pkg: str) -> bool:
    return (
        subprocess.run(
            ["dpkg", "-s", pkg], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ).returncode
        == 0
    )


def ensure_packages(pkgs: list[str]) -> None:
    missing = [p for p in pkgs if not dpkg_installed(p)]
    if missing:
        print("🛠  Installing:", ", ".join(missing))
        run(["sudo", "apt-get", "update"])
        run(
            [
                "sudo",
                "DEBIAN_FRONTEND=noninteractive",
                "apt-get",
                "install",
                "-y",
                *missing,
            ]
        )
    else:
        print("✅ Required packages already present ✔")


def generate_secret() -> str:
    return secrets.token_hex(24)


def clone_repo(repo_url: str, target_dir: Path) -> None:
    if not target_dir.exists():
        print(f"📥 Cloning repository into {target_dir} …")
        run(["git", "clone", repo_url, str(target_dir)])
    else:
        print(f"✅ Repository directory {target_dir} already exists – skipping clone.")


def patch_compose_port(compose_path: Path, service: str = "flask-app") -> int:
    with compose_path.open() as f:
        compose = yaml.safe_load(f)

    container_count = int(
        subprocess.check_output(
            [
                "bash",
                "-c",
                f"docker ps -a --filter 'name={service}' --format '{{{{.Names}}}}' | wc -l",
            ],
            text=True,
        ).strip()
    )
    new_port = 5000 + container_count
    compose["services"][service]["ports"] = [f"{new_port}:5000"]

    with compose_path.open("w") as f:
        yaml.safe_dump(compose, f, default_flow_style=False)

    print(f"🔧 Patched {compose_path} → {new_port}:5000")
    return new_port


def write_env_file(env_path: Path, variables: dict[str, str]) -> None:
    env_content = "\n".join(f"{k}={v}" for k, v in variables.items()) + "\n"
    env_path.write_text(env_content)
    print(f"📝 Wrote {env_path}")


def ensure_docker_network(name: str) -> None:
    existing = subprocess.run(
        ["docker", "network", "ls", "--format", "{{.Name}}"],
        capture_output=True,
        text=True,
    ).stdout.split()
    if name not in existing:
        run(["docker", "network", "create", name])
    else:
        print(f"✅ Docker network '{name}' already exists.")


def write_mysql_compose(path: Path) -> None:
    compose_dict = {
        "version": "3",
        "services": {
            "db": {
                "image": "mysql:8.0",
                "container_name": "mysql_db",
                "restart": "always",
                "environment": {
                    "MYSQL_ROOT_PASSWORD": "password123456",
                    "MYSQL_DATABASE": "video",
                    "MYSQL_USER": "admin",
                    "MYSQL_PASSWORD": "password123456",
                },
                "expose": ["3306"],
                "ports": ["3306:3306"],
                "volumes": ["/tmp/app/mysqld:/run/mysqld", "db_data:/var/lib/mysql"],
                "healthcheck": {
                    "test": ["CMD", "mysqladmin", "ping", "-h", "localhost"],
                    "timeout": "20s",
                    "retries": 10,
                },
                "networks": ["shared-net"],
            }
        },
        "volumes": {"db_data": {}},
        "networks": {"shared-net": {"external": True}},
    }
    path.write_text(yaml.safe_dump(compose_dict))
    print(f"📝 Wrote MySQL compose → {path}")


def write_nginx_conf(dns_web: str, port: int, conf_path: Path) -> None:
    conf_body = textwrap.dedent(
        f"""
        server {{
            server_name {dns_web};
            location / {{
                if ($query_string ~* "union.*select.*(\") {{ return 403; }}
                if ($query_string ~* "select.+from") {{ return 403; }}
                if ($query_string ~* "insert\\s+into") {{ return 403; }}
                if ($query_string ~* "drop\\s+table") {{ return 403; }}
                if ($query_string ~* "information_schema") {{ return 403; }}
                if ($query_string ~* "sleep\\((\\s*)(\\d*)(\\s*)\\)") {{ return 403; }}
                proxy_pass http://127.0.0.1:{port};
                proxy_set_header Host $host;
                proxy_set_header X-Real-IP $remote_addr;
                proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                proxy_set_header X-Forwarded-Proto $scheme;
            }}
        }}
        """
    )
    conf_path.write_text(conf_body)
    print(f"📝 Wrote Nginx vhost → {conf_path}")


def reload_nginx() -> None:
    run(["sudo", "nginx", "-t"])
    run(["sudo", "systemctl", "reload", "nginx"])


def obtain_certificate(dns_web: str, email: str) -> None:
    run(
        [
            "sudo",
            "certbot",
            "--nginx",
            "-d",
            dns_web,
            "--non-interactive",
            "--agree-tos",
            f"--email={email}",
        ]
    )


def wait_for_mysql() -> None:
    print("⏳ Waiting for MySQL healthcheck …")
    while True:
        res = subprocess.run(
            [
                "docker",
                "exec",
                "mysql_db",
                "mysqladmin",
                "ping",
                "-u",
                "root",
                "-ppassword123456",
                "--silent",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        if "mysqld is alive" in res.stdout:
            break
        time.sleep(4)
    print("✅ MySQL is healthy.")


# ────────────────────────────────────────────────────────────────────────────────
# Public API – deploy() callable from GUI or other Python code
# ────────────────────────────────────────────────────────────────────────────────


def deploy(
    input_dir: str,
    app_id: str,
    app_secret: str,
    dns_web: str,
    app_name: str,
    *,
    email: str = "admin@example.com",
    repo_url: str = "https://github.com/bach-long/getvideo-public.git",
) -> None:
    """Full deployment entry‑point.

    Parameters
    ----------
    input_dir : str  – target directory name under /home
    app_id    : str  – APP_ID for .env
    app_secret: str  – APP_SECRET for .env
    dns_web   : str  – domain for nginx / certbot
    app_name  : str  – human‑readable app name
    email     : str  – email used by certbot (default admin@example.com)
    repo_url  : str  – git repository to clone
    """

    target_dir = Path("/home") / input_dir
    secret_key = generate_secret()

    # 1. Ensure packages
    ensure_packages(
        [
            "git",
            "nginx",
            "curl",
            "gnupg",
            "lsb-release",
            "certbot",
            "python3-certbot-nginx",
            "docker-ce",
            "docker-ce-cli",
            "containerd.io",
            "docker-buildx-plugin",
            "docker-compose-plugin",
            "netcat",
        ]
    )
    run(["sudo", "ufw", "allow", "80"])
    run(["sudo", "ufw", "allow", "443"])

    # 2. Clone repository
    clone_repo(repo_url, target_dir)

    # 3. Patch docker-compose port
    compose_path = target_dir / "docker-compose.yml"
    new_port = patch_compose_port(compose_path)

    # 4. Write .env
    write_env_file(
        target_dir / ".env",
        {
            "ACCESS_TOKEN": "",
            "USER_TOKEN": "",
            "APP_TOKEN": "",
            "APP_ID": app_id,
            "APP_SECRET": app_secret,
            "SECRET_KEY": secret_key,
            "TOKEN_TELEGRAM_BOT": "",
            "APP_NAME": app_name,
            "PASSWORD_DB": "password123456",
            "NAME_DB": "video",
            "USER_DB": "admin",
            "ADDRESS_DB": "mysql_db",
            "EMAIL": email,
            "ADDRESS": "147 Thái Phiên, Phường 9, Quận 11, TP.HCM, Việt Nam",
            "PHONE_NUMBER": "07084773586",
            "DNS_WEB": dns_web,
            "COMPANY_NAME": "CÔNG TY TNHH NOIR STEED",
            "TAX_NUMBER": "0318728792",
        },
    )

    # 5. Ensure docker network and write MySQL compose
    ensure_docker_network("shared-net")
    write_mysql_compose(Path("/home/docker-compose.yml"))

    # 6. Nginx & TLS
    nginx_conf_path = Path(f"/etc/nginx/sites-enabled/{dns_web}")
    write_nginx_conf(dns_web, new_port, nginx_conf_path)
    reload_nginx()
    obtain_certificate(dns_web, email)

    # 7. Start MySQL stack and wait for healthcheck
    run(["docker", "compose", "-f", "/home/docker-compose.yml", "up", "-d", "--build"])
    wait_for_mysql()

    # 8. Start application stack
    run(["docker", "compose", "up", "--build", "-d"], cwd=target_dir)
    print("🎉 Deployment complete!")


# ---------------------------------------------------------------------------
# Optional CLI wrapper – still useful for debugging
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if os.geteuid() != 0:
        print("⚠️  Warning: script should be run with sudo/root for full functionality.")

    import argparse

    p = argparse.ArgumentParser(description="Deploy application stack")
    p.add_argument("input_dir")
    p.add_argument("app_id")
    p.add_argument("app_secret")
    p.add_argument("dns_web")
    p.add_argument("app_name")
    p.add_argument("--email", default="admin@example.com")
    p.add_argument("--repo", default="https://github.com/bach-long/getvideo-public.git")
    args = p.parse_args()

    deploy(
        input_dir=args.input_dir,
        app_id=args.app_id,
        app_secret=args.app_secret,
        dns_web=args.dns_web,
        app_name=args.app_name,
        email=args.email,
        repo_url=args.repo,
    )
