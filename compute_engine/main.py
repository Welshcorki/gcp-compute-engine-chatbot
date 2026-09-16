import os
import json
import asyncio
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from google import genai

load_dotenv()

app = FastAPI(title="Gemini Web Chatbot", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_gemini_client():
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        # GCP Secret Manager fallback
        try:
            from google.cloud import secretmanager
            client = secretmanager.SecretManagerServiceClient()
            secret_name = "projects/584903808975/secrets/GEMINI_API_KEY/versions/latest"
            response = client.access_secret_version(request={"name": secret_name})
            api_key = response.payload.data.decode("UTF-8").strip()
            # 캐싱용으로 환경변수에 저장
            os.environ["GEMINI_API_KEY"] = api_key
        except Exception as sm_err:
            pass

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY 환경변수가 설정되지 않았으며 Secret Manager에서도 읽어오지 못했습니다."
        )
    return genai.Client(api_key=api_key)

class MessageItem(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: Optional[List[MessageItem]] = None
    input: Optional[str] = None
    model: Optional[str] = "models/gemini-3.8-flash"
    previous_interaction_id: Optional[str] = None

AVAILABLE_MODELS = [
    {
        "id": "models/gemini-3.8-flash",
        "name": "Gemini 3.8 Flash",
        "badge": "Flash",
        "description": "최신 고속 차세대 모델 + Google Search + Thinking (기본 권장)",
        "is_default": True
    },
    {
        "id": "models/gemini-3.7-flash",
        "name": "Gemini 3.7 Flash",
        "badge": "Flash 3.7",
        "description": "다목적 고성능 플래시 모델 + Google Search",
        "is_default": False
    }
]

# 사용자 정의 도구 및 생성 파라미터 설정
DEFAULT_TOOLS = [
    {
        'type': 'google_search',
    },
]

DEFAULT_GENERATION_CONFIG = {
    'max_output_tokens': 65536,
    'thinking_level': 'medium',
}

@app.get("/api/models")
async def get_models():
    return {"models": AVAILABLE_MODELS}

@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    client = get_gemini_client()
    
    # 모델명 정규화
    model_id = request.model or "models/gemini-3.8-flash"
    if not model_id.startswith("models/"):
        model_id = f"models/{model_id}"

    # 입력 텍스트 추출
    user_input = request.input
    if not user_input and request.messages:
        # 마지막 사용자 메시지 가져오기
        for msg in reversed(request.messages):
            if msg.role in ["user", "human"]:
                user_input = msg.content
                break
    
    if not user_input:
        raise HTTPException(status_code=400, detail="입력 메시지가 비어있습니다.")

    # previous_interaction_id 파라미터
    prev_id = request.previous_interaction_id if request.previous_interaction_id else None

    async def event_generator():
        loop = asyncio.get_event_loop()

        def run_interaction_stream():
            kwargs = {
                "model": model_id,
                "input": user_input,
                "tools": DEFAULT_TOOLS,
                "generation_config": DEFAULT_GENERATION_CONFIG,
                "stream": True,
            }
            if prev_id:
                kwargs["previous_interaction_id"] = prev_id
            return client.interactions.create(**kwargs)

        try:
            # Interactions 스트림 생성 (비동기 executor 활용)
            stream = await loop.run_in_executor(None, run_interaction_stream)

            new_interaction_id = None
            citations = []

            for event in stream:
                # 1. 새 Interaction ID 수신
                if event.event_type == "interaction.created" and hasattr(event, "interaction"):
                    new_interaction_id = event.interaction.id
                    payload = json.dumps({"interaction_id": new_interaction_id}, ensure_ascii=False)
                    yield f"data: {payload}\n\n"

                # 2. 텍스트 델타 수신 (실시간 스트리밍 출력)
                elif event.event_type == "step.delta" and hasattr(event, "delta"):
                    delta = event.delta
                    if hasattr(delta, "text") and delta.text:
                        payload = json.dumps({"text": delta.text}, ensure_ascii=False)
                        yield f"data: {payload}\n\n"
                        await asyncio.sleep(0.005)

                # 3. 모델 출력 완료 및 인용 정보 수집
                elif event.event_type == "step.stop":
                    pass

                elif event.event_type == "interaction.completed":
                    pass

            yield "data: [DONE]\n\n"

        except Exception as e:
            error_payload = json.dumps({"error": str(e)}, ensure_ascii=False)
            yield f"data: {error_payload}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

# Static files mount
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = os.path.join(static_dir, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(static_dir, "index.html"))
else:
    @app.get("/")
    async def index_fallback():
        return {
            "message": "Gemini 챗봇 API 서버가 동작 중입니다. frontend를 빌드하여 static 폴더를 생성해주세요."
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
