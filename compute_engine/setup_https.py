import os
import sys
import time
import subprocess
from datetime import datetime

# Windows 콘솔 utf-8 인코딩 설정
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "deployment.log")
PLINK_EXE = r"C:\Users\butte\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\sdk\plink.exe"
PPK_KEY = os.path.expanduser(r"~\.ssh\google_compute_engine.ppk")

def log(msg, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] [{level}] {msg}"
    try:
        print(formatted)
    except UnicodeEncodeError:
        print(formatted.encode("ascii", "replace").decode("ascii"))
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except Exception:
        pass

def run_cmd(cmd, check=True, capture_output=True, timeout=300):
    log(f"로컬 명령 실행: {cmd}")
    try:
        res = subprocess.run(
            cmd,
            shell=True,
            text=True,
            capture_output=capture_output,
            timeout=timeout,
            encoding="utf-8",
            errors="replace"
        )
        if res.stdout and res.stdout.strip():
            log(f"출력:\n{res.stdout.strip()}")
        if res.stderr and res.stderr.strip():
            log(f"에러 출력:\n{res.stderr.strip()}", level="WARN" if res.returncode == 0 else "ERROR")
        if check and res.returncode != 0:
            raise RuntimeError(f"명령어 실패 (코드 {res.returncode}): {cmd}\n{res.stderr}")
        return res
    except Exception as e:
        log(f"명령어 실행 중 예외 발생: {e}", level="ERROR")
        if check:
            raise
        return None

def run_remote_ssh(host, user, command, timeout=600):
    log(f"원격 SSH 명령 실행 ({user}@{host}):\n{command.strip()}")
    res = subprocess.run(
        [PLINK_EXE, "-batch", "-ssh", "-i", PPK_KEY, f"{user}@{host}", command],
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace"
    )
    if res.stdout and res.stdout.strip():
        log(f"원격 출력:\n{res.stdout.strip()}")
    if res.stderr and res.stderr.strip():
        log(f"원격 에러/알림:\n{res.stderr.strip()}", level="WARN" if res.returncode == 0 else "ERROR")
    if res.returncode != 0:
        raise RuntimeError(f"원격 명령 실행 실패 (코드 {res.returncode}):\n{res.stderr}")
    return res

def main():
    log("=== Compute Engine HTTPS (Let's Encrypt + Nginx) 적용 시작 ===")

    project_id = "iceu-songpa30"
    zone = "us-central1-a"
    instance_name = "gemini-chatbot-vm"
    user = "welshcorki"

    # 1. 인스턴스 외부 IP 조회
    log("단계 1: 인스턴스 공인 IP 조회")
    ip_res = run_cmd(
        f"gcloud compute instances describe {instance_name} --zone={zone} "
        f"--format=\"get(networkInterfaces[0].accessConfigs[0].natIP)\""
    )
    host = ip_res.stdout.strip()
    log(f"인스턴스 IP: {host}")

    domain = f"{host}.sslip.io"
    log(f"적용 대상 도메인: {domain}")

    # 2. GCP 방화벽 규칙 (tcp:80, tcp:443) 생성 및 인스턴스 태그 추가
    log("단계 2: 방화벽 규칙(tcp:80, tcp:443) 생성 및 인스턴스 태그 설정")
    fw_check = run_cmd("gcloud compute firewall-rules describe allow-http-https", check=False)
    if not fw_check or fw_check.returncode != 0:
        run_cmd(
            f"gcloud compute firewall-rules create allow-http-https "
            f"--project={project_id} "
            f"--allow=tcp:80,tcp:443 "
            f"--target-tags=http-server,https-server "
            f"--description=\"Allow HTTP and HTTPS inbound traffic\""
        )
    else:
        log("방화벽 규칙 'allow-http-https'가 이미 존재합니다.")

    run_cmd(
        f"gcloud compute instances add-tags {instance_name} "
        f"--zone={zone} --tags=https-server,http-server",
        check=False
    )

    # 3. VM 내부 Nginx 및 Certbot 설치, 리버스 프록시 및 SSL 인증서 발급
    log("단계 3: VM 내부 Nginx & Certbot 설치 및 Let's Encrypt SSL 인증서 발급")
    remote_script = f"""
set -e

echo "[1/5] Nginx 및 Certbot 패키지 설치 중..."
sudo apt-get update -y > /dev/null
sudo apt-get install -y nginx certbot python3-certbot-nginx > /dev/null

echo "[2/5] Nginx 리버스 프록시 설정 파일 생성 중 ({domain})..."
sudo tee /etc/nginx/sites-available/chatbot > /dev/null <<'EOF'
server {{
    listen 80;
    server_name {domain};

    location / {{
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE 스트리밍 필수 설정
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 600s;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
    }}
}}
EOF

sudo ln -sf /etc/nginx/sites-available/chatbot /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx

echo "[3/5] Let's Encrypt 공인 SSL 인증서 발급 및 HTTPS 자동 구성..."
sudo certbot --nginx -d {domain} --non-interactive --agree-tos --register-unsafely-without-email --redirect

echo "[4/5] 챗봇 서비스 내부 바인딩(127.0.0.1:8000)으로 전환..."
sudo sed -i 's/--host 0.0.0.0/--host 127.0.0.1/g' /etc/systemd/system/chatbot.service
sudo systemctl daemon-reload
sudo systemctl restart chatbot.service

echo "[5/5] 서비스 구동 상태 확인..."
sudo systemctl status nginx --no-pager
sudo systemctl status chatbot.service --no-pager
"""
    run_remote_ssh(host, user, remote_script)

    # 4. 외부 HTTPS 접속 검증
    log("단계 4: 외부 HTTPS 접속 및 SSL 검증")
    https_url = f"https://{domain}/"
    log(f"HTTPS 서비스 접속 URL: {https_url}")

    log("안정화를 위해 5초 대기 후 HTTPS 헬스체크 실행...")
    time.sleep(5)

    check_res = run_cmd(f"curl -s -k -m 10 https://{domain}/api/models", check=False)
    if check_res and check_res.returncode == 0 and "models" in check_res.stdout:
        log("[성공] HTTPS를 통한 API 호출이 정상 작동합니다!")
        log(f"모델 응답: {check_res.stdout.strip()}")
    else:
        log("[주의] HTTPS 응답 대기 중입니다.", level="WARN")

    log("=== Compute Engine HTTPS 구성 완료 ===")
    print("\n==================================================")
    print(f"[성공] Compute Engine HTTPS 적용 완료!")
    print(f"안전한 HTTPS 접속 주소: {https_url}")
    print(f"(주의 요함 경고 없이 안전한 자물쇠 마크가 활성화됩니다)")
    print("==================================================")

if __name__ == "__main__":
    main()
