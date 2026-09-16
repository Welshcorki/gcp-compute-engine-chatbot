# 🚀 GCP Compute Engine Gemini Chatbot

Google Cloud Platform (GCP)의 **Compute Engine** 인스턴스 배포를 고려하여 설계된 고성능 **Gemini 3.8 Flash & 3.7 Flash 웹 챗봇 서비스**입니다.

Google GenAI 공식 SDK의 최신 **Interactions API**(`client.interactions.create`)를 도입하여 **실시간 웹 검색(Google Search Grounding)** 및 **사고/추론(Thinking Level: Medium)**이 결합된 고지능 스트리밍 답변을 제공합니다. 또한 공식 Gemini 웹사이트 감성을 정밀하게 재현한 프리미엄 다크 테마 UI와 음성 입력(STT) 기능을 탑재하고 있습니다.

---

## ✨ 주요 기능

- **🔒 완벽한 공인 HTTPS 보안 통신 (Let's Encrypt + sslip.io + Nginx)**
  - 브라우저의 `[주의 요함]` 경고를 100% 제거하고 녹색/안전한 자물쇠(🔒) 활성화
  - Nginx 리버스 프록시를 통한 SSL/TLS 종단 및 HTTP(80) $\rightarrow$ HTTPS(443) 자동 보안 리다이렉트
  - 실시간 SSE 스트리밍 버퍼링 최적화 (`proxy_buffering off`)
- **⚡ 차세대 Flash 모델 지원 및 유연한 선택**
  - **Gemini 3.8 Flash** (`models/gemini-3.8-flash`, 기본 권장): 최신 초고속 차세대 플래시 모델
  - **Gemini 3.7 Flash** (`models/gemini-3.7-flash`): 다목적 고성능 모델
  - 화면 내 드롭다운(`Flash ∨`)을 통해 언제든 자유롭게 모델 전환 가능
- **🔍 실시간 구글 검색 연동 (Google Search Grounding)**
  - `tools=[{'type': 'google_search'}]` 적용
  - 최신 날씨, 뉴스, 주식, 시사 이슈 등 실시간 웹 정보를 자동 검색하여 최신성 높은 신뢰도 있는 정보 제공
- **🧠 고도화된 추론 및 사고 과정 (Thinking Level Medium)**
  - `generation_config={'max_output_tokens': 65536, 'thinking_level': 'medium'}`
  - 복잡한 질문이나 논리적 추론이 필요한 문제에 대해 심층 사고 후 답변 도출
- **💬 연속 대화 문맥 유지 (Multi-turn Session)**
  - `interaction_id` 및 `previous_interaction_id` 세션 연동으로 이전 질문과 답변 맥락을 완벽하게 기억
- **🌊 실시간 토큰 스트리밍 (SSE)**
  - Server-Sent Events 기반으로 지연 없는 타이핑 효과 및 실시간 마크다운 파싱/코드 하이라이트 제공
- **🎨 Gemini 공식 감성의 완성도 높은 UI/UX**
  - 딥 네이비 방사형 그라데이션 및 캡슐형(Pill shape) 다크 입력창
  - Web Speech API 기반 음성 인식(STT) 및 원클릭 코드 복사 버튼 지원

---

## 🔐 HTTP vs HTTPS 아키텍처 진화 및 전환 기술 분석

본 프로젝트는 초기 프로토타입 단계에서 **HTTP(8000번 포트)**로 구동되었으나, 브라우저의 보안 경고(`[주의 요함]`)를 해결하고 전송 계층의 보안을 극대화하기 위해 **공인 HTTPS(443번 포트)** 환경으로 아키텍처를 전면 전환했습니다.

### 1. HTTP vs HTTPS 프로토콜의 핵심 차이점

| 비교 항목 | HTTP (초기 구현) | HTTPS (현재 아키텍처) |
| :--- | :--- | :--- |
| **통신 보안** | 평문(Plaintext) 전송 (패킷 스니핑/변조에 취약) | **TLS 1.2 / 1.3 암호화** 터널 전송 (종단 간 기밀성 및 무결성 보장) |
| **브라우저 UI** | **`⚠️ 주의 요함`** 경고 뱃지 표시 | **`🔒 안전한 자물쇠 마크`** 활성화 |
| **인증서** | 없음 | **Let's Encrypt 공인 CA 인증서** (글로벌 브라우저 100% 신뢰) |
| **접속 포트** | 비표준 포트 (`:8000`) 필수 지정 | 웹 표준 보안 포트 (**443**) 적용으로 **포트 번호 생략 가능** |
| **백엔드 노출** | Uvicorn 서버가 공인 인터넷에 직접 노출 (`0.0.0.0`) | **Nginx 리버스 프록시** 뒤로 백엔드 내부 격리 (`127.0.0.1`) |

---

### 2. HTTPS 전환을 위해 도입된 핵심 기술 스택

HTTPS 환경을 구축하기 위해 Compute Engine 인스턴스 상에 다음과 같은 인프라 및 소프트웨어 기술들이 결합되었습니다:

```text
[사용자 웹 브라우저]
       │
       │  (1) HTTPS (443 포트) / TLS 암호화 세션
       ▼
[GCP VPC 방화벽 : allow-http-https (tcp:80, tcp:443)]
       │
       ▼
[Nginx 리버스 프록시 (포트 80, 443)]
  ├─ (2) sslip.io 와일드카드 DNS: 34.10.109.31.sslip.io 매핑
  ├─ (3) Let's Encrypt & Certbot: 공인 SSL 인증서 자동 발급 및 갱신
  ├─ (4) HTTP(80) ➔ HTTPS(443) 301 자동 보안 리다이렉트
  └─ (5) SSE 최적화: proxy_buffering off (실시간 스트리밍 보장)
       │
       │  (6) 로컬 루프백 내부 통신 (127.0.0.1:8000)
       ▼
[Uvicorn / FastAPI 챗봇 서비스 (systemd)]
```

#### ① Nginx 리버스 프록시 (Reverse Proxy) & SSL/TLS 종단
- **역할**: 클라이언트와 직접 마주하는 프론트엔드 웹 서버로서 SSL 암호화/복호화(SSL Termination) 처리를 전담합니다.
- **백엔드 보호**: 기존에 외부로 노출되어 있던 Uvicorn 프로세스를 내부 루프백 IP(`127.0.0.1:8000`)로 격리하여 외부의 직접적인 공격 표면(Attack Surface)을 원천 차단했습니다.
- **실시간 SSE 스트리밍 보장**: Nginx 기본 설정에서는 프록시 버퍼링으로 인해 SSE 스트리밍 텍스트가 지연될 수 있으므로, `proxy_buffering off;`, `proxy_cache off;`, `proxy_set_header Connection '';` 설정을 적용하여 Gemini의 실시간 타이핑 효과를 완벽하게 유지했습니다.

#### ② Let's Encrypt & Certbot (공인 무료 SSL 인증서)
- **역할**: 전 세계 주요 브라우저(Chrome, Safari, Edge 등)에서 신뢰하는 비영리 공인 인증기관(CA)인 **Let's Encrypt**로부터 정식 SSL/TLS 인증서를 발급받았습니다.
- **자동화 관리**: `python3-certbot-nginx` 플러그인을 통해 ACME HTTP-01 챌린지 검증, Nginx 가상 호스트 SSL 지시어 주입, 만료 전 자동 갱신(`certbot.timer`)을 자동화했습니다.

#### ③ sslip.io (와일드카드 공용 DNS)
- **도메인 문제 해결**: 공인 SSL 인증서는 IP 주소만으로는 발급에 제약이 있으며 도메인 네임이 필수적입니다. 유료 도메인을 구매하지 않고도 Compute Engine의 고정 외부 IP(`34.10.109.31`)를 DNS 상에서 즉시 유효한 도메인(`34.10.109.31.sslip.io`)으로 해석해주는 무료 공용 매핑 서비스 **sslip.io**를 활용했습니다.

#### ④ GCP VPC 방화벽 및 인스턴스 태깅 (`allow-http-https`)
- **네트워크 인프라 개방**: 웹 표준 포트인 `tcp:80`(HTTP 인증 및 리다이렉트용)과 `tcp:443`(HTTPS 보안 통신용)을 허용하는 VPC 방화벽 규칙 `allow-http-https`를 생성하고, 인스턴스에 `http-server`, `https-server` 태그를 결합하여 인바운드 트래픽을 허용했습니다.

---

## 🏗️ 아키텍처 및 폴더 구조

```text
gcp-compute-engine-chatbot/
├── compute_engine/                     # Compute Engine VM 배포 모듈 (IaaS)
│   ├── frontend/                       # 프론트엔드 소스코드 (Vite 번들러)
│   ├── static/                         # 프론트엔드 빌드 산출물
│   ├── main.py                         # FastAPI 백엔드
│   ├── requirements.txt                # 파이썬 의존성 패키지
│   ├── deploy_to_compute_engine.py     # VM 원클릭 자동 배포 스크립트
│   ├── setup_https.py                  # Nginx + Let's Encrypt SSL 원클릭 구성
│   └── compute_engine_example.ipynb    # GCP VM API 실습 노트북
├── cloud_run/                          # Cloud Run 서버리스 컨테이너 배포 모듈 (PaaS)
│   ├── frontend/                       # 프론트엔드 소스코드 (Vite)
│   ├── static/                         # 프론트엔드 빌드 산출물
│   ├── Dockerfile                      # 멀티 스테이지 최적화 컨테이너 빌드 파일
│   ├── .dockerignore                   # 컨테이너 빌드 제외 규칙
│   ├── main.py                         # FastAPI 백엔드 ($PORT 동적 바인딩)
│   ├── requirements.txt                # 백엔드 의존성
│   ├── deploy_to_cloud_run.py          # Cloud Run 원클릭 자동 빌드 & 배포 스크립트
│   └── README.md                       # Cloud Run 상세 가이드
├── .gitignore                          # Git 제외 설정 파일
└── README.md                           # 프로젝트 통합 설명서
```

---

## 🛠️ 시작하기 (Local Environment)

### 1. 사전 준비 (Prerequisites)
- **Python**: 3.10 이상 (Conda `myenv` 가상환경 권장)
- **Node.js**: 18+ 및 npm
- **Gemini API Key**: [Google AI Studio](https://aistudio.google.com/)에서 발급

### 2. 환경 변수 설정
시스템 환경변수에 `GEMINI_API_KEY`를 등록하거나, `compute_engine/` 디렉터리에 `.env` 파일을 생성합니다:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. 백엔드 패키지 설치
Conda 가상환경(`myenv`) 활성화 후 설치:
```bash
conda activate myenv
cd compute_engine
pip install -r requirements.txt
```

### 4. 프론트엔드 빌드
소스코드 수정 시 또는 최초 실행 시 `frontend` 빌드를 수행합니다:
```bash
cd frontend
npm install
npm run build
cd ..
```
> 산출물이 자동으로 `compute_engine/static/` 디렉터리에 번들링됩니다.

### 5. 서버 실행
```bash
# compute_engine 디렉터리 내에서 실행
uvicorn main:app --host 127.0.0.1 --port 8000
```
웹 브라우저에서 **`http://127.0.0.1:8000`**으로 접속합니다.

---

## ☁️ GCP Compute Engine 배포 가이드

### 방법 1. 로컬에서 원클릭 자동 배포 (권장)
로컬 터미널에서 Google Cloud SDK(gcloud CLI)가 인증된 상태라면 아래 스크립트로 VM 생성 이후의 모든 설정(아카이브 패키징, PSCP 전송, systemd 서비스 등록, Secret Manager 연동)을 전자동으로 수행할 수 있습니다:

```bash
# 1. 챗봇 서비스 자동 배포
python compute_engine/deploy_to_compute_engine.py

# 2. 공인 HTTPS 보안 적용 (Nginx + Let's Encrypt SSL)
python compute_engine/setup_https.py
```

---

### 방법 2. VM 인스턴스 직접 수동 배포
GCP Compute Engine (Ubuntu/Debian Linux VM)에 직접 접속하여 배포할 때의 절차입니다:

```bash
# 1. 저장소 클론 및 compute_engine 서브 폴더 이동
git clone https://github.com/your-username/gcp-compute-engine-chatbot.git
cd gcp-compute-engine-chatbot/compute_engine

# 2. Python 가상환경 구성 및 패키지 설치
sudo apt update && sudo apt install -y python3-pip python3-venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. 환경변수 등록 (.env 파일 또는 export)
export GEMINI_API_KEY="your_api_key"

# 4. 백그라운드 서비스(systemd 또는 nohup) 실행
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
```
브라우저에서 `http://<외부_IP>:8000`으로 접속하여 챗봇을 사용하실 수 있습니다.

---

## ⚡ Google Cloud Run 서버리스 배포 가이드

서버리스 완전 관리형 환경(Scale-to-Zero, 요청 없을 시 비용 0원, 자동 HTTPS)으로 운영하고자 할 경우 `cloud_run` 모듈을 사용합니다:

### 원클릭 자동 빌드 & 배포 (권장)
```bash
# Cloud Build 원격 컨테이너 빌드, Secret Manager 연동, Cloud Run 배포를 전자동으로 실행
python cloud_run/deploy_to_cloud_run.py
```
> 배포 완료 후 터미널에 생성된 공인 HTTPS 주소(`https://gemini-chatbot-run-xxxx.a.run.app`)로 즉시 접속 가능합니다.

자세한 로컬 테스트 및 Docker 빌드 가이드는 [cloud_run/README.md](file:///c:/Users/butte/github/Project/gcp-compute-engine-chatbot/cloud_run/README.md)를 참고하세요.

---

## 📜 라이선스
이 프로젝트는 개인 및 학습/상업적 용도로 자유롭게 수정 및 배포할 수 있습니다.
