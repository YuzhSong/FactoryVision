import json
import os
import socket
import sys

import paramiko


HOST = os.environ.get("FACTORYVISION_SRS_HOST", "")
USER = os.environ.get("FACTORYVISION_SRS_USER", "")
PASSWORD = os.environ.get("FACTORYVISION_SRS_PASSWORD", "")

COMMANDS = [
    ("docker_ps", "docker ps --format '{{json .}}'"),
    ("docker_ps_a", "docker ps -a --format '{{json .}}'"),
    ("ports", "ss -tunlp | grep -E '1935|8443|8080|1985' || true"),
    ("compose_files", "find ~ /opt /srv /data -maxdepth 4 \\( -name 'docker-compose.yml' -o -name 'docker-compose.yaml' -o -name 'compose.yml' -o -name 'compose.yaml' \\) 2>/dev/null"),
    ("srs_guess", "docker ps -a --format '{{.Names}}' | grep -Ei 'srs|stream|media|live' || true"),
    ("dns", "getent hosts webrtc.rainycode.cn || nslookup webrtc.rainycode.cn 2>/dev/null || true"),
]


def run(ssh, cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
    code = stdout.channel.recv_exit_status()
    return {
        "command": cmd,
        "exit_code": code,
        "stdout": stdout.read().decode("utf-8", errors="replace"),
        "stderr": stderr.read().decode("utf-8", errors="replace"),
    }


def main():
    if not HOST or not USER or not PASSWORD:
        raise SystemExit(
            "Set FACTORYVISION_SRS_HOST, FACTORYVISION_SRS_USER, and "
            "FACTORYVISION_SRS_PASSWORD before running this script."
        )

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=15, banner_timeout=15, auth_timeout=15)

    result = {"host": HOST, "checks": {}}
    for name, cmd in COMMANDS:
        result["checks"][name] = run(ssh, cmd)

    # Try to inspect likely compose dirs and logs from likely containers.
    compose_out = result["checks"]["compose_files"]["stdout"].strip().splitlines()
    result["compose_details"] = []
    for path in compose_out[:8]:
        dirpath = path.rsplit("/", 1)[0]
        detail = {
            "path": path,
            "pwd": dirpath,
            "config": run(ssh, f"cd {dirpath} && sed -n '1,240p' {path.split('/')[-1]}"),
            "ps": run(ssh, f"cd {dirpath} && docker compose ps || docker-compose ps"),
        }
        result["compose_details"].append(detail)

    names = [line.strip() for line in result["checks"]["srs_guess"]["stdout"].splitlines() if line.strip()]
    if not names:
        all_names = []
        for line in result["checks"]["docker_ps_a"]["stdout"].splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if obj.get("Names"):
                    all_names.append(obj["Names"])
            except Exception:
                pass
        names = all_names[:3]

    result["container_logs"] = []
    for name in names[:3]:
        result["container_logs"].append({
            "name": name,
            "logs": run(ssh, f"docker logs --tail 200 {name}"),
        })

    try:
        result["local_dns"] = socket.gethostbyname_ex("webrtc.rainycode.cn")
    except Exception as e:
        result["local_dns"] = {"error": str(e)}

    ssh.close()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
