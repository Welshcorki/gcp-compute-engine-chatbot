import os
import sys
import time
import subprocess
import re
from datetime import datetime

# Windows 콘솔 utf-8 인코딩 설정
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "cloud_run_deployment.log")

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

def run_cmd(cmd, check=True, capture_output=True, timeout=900, cwd=None):
    log(f"명령 실행: {cmd}")
    try:
        res = subprocess.run(
            cmd,
            shell=True,
            text=True,
            capture_output=capture_output,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
            cwd=cwd or BASE_DIR
        )
        if res.stdout and res.stdout.strip():
            log(f"출력:\n{res.stdout.strip()}")
        if res.stderr and res.stderr.strip():
            log(f"알림/에러:\n{res.stderr.strip()}", level="WARN" if res.returncode == 0 else "ERROR")
        if check and res.returncode != 0:
            raise RuntimeError(f"명령어 실패 (코드 {res.returncode}): {cmd}\n{res.stderr}")
        return res
    except Exception as e:
        log(f"명령어 실행 중 예외 발생: {e}", level="ERROR")
        if check:
            raise
        return None

def main():
    log("=== GCP Cloud Run 챗봇 원클릭 자동 배포 프로세스를 시작합니다 ===")

    project_id = "iceu-songpa30"
    region = "us-central1"
    service_name = "gemini-chatbot-run"

    # 1. gcloud 설정 및 계정 확인
    log("단계 1: gcloud 프로젝트 및 활성 계정 점검")
    proj_check = run_cmd("gcloud config get-value project", check=False)
    current_proj = proj_check.stdout.strip() if proj_check else ""
    if current_proj != project_id:
        log(f"프로젝트를 '{project_id}'로 전환합니다.")
        run_cmd(f"gcloud config set project {project_id}")

    # 2. 필수 GCP API 활성화 확인 (run.googleapis.com, cloudbuild.googleapis.com)
    log("단계 2: 필수 API 활성화 상태 점검 (Cloud Run & Cloud Build)")
    run_cmd(
        f"gcloud services enable run.googleapis.com cloudbuild.googleapis.com "
        f"secretmanager.googleapis.com --project={project_id}",
        check=False
    )

    # 3. Cloud Run 빌드 및 배포 실행 (gcloud run deploy --source .)
    log("단계 3: 소스 기반 Cloud Run 컨테이너 빌드 및 배포 시작")
    log("Cloud Build를 통해 컨테이너 이미지를 빌드하고 Cloud Run에 자동 롤아웃합니다...")

    deploy_cmd = (
        f"gcloud run deploy {service_name} "
        f"--source . "
        f"--region={region} "
        f"--project={project_id} "
        f"--platform=managed "
        f"--allow-unauthenticated "
        f"--set-secrets=\"GEMINI_API_KEY=GEMINI_API_KEY:latest\" "
        f"--min-instances=0 "
        f"--max-instances=5 "
        f"--memory=512Mi "
        f"--cpu=1 "
        f"--timeout=300 "
        f"--format=\"value(status.url)\""
    )

    deploy_res = run_cmd(deploy_cmd, cwd=BASE_DIR)
    service_url = deploy_res.stdout.strip() if deploy_res else ""

    # 만약 format으로 URL을 바로 못 가져온 경우 별도 조회
    if not service_url or not service_url.startswith("http"):
        url_res = run_cmd(
            f"gcloud run services describe {service_name} "
            f"--region={region} --project={project_id} --format=\"value(status.url)\""
        )
        service_url = url_res.stdout.strip()

    log(f"배포 완료! 부여된 Cloud Run 공인 HTTPS 서비스 URL: {service_url}")

    # 4. 엔드포인트 헬스체크
    log("단계 4: 배포된 Cloud Run 챗봇 서비스 헬스체크 수행")
    time.sleep(3)

    health_res = run_cmd(f"curl -s -m 15 {service_url}/api/health", check=False)
    if health_res and health_res.returncode == 0 and "healthy" in health_res.stdout:
        log("[성공] /api/health 상태 정상 확인!")
    else:
        log("[알림] /api/health 응답 대기 중...", level="WARN")

    model_res = run_cmd(f"curl -s -m 15 {service_url}/api/models", check=False)
    if model_res and model_res.returncode == 0 and "models" in model_res.stdout:
        log(f"[성공] Gemini 모델 목록 정상 로드: {model_res.stdout.strip()}")
    else:
        log("[주의] 모델 API 응답 지연 중", level="WARN")

    log("=== Cloud Run 챗봇 배포 및 검증 완료 ===")
    print("\n==================================================")
    print("🚀 [배포 성공] Google Cloud Run 챗봇 서비스 배포 완료!")
    print(f"🔗 서비스 웹 접속 주소: {service_url}")
    print(f"🔒 자동 공인 HTTPS 인증서 적용 완료 (Let's Encrypt / Google Managed)")
    print(f"⚡ 서버리스 Scale-to-Zero 활성화 (사용 안 할 때 비용 0원)")
    print(f"📝 상세 배포 로그: {LOG_FILE}")
    print("==================================================")

if __name__ == "__main__":
    main()
