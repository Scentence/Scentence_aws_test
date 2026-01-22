from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# [추가] DB 초기화 및 종료 함수 임포트
from scentmap.db import init_db_schema, close_pool
from scentmap.app.api.network_data import router as network_router


# [추가] 앱 수명주기 관리 (시작 시 테이블 생성 -> 종료 시 연결 해제)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. 서버 시작 시: 테이블 자동 생성 (없으면 만듦)
    init_db_schema()
    yield
    # 2. 서버 종료 시: 커넥션 풀 닫기
    close_pool()


# [수정] lifespan 파라미터 추가
app = FastAPI(title="Scentmap Service", lifespan=lifespan)

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

app.include_router(network_router)


@app.get("/")
def root():
    return {"message": "Scentmap service is running!"}


@app.get("/health")
def health():
    return {"status": "ok", "service": "scentmap"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("scentmap.main:app", host="0.0.0.0", port=8001, reload=True)
