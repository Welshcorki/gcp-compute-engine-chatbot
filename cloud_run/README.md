# 🚀 Google Cloud Run Gemini Chatbot

Google Cloud Platform (GCP)의 **Cloud Run** 서버리스 완전 관리형 컨테이너 환경에 최적화된 **Gemini 3.8 Flash & 3.7 Flash 웹 챗봇 서비스**입니다.

Interactions API 기반의 **Google Search Grounding**, **Thinking Level**, **실시간 SSE 스트리밍**, **프리미엄 다크 테마 UI**를 단일 컨테이너로 완전 패키징하여 운영합니다.

---

## ✨ Cloud Run 아키텍처의 특장점

1. **🔒 구글 자동 관리 공인 HTTPS**
   - 별도의 Nginx, Certbot 설정 없이 `https://<서비스명>-<해시>-<리전>.a.run.app` 형태의 글로벌 신뢰 공인 HTTPS 보안 인증서가 즉시 제공됩니다.
2. **💰 비용 0원 유지 (Scale-to-Zero)**
   - 트래픽이 없을 때는 인스턴스 개수가 0개(`min-instances: 0`)로 축소되어 유휴 비용이 전혀 발생하지 않습니다.
   - 요청이 들어오면 수 초 내에 자동 스케일 업(Auto-scaling)됩니다.
3. **📦 Multi-stage Docker 컨테이너 빌드**
   - **Stage 1 (Node.js 20)**: 프론트엔드(`frontend/`)를 자동으로 번들링하여 정적 산출물(`static/`) 생성
   - **Stage 2 (Python 3.11 Slim)**: 경량화 파이썬 런타임에 FastAPI 백엔드와 번들 산출물만 포함하여 초경량 이미지 빌드
4. **🔐 Secret Manager 네이티브 주입**
   - Cloud Run 배포 시 `--set-secrets="GEMINI_API_KEY=GEMINI_API_KEY:latest"` 플래그로 컨테이너 환경변수에 API 키가 안전하게 주입됩니다.

---

## 🏗️ 폴더 구조

```text
cloud_run/
├── frontend/                   # 프론트엔드 소스코드 (Vite + Vanilla JS)
│   ├── src/
│   │   ├── main.js             # 상태 관리, SSE 스트림, STT 음성인식
│   │   └── style.css           # Gemini 스타일 프리미엄 다크 UI
│   ├── index.html              # 메인 HTML
│   ├── vite.config.js          # build outDir -> ../static 설정
│   └── package.json
├── static/                     # 프론트엔드 번들 산출물 (FastAPI가 서빙)
├── Dockerfile                  # 멀티 스테이지 최적화 컨테이너 빌드 파일
├── .dockerignore               # 컨테이너 빌드 제외 설정
├── main.py                     # FastAPI 백엔드 ($PORT 동적 바인딩 지원)
├── requirements.txt            # 백엔드 의존성 목록
├── deploy_to_cloud_run.py      # Cloud Run 원클릭 자동 빌드 & 배포 스크립트
└── README.md                   # Cloud Run 모듈 가이드
```

---

## 🛠️ 로컬 개발 및 테스트

### 1. 로컬 파이썬 환경에서 바로 실행
```bash
cd cloud_run

# 가상환경 패키지 설치
pip install -r requirements.txt

# 환경변수 설정 (.env 파일 또는 export)
export GEMINI_API_KEY="your_api_key"

# 서버 실행 (기본 포트 8080)
uvicorn main:app --host 127.0.0.1 --port 8080
```
브라우저에서 `http://127.0.0.1:8080` 접속

### 2. 로컬 Docker 컨테이너로 실행
```bash
cd cloud_run

# 멀티 스테이지 도커 이미지 빌드
docker build -t gemini-chatbot-run .

# 컨테이너 실행
docker run -p 8080:8080 -e GEMINI_API_KEY="your_api_key" gemini-chatbot-run
```
브라우저에서 `http://localhost:8080` 접속

---

## ☁️ Cloud Run 배포 가이드

### 방법 1. 원클릭 자동 배포 (권장)
로컬에 Google Cloud SDK(`gcloud`)가 인증되어 있다면 아래 스크립트로 Cloud Build를 통한 원격 컨테이너 빌드부터 Cloud Run 배포, Secret Manager 연동, 공인 HTTPS 발급, 헬스체크까지 한 번에 완료됩니다:

```bash
# 프로젝트 루트 또는 cloud_run 폴더에서 실행 가능
python cloud_run/deploy_to_cloud_run.py
```

### 방법 2. gcloud CLI 수동 배포
```bash
cd cloud_run

gcloud run deploy gemini-chatbot-run \
  --source . \
  --region us-central1 \
  --project iceu-songpa30 \
  --platform managed \
  --allow-unauthenticated \
  --set-secrets="GEMINI_API_KEY=GEMINI_API_KEY:latest" \
  --min-instances 0 \
  --max-instances 5 \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300
```
배포가 완료되면 터미널에 출력되는 `Service URL`(`https://gemini-chatbot-run-xxxx.a.run.app`)로 접속하여 챗봇을 즉시 사용할 수 있습니다.
