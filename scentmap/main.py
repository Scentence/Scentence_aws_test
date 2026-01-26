from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import logging
from contextlib import asynccontextmanager
import os

from scentmap.db import init_db_schema, close_pool
from scentmap.app.api.network import router as network_router
from scentmap.app.api.label import router as labels_router

from scentmap.app.services.label_service import load_labels

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버 시작 시 초기화
    logger.info("🚀 Scentmap 서비스 시작 중...")
    
    # 1. 테이블 자동 생성 (없으면 만듦)
    init_db_schema()
    
    # 2. 라벨 데이터 사전 로드
    try:
        load_labels()
        logger.info("✅ 라벨 데이터 로드 완료")
    except Exception as e:
        logger.error(f"⚠️ 라벨 데이터 로드 실패: {e}")
        logger.warning("서비스는 계속 실행되지만 라벨 데이터는 첫 요청 시 로드됩니다.")
    
    logger.info("⚡ 서버 준비 완료")
    
    yield
    
    # 서버 종료 시 정리
    logger.info("🛑 Scentmap 서비스 종료 중...")
    close_pool()


app = FastAPI(title="Scentmap Service", lifespan=lifespan)

origins_env = os.getenv("CORS_ORIGINS")
if origins_env:
    origins = [origin.strip() for origin in origins_env.split(",") if origin.strip()]
else:
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 대용량 응답 압축 (네트워크 데이터 전송 시간 단축)
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.include_router(network_router)
app.include_router(labels_router)


@app.get("/")
def root():
    return {"message": "Scentmap service is running!"}


@app.get("/health")
def health():
    return {"status": "ok", "service": "scentmap"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("scentmap.main:app", host="0.0.0.0", port=8001, reload=True)
