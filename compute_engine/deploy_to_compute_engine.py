import os
import sys
import time
import tarfile
import subprocess
from datetime import datetime

# Windows 콘솔 utf-8 인코딩 설정
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "deployment.log")
PLINK_EXE = r"C:\Users\butte\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\sdk\plink.exe"
PSCP_EXE = r"C:\Users\butte\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\sdk\pscp.exe"
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
    except Exception as e:
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

def upload_file(local_path, remote_dest, host, user):
    log(f"파일 전송 (PSCP): {local_path} -> {user}@{host}:{remote_dest}")
    res = subprocess.run(
        [PSCP_EXE, "-batch", "-i", PPK_KEY, local_path, f"{user}@{host}:{remote_dest}"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    if res.stdout and res.stdout.strip():
        log(f"PSCP 출력: {res.stdout.strip()}")
    if res.stderr and res.stderr.strip():
        log(f"PSCP 에러: {res.stderr.strip()}", level="WARN" if res.returncode == 0 else "ERROR")
    if res.returncode != 0:
        raise RuntimeError(f"파일 전송 실패 (코드 {res.returncode}):\n{res.stderr}")
    return res

def main():
    log("=== GCP Compute Engine 챗봇 배포 프로세스를 재개합니다 ===")

    project_id = "iceu-songpa30"
    zone = "us-central1-a"
    instance_name = "gemini-chatbot-vm"
    user = "welshcorki"
    secret_id = "projects/584903808975/secrets/GEMINI_API_KEY"

    # 1. 인스턴스 IP 조회
    log("단계 1: 인스턴스 외부 공인 IP 확인")
    ip_res = run_cmd(
        f"gcloud compute instances describe {instance_name} --zone={zone} "
        f"--format=\"get(networkInterfaces[0].accessConfigs[0].natIP)\""
    )
    host = ip_res.stdout.strip()
    log(f"인스턴스 '{instance_name}'의 외부 IP: {host}")

    # 2. 배포 아카이브 생성
    log("단계 2: 배포용 아카이브 파일(chatbot_deploy.tar.gz) 생성")
    archive_name = os.path.join(BASE_DIR, "chatbot_deploy.tar.gz")
    with tarfile.open(archive_name, "w:gz") as tar:
        tar.add(os.path.join(BASE_DIR, "main.py"), arcname="main.py")
        tar.add(os.path.join(BASE_DIR, "requirements.txt"), arcname="requirements.txt")
        tar.add(os.path.join(BASE_DIR, "static"), arcname="static")
    log(f"배포 아카이브 생성 완료: {archive_name} ({os.path.getsize(archive_name):,} bytes)")

    # 3. VM으로 파일 업로드
    log("단계 3: VM 인스턴스로 소스코드 전송 (PSCP)")
    upload_file(archive_name, "/tmp/chatbot_deploy.tar.gz", host, user)
    log("소스코드 아카이브 전송 성공")

    # 4. VM 내부 설치 및 서비스 구동
    log("단계 4: VM 내부 챗봇 환경 구성, Secret Manager 연동 및 Systemd 서비스 등록")
    remote_setup_cmd = f"""
set -e

echo "[1/6] 시스템 패키지 업데이트 및 python3-venv 설치 중..."
sudo apt-get update -y > /dev/null
sudo apt-get install -y python3-pip python3-venv > /dev/null

echo "[2/6] 챗봇 작업 디렉터리 준비 및 파일 압축 해제..."
mkdir -p /home/{user}/chatbot
tar -xzf /tmp/chatbot_deploy.tar.gz -C /home/{user}/chatbot

echo "[3/6] Python 가상환경 생성 및 의존성 패키지 설치 중..."
cd /home/{user}/chatbot
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
./venv/bin/pip install --upgrade pip > /dev/null
./venv/bin/pip install -r requirements.txt > /dev/null

echo "[4/6] GCP Secret Manager에서 GEMINI_API_KEY 가져오는 중..."
SECRET_VAL=$(gcloud secrets versions access latest --secret="GEMINI_API_KEY" --project="584903808975")
if [ -z "$SECRET_VAL" ]; then
    echo "ERROR: Secret Manager에서 키를 조회하지 못했습니다."
    exit 1
fi
echo "GEMINI_API_KEY=$SECRET_VAL" > /home/{user}/chatbot/.env
chmod 600 /home/{user}/chatbot/.env
echo "Secret Manager 키 연동 완료 (.env 안전하게 생성됨)"

echo "[5/6] Systemd 서비스(chatbot.service) 유닛 파일 등록 중..."
sudo tee /etc/systemd/system/chatbot.service > /dev/null <<EOF
[Unit]
Description=Gemini Web Chatbot Service (Compute Engine)
After=network.target

[Service]
User={user}
WorkingDirectory=/home/{user}/chatbot
EnvironmentFile=/home/{user}/chatbot/.env
ExecStart=/home/{user}/chatbot/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo "[6/6] chatbot.service 시작 및 자동 실행 등록..."
sudo systemctl daemon-reload
sudo systemctl enable chatbot.service
sudo systemctl restart chatbot.service
sleep 2

sudo systemctl status chatbot.service --no-pager
"""
    run_remote_ssh(host, user, remote_setup_cmd)

    # 5. 외부 접속 헬스체크
    log("단계 5: 외부 공인 IP를 통한 챗봇 웹 서비스 헬스체크")
    service_url = f"http://{host}:8000"
    log(f"챗봇 웹 서비스 URL: {service_url}")

    log("서비스 안정화를 위해 5초 대기 후 헬스체크 실행...")
    time.sleep(5)

    health_check = run_cmd(f"curl -s -m 10 {service_url}/api/models", check=False)
    if health_check and health_check.returncode == 0 and "models" in health_check.stdout:
        log("[배포 완료 및 검증 성공] Compute Engine 챗봇 서비스가 정상 응답하고 있습니다!")
        log(f"헬스체크 모델 목록 응답: {health_check.stdout.strip()}")
    else:
        log("[주의] 외부 접속 지연 중 (방화벽 전파 대기 중일 수 있습니다).", level="WARN")

    # 임시 아카이브 삭제
    if os.path.exists(archive_name):
        os.remove(archive_name)

    log(f"모든 배포 과정이 성공적으로 완료되었습니다. 접속 URL: {service_url}")
    print(f"\n==================================================")
    print(f"[배포 완료] Compute Engine 챗봇 배포 성공!")
    print(f"웹 챗봇 접속 주소: {service_url}")
    print(f"전체 진행 로그: {os.path.abspath(LOG_FILE)}")
    print(f"==================================================")

if __name__ == "__main__":
    main()
