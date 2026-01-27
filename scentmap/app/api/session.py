from fastapi import APIRouter, HTTPException
from fastapi.responses import ORJSONResponse

from scentmap.app.schemas.session_schema import (
    SessionStartRequest,
    SessionStartResponse,
    ActivityLogRequest,
    ActivityLogResponse,
    GenerateCardResponse
)
from scentmap.app.services.session_service import (
    create_session,
    update_session_activity,
    check_card_trigger,
    generate_template_card
)

router = APIRouter(prefix="/session", tags=["session"])


@router.post("/start", response_model=SessionStartResponse)
def start_session(request: SessionStartRequest):
    """
    향수맵 탐색 세션 시작
    
    - 세션 ID 발급
    - 회원/비회원 구분
    - 비침투적 로깅 시작
    """
    try:
        session = create_session(member_id=request.member_id)
        return SessionStartResponse(session_id=session["session_id"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"세션 생성 실패: {str(e)}")


@router.post("/{session_id}/activity", response_model=ActivityLogResponse)
def log_activity(session_id: str, request: ActivityLogRequest):
    """
    사용자 활동 로깅 (비침투적)
    
    - 어코드 선택
    - 향수 반응 (좋아요/관심/패스)
    - 카드 생성 조건 자동 체크
    """
    try:
        # 활동 로깅
        update_session_activity(
            session_id=session_id,
            accord_selected=request.accord_selected,
            perfume_id=request.perfume_id,
            reaction=request.reaction
        )
        
        # 카드 생성 조건 체크
        trigger_result = check_card_trigger(session_id)
        
        return ActivityLogResponse(
            logged=True,
            card_trigger_ready=trigger_result["ready"],
            trigger_message=trigger_result.get("message")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"활동 로깅 실패: {str(e)}")


@router.post("/{session_id}/generate-card", response_model=GenerateCardResponse)
def generate_card(session_id: str):
    """
    향기카드 생성
    
    Phase 1: 템플릿 기반 생성
    - CSV 설명을 활용한 고정 문구
    - LLM 없이 간단한 조합
    
    Phase 2: LLM 기반 생성 (향후)
    """
    try:
        card = generate_template_card(session_id)
        return GenerateCardResponse(**card)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"카드 생성 실패: {str(e)}")
