# ==============================================================================
# Stage 1: Build Frontend (Node.js 20)
# ==============================================================================
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend

# 의존성 정의 파일 복사 및 설치
COPY frontend/package*.json ./
RUN npm ci --silent || npm install

# 프론트엔드 소스 복사 및 Vite 번들링
COPY frontend/ ./
RUN npm run build

# ==============================================================================
# Stage 2: Runtime Environment (Python 3.11 Slim)
# ==============================================================================
FROM python:3.11-slim
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 백엔드 소스 복사
COPY main.py .

# Stage 1에서 빌드된 최신 정적 산출물(static)을 런타임 이미지로 복사
COPY --from=frontend-builder /app/static ./static

# Cloud Run 기본 포트 노출
EXPOSE 8080

# Cloud Run 주입 환경변수 $PORT를 동적으로 수신하여 Uvicorn 구동
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT}
