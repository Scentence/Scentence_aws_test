import json
import time
from typing import Generator, List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
import os

# [수정] AIMessage 추가 임포트
from langchain_core.messages import HumanMessage, AIMessage

# 모듈 임포트
from agent.schemas import ChatRequest
from agent.graph import app_graph

# [추가] DB 관련 함수 임포트
from agent.database import save_chat_message, get_chat_history, get_user_chat_list

# Frontend에서 가져온 유저 라우터
from routers import users

app = FastAPI(title="Perfume Re-Act Chatbot")

uploads_dir = os.path.join(os.getcwd(), "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# 유저 라우터 등록
app.include_router(users.router)

# CORS 설정
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


# =================================================================
# 핵심 로직: 스트림 제너레이터 (History 저장 및 복원 로직 추가)
# =================================================================
async def stream_generator(
    user_query: str, thread_id: str, member_id: int = 0
) -> Generator[str, None, None]:

    # [1] 사용자 메시지 DB 저장 (User Turn)
    # -----------------------------------------------------------
    save_chat_message(thread_id, member_id, "user", user_query)
    # -----------------------------------------------------------

    config = {"configurable": {"thread_id": thread_id}}

    # [2] 문맥 복원: DB에서 해당 스레드의 과거 대화 내역 로드
    # -----------------------------------------------------------
    db_history = get_chat_history(thread_id)
    restored_messages = []

    for msg in db_history:
        # 현재 보낸 질문이 DB에 이미 들어갔으므로 중복 방지
        if msg["role"] == "user" and msg["text"] == user_query:
            continue

        if msg["role"] == "user":
            restored_messages.append(HumanMessage(content=msg["text"]))
        else:
            restored_messages.append(AIMessage(content=msg["text"]))

    # 과거 내역 + 현재 질문을 합쳐서 그래프 입력으로 전달
    inputs = {
        "messages": restored_messages + [HumanMessage(content=user_query)],
        "member_id": member_id,
    }
    # -----------------------------------------------------------

    # AI 답변 전체를 저장하기 위한 누적 변수
    full_ai_response = ""

    try:
        async for event in app_graph.astream_events(
            inputs, config=config, version="v2"
        ):
            kind = event["event"]
            metadata = event.get("metadata", {})
            node_name = metadata.get("langgraph_node", "")

            # [A] Writer: 실시간 스트리밍
            if kind == "on_chat_model_stream":
                if node_name == "writer":
                    content = event["data"]["chunk"].content
                    if content:
                        full_ai_response += content  # 답변 누적
                        data = json.dumps(
                            {"type": "answer", "content": content}, ensure_ascii=False
                        )
                        yield f"data: {data}\n\n"

            # [B] Interviewer: 결과 전송
            elif kind == "on_chain_end" and node_name == "interviewer":
                output = event["data"].get("output")
                if output and isinstance(output, dict):
                    messages = output.get("messages")
                    if messages and len(messages) > 0:
                        last_msg = messages[-1]
                        if hasattr(last_msg, "content") and last_msg.content:
                            full_ai_response += last_msg.content  # 답변 누적
                            data = json.dumps(
                                {"type": "answer", "content": last_msg.content},
                                ensure_ascii=False,
                            )
                            yield f"data: {data}\n\n"

            # [C] Researcher (로그): 도구 사용 알림
            elif kind == "on_chat_model_end" and node_name == "researcher":
                output = event["data"].get("output")
                if output and hasattr(output, "tool_calls") and output.tool_calls:
                    tool_name = output.tool_calls[0]["name"]
                    log_msg = f"🔎 [검색 중] {tool_name} 도구를 사용하고 있습니다..."
                    data = json.dumps(
                        {"type": "log", "content": log_msg}, ensure_ascii=False
                    )
                    yield f"data: {data}\n\n"

            # [D] Tools (로그): 데이터 조회 완료
            elif kind == "on_chain_end" and node_name == "tools":
                log_msg = "✅ 데이터 조회 완료! 분석 중입니다..."
                data = json.dumps(
                    {"type": "log", "content": log_msg}, ensure_ascii=False
                )
                yield f"data: {data}\n\n"

        # [3] AI 답변 완료 후 DB 저장 (Assistant Turn)
        # -----------------------------------------------------------
        if full_ai_response:
            save_chat_message(thread_id, member_id, "assistant", full_ai_response)
        # -----------------------------------------------------------

    except GeneratorExit:
        print(f"👋 Client disconnected (Thread: {thread_id})")
        return
    except Exception as e:
        print(f"🚨 Server Error: {e}")
        error_msg = json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False)
        yield f"data: {error_msg}\n\n"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat")
async def chat_stream(request: ChatRequest):
    return StreamingResponse(
        stream_generator(request.user_query, request.thread_id, request.member_id),
        media_type="text/event-stream",
    )


# =================================================================
# 신규 추가: 채팅 히스토리 관련 API
# =================================================================


@app.get("/chat/rooms/{member_id}")
async def get_rooms(member_id: int):
    """사용자의 채팅방 목록 조회 (사이드바용)"""
    rooms = get_user_chat_list(member_id)
    return {"rooms": rooms}


@app.get("/chat/history/{thread_id}")
async def get_history(thread_id: str):
    """특정 채팅방의 과거 대화 내역 조회"""
    messages = get_chat_history(thread_id)
    return {"messages": messages}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
