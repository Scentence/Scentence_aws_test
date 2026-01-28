from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import ORJSONResponse

from scentmap.app.schemas.session_schema import (
    SessionStartRequest,
    SessionStartResponse,
    ActivityLogRequest,
    ActivityLogResponse,
    GenerateCardResponse,
    SaveCardRequest,
    SaveCardResponse,
    MyCardsResponse
)
from scentmap.app.services.session_service import (
    create_session,
    update_session_activity,
    check_card_trigger,
    generate_template_card,
    generate_llm_card,
    save_card,
    get_my_cards,
    DailyLimitExceededError
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
            trigger_message=trigger_result.get("message"),
            daily_limit_reached=trigger_result.get("daily_limit_reached"),
            daily_limit_remaining=trigger_result.get("daily_limit_remaining")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"활동 로깅 실패: {str(e)}")


@router.post("/{session_id}/generate-card", response_model=GenerateCardResponse)
def generate_card(
    session_id: str,
    use_template: bool = Query(False, description="템플릿 모드 사용 (LLM 없이)"),
    use_simple_model: bool = Query(True, description="간단한 모델 사용 (gpt-4o-mini)")
):
    """
    향기카드 생성
    
    Phase 2: LLM 기반 생성 (기본)
    - OpenAI GPT를 활용한 자연스러운 스토리 생성
    - 실패 시 자동으로 템플릿 폴백
    
    Phase 3: MBTI 통합
    - 회원인 경우 MBTI 정보를 카드에 포함
    - "INFJ인 당신은..." 형태로 개인화
    
    Query Parameters:
    - use_template: True이면 LLM 없이 템플릿만 사용
    - use_simple_model: True이면 gpt-4o-mini, False이면 gpt-4o (기본: True)
    """
    try:
        if use_template:
            # 템플릿 모드: LLM 없이 고정 문구
            card = generate_template_card(session_id)
        else:
            # LLM 모드: 자연스러운 스토리 생성 (MBTI 통합, 폴백 포함)
            card = generate_llm_card(session_id, use_simple_model=use_simple_model)
        
        import logging
        logger = logging.getLogger(__name__)

        # card_id 누락 방지: 세션의 최신 카드로 보정
        if not card.get("card_id") or not card.get("card"):
            logger.warning(f"card_id 또는 card 누락 감지, DB에서 보정 시도")
            try:
                from scentmap.db import get_recom_db_connection

                with get_recom_db_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            SELECT card_id, generation_method, card_data
                            FROM TB_SCENT_CARD_RESULT_T
                            WHERE session_id = %s
                            ORDER BY created_dt DESC
                            LIMIT 1
                        """, (session_id,))
                        row = cur.fetchone()
                        if row:
                            card["card_id"] = str(row[0])
                            if "generation_method" not in card and row[1]:
                                card["generation_method"] = row[1]
                            if not card.get("card") and row[2]:
                                card["card"] = row[2]
                            logger.info(f"card_id 보정 성공: session={session_id}, card_id={card['card_id']}")
                        else:
                            logger.error(f"보정 실패: DB에 카드가 없음 (session={session_id})")
            except Exception as lookup_error:
                logger.error(f"card_id 보정 중 예외 발생: {lookup_error}", exc_info=True)
        
        # 혹시 card 내부에 card_id가 있는 구형 응답 구조라면 상위로 끌어올림
        if not card.get("card_id") and isinstance(card.get("card"), dict):
            nested_card_id = card["card"].get("card_id")
            if nested_card_id:
                card["card_id"] = str(nested_card_id)
                logger.info(f"card 내부에서 card_id 보정: session={session_id}, card_id={card['card_id']}")

        # 상위 card_id를 card 내부에도 주입 (클라이언트 호환성)
        if card.get("card_id") and isinstance(card.get("card"), dict):
            card["card"]["card_id"] = card["card_id"]
        
        # card_id 최종 검증
        if not card.get('card_id'):
            logger.error(f"card_id 최종 검증 실패")
            raise ValueError("카드 생성 중 card_id를 받지 못했습니다")
        
        # Pydantic 응답 모델 생성
        try:
            response = GenerateCardResponse(**card)
            logger.info(f"카드 API 응답 생성 완료: card_id={response.card_id}")
            
            return response
        except Exception as pydantic_error:
            logger.error(f"Pydantic 모델 생성 실패: {pydantic_error}", exc_info=True)
            raise
    except DailyLimitExceededError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"카드 생성 실패: {str(e)}")


@router.post("/{session_id}/save-card", response_model=SaveCardResponse)
def save_generated_card(
    session_id: str,
    request: SaveCardRequest,
    member_id: int = Query(..., description="회원 ID (필수)")
):
    """
    생성된 카드 저장 (회원 전용)
    
    Phase 3: 카드 저장 기능
    - 회원만 카드를 저장할 수 있음
    - 마이페이지에서 저장된 카드 조회 가능
    """
    try:
        result = save_card(request.card_id, member_id)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
        
        return SaveCardResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"카드 저장 실패: {str(e)}")


@router.get("/my-cards", response_model=MyCardsResponse)
def get_member_cards(
    member_id: int = Query(..., description="회원 ID (필수)"),
    limit: int = Query(20, ge=1, le=100, description="조회 개수 (1-100)"),
    offset: int = Query(0, ge=0, description="오프셋")
):
    """
    내 카드 조회 (회원 전용)
    
    Phase 3: 마이페이지 카드 조회
    - 저장된 카드 목록 조회
    - 페이지네이션 지원
    """
    try:
        result = get_my_cards(member_id, limit, offset)
        return MyCardsResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"카드 조회 실패: {str(e)}")


@router.post("/{session_id}/feedback")
def submit_feedback(
    session_id: str,
    card_id: str = Query(..., description="카드 ID"),
    feedback: str = Query(..., description="positive or negative")
):
    # 피드백 API 엔드포인트
    """
    카드 피드백 제출
    
    Phase 4: 사용자 피드백 수집
    - 사용자가 카드에 대한 평가 제출
    - TB_SCENT_CARD_RESULT_T.user_feedback 업데이트
    """
    try:
        from scentmap.db import get_recom_db_connection
        import logging
        
        logger = logging.getLogger(__name__)
        logger.info(f"피드백 저장 시도: session={session_id}, card={card_id}, feedback={feedback}")
        
        # 입력값 유효성 검사
        if feedback not in ["positive", "negative"]:
            logger.warning(f"잘못된 피드백 값: {feedback}")
            raise HTTPException(
                status_code=400, 
                detail=f"피드백 값은 'positive' 또는 'negative'여야 합니다. 받은 값: {feedback}"
            )
        
        with get_recom_db_connection() as conn:
            with conn.cursor() as cur:
                # 먼저 카드가 존재하는지 확인
                cur.execute("""
                    SELECT card_id, session_id, user_feedback 
                    FROM TB_SCENT_CARD_RESULT_T
                    WHERE card_id = %s::uuid AND session_id = %s
                """, (card_id, session_id))
                
                existing_card = cur.fetchone()
                
                if not existing_card:
                    logger.warning(f"카드를 찾을 수 없음: card_id={card_id}, session_id={session_id}")
                    raise HTTPException(
                        status_code=404, 
                        detail=f"카드를 찾을 수 없습니다 (card_id={card_id}, session_id={session_id})"
                    )
                
                # UUID 타입으로 변환하여 UPDATE
                cur.execute("""
                    UPDATE TB_SCENT_CARD_RESULT_T
                    SET user_feedback = %s
                    WHERE card_id = %s::uuid AND session_id = %s
                """, (feedback, card_id, session_id))
                
                updated_rows = cur.rowcount
                conn.commit()
                
                logger.info(f"피드백 저장 완료: {updated_rows}개 행 업데이트 (feedback={feedback})")
        
        return {
            "success": True, 
            "message": "피드백이 저장되었습니다",
            "feedback": feedback
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"피드백 저장 에러: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"피드백 저장 실패: {str(e)}")


@router.post("/{session_id}/update-mbti")
def update_member_mbti(
    session_id: str,
    member_id: int = Query(..., description="회원 ID"),
    mbti: str = Query(..., description="MBTI 유형")
):
    """
    회원 MBTI 업데이트 (임시 저장)
    
    Phase 4: MBTI 입력 기능
    - 세션에 MBTI 저장
    - 다음 카드 생성 시 사용
    - TODO: 실제 회원 DB에 저장하려면 별도 처리 필요
    """
    try:
        from scentmap.db import get_recom_db_connection
        
        # 세션에 임시 저장 (device_type 필드 활용)
        with get_recom_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE TB_SCENT_CARD_SESSION_T
                    SET device_type = %s
                    WHERE session_id = %s
                """, (f"mbti:{mbti}", session_id))
                conn.commit()
        
        return {"success": True, "mbti": mbti}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MBTI 업데이트 실패: {str(e)}")
