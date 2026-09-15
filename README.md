# 🚀 GCP Compute Engine Gemini Chatbot

Google Cloud Platform (GCP)의 **Compute Engine** 인스턴스 배포를 고려하여 설계된 고성능 **Gemini 3.8 Flash & 3.7 Flash 웹 챗봇 서비스**입니다.

Google GenAI 공식 SDK의 최신 **Interactions API**(`client.interactions.create`)를 도입하여 **실시간 웹 검색(Google Search Grounding)** 및 **사고/추론(Thinking Level: Medium)**이 결합된 고지능 스트리밍 답변을 제공합니다. 또한 공식 Gemini 웹사이트 감성을 정밀하게 재현한 프리미엄 다크 테마 UI와 음성 입력(STT) 기능을 탑재하고 있습니다.

---

## ✨ 주요 기능

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

## 🏗️ 아키텍처 및 폴더 구조

```text
gcp-compute-engine-chatbot/
├── frontend/             # 프론트엔드 소스코드 (Vite 번들러)
│   ├── src/
│   │   ├── main.js       # 상태 관리, SSE 통신, 음성인식, 마크다운 렌더링
│   │   └── style.css     # Gemini 스타일 프리미엄 다크 디자인 시스템
│   ├── index.html        # 메인 HTML
│   ├── vite.config.js    # build outDir -> ../static 설정
│   └── package.json
├── static/               # 프론트엔드 빌드 산출물 (FastAPI가 서빙)
│   ├── assets/
│   └── index.html
├── main.py               # FastAPI 백엔드 (Interactions API 및 정적 파일 호스팅)
├── requirements.txt      # 파이썬 의존성 패키지 목록
├── .gitignore            # Git 제외 설정 파일
└── README.md             # 프로젝트 설명서
```

---

## 🛠️ 시작하기 (Local Environment)

### 1. 사전 준비 (Prerequisites)
- **Python**: 3.10 이상 (Conda `myenv` 가상환경 권장)
- **Node.js**: 18+ 및 npm
- **Gemini API Key**: [Google AI Studio](https://aistudio.google.com/)에서 발급

### 2. 환경 변수 설정
시스템 환경변수에 `GEMINI_API_KEY`를 등록하거나, 프로젝트 루트에 `.env` 파일을 생성합니다:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. 백엔드 패키지 설치
Conda 가상환경(`myenv`) 활성화 후 설치:
```bash
conda activate myenv
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
> 산출물이 자동으로 상위 `static/` 디렉터리에 번들링됩니다.

### 5. 서버 실행
```bash
# Conda myenv 가상환경 적용 실행
conda run -n myenv uvicorn main:app --host 127.0.0.1 --port 8000
```
웹 브라우저에서 **`http://127.0.0.1:8000`**으로 접속합니다.

---

## ☁️ GCP Compute Engine 배포 가이드

GCP Compute Engine (Ubuntu/Debian Linux VM)에 배포할 때의 기본 절차입니다.

### 1. 인스턴스 방화벽 설정
- GCP 콘솔 > **VPC 네트워크** > **방화벽 규칙**에서 `tcp:8000` (또는 `tcp:80`) 포트 인바운드 허용

### 2. VM 인스턴스 접속 및 설정
```bash
# 저장소 클론
git clone https://github.com/your-username/gcp-compute-engine-chatbot.git
cd gcp-compute-engine-chatbot

# Python 및 Node.js 설치 (필요 시)
sudo apt update && sudo apt install -y python3-pip python3-venv

# 가상환경 생성 및 패키지 설치
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 환경변수 등록 (.env 파일 또는 export)
export GEMINI_API_KEY="your_api_key"

# 백그라운드 서비스(systemd 또는 nohup) 실행
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
```
브라우저에서 `http://<외부_IP>:8000`으로 접속하여 챗봇을 사용하실 수 있습니다.

---

## 📜 라이선스
이 프로젝트는 개인 및 학습/상업적 용도로 자유롭게 수정 및 배포할 수 있습니다.
