import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import psycopg2.extras
from scentmap.db import get_recom_db_connection, get_db_connection

logger = logging.getLogger(__name__)


def create_session(member_id: Optional[int] = None) -> Dict:
    """
    새 탐색 세션 생성
    
    Args:
        member_id: 회원 ID (비회원은 None)
    
    Returns:
        session_id를 포함한 세션 정보
    """
    session_id = str(uuid.uuid4())
    
    try:
        with get_recom_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO TB_SCENT_CARD_SESSION_T (
                        session_id,
                        member_id,
                        selected_accords,
                        liked_perfume_ids,
                        interested_perfume_ids,
                        passed_perfume_ids,
                        exploration_time,
                        interaction_count
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    session_id,
                    member_id,
                    [],  # 빈 배열
                    [],
                    [],
                    [],
                    0,
                    0
                ))
                conn.commit()
        
        logger.info(f"✅ 세션 생성 완료: {session_id}")
        return {"session_id": session_id, "member_id": member_id}
    
    except Exception as e:
        logger.error(f"❌ 세션 생성 실패: {e}")
        raise


def update_session_activity(
    session_id: str,
    accord_selected: Optional[str] = None,
    perfume_id: Optional[int] = None,
    reaction: Optional[str] = None
):
    """
    세션 활동 업데이트 (비침투적 로깅)
    
    Args:
        session_id: 세션 ID
        accord_selected: 선택된 어코드
        perfume_id: 향수 ID
        reaction: 반응 ('liked', 'interested', 'passed')
    """
    try:
        with get_recom_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # 현재 세션 정보 조회
                cur.execute("""
                    SELECT 
                        selected_accords,
                        liked_perfume_ids,
                        interested_perfume_ids,
                        passed_perfume_ids,
                        interaction_count,
                        session_start_dt
                    FROM TB_SCENT_CARD_SESSION_T
                    WHERE session_id = %s
                """, (session_id,))
                
                session = cur.fetchone()
                if not session:
                    logger.warning(f"⚠️ 세션을 찾을 수 없음: {session_id}")
                    return
                
                # 기존 데이터 가져오기
                selected_accords = list(session['selected_accords'] or [])
                liked_ids = list(session['liked_perfume_ids'] or [])
                interested_ids = list(session['interested_perfume_ids'] or [])
                passed_ids = list(session['passed_perfume_ids'] or [])
                interaction_count = session['interaction_count'] or 0
                
                # 데이터 업데이트
                if accord_selected and accord_selected not in selected_accords:
                    selected_accords.append(accord_selected)
                
                if perfume_id and reaction:
                    if reaction == 'liked' and perfume_id not in liked_ids:
                        liked_ids.append(perfume_id)
                    elif reaction == 'interested' and perfume_id not in interested_ids:
                        interested_ids.append(perfume_id)
                    elif reaction == 'passed' and perfume_id not in passed_ids:
                        passed_ids.append(perfume_id)
                
                interaction_count += 1
                
                # 탐색 시간 계산 (초)
                session_start = session['session_start_dt']
                exploration_time = int((datetime.now() - session_start).total_seconds())
                
                # DB 업데이트
                cur.execute("""
                    UPDATE TB_SCENT_CARD_SESSION_T
                    SET 
                        selected_accords = %s,
                        liked_perfume_ids = %s,
                        interested_perfume_ids = %s,
                        passed_perfume_ids = %s,
                        interaction_count = %s,
                        exploration_time = %s,
                        last_activity_dt = CURRENT_TIMESTAMP
                    WHERE session_id = %s
                """, (
                    selected_accords,
                    liked_ids,
                    interested_ids,
                    passed_ids,
                    interaction_count,
                    exploration_time,
                    session_id
                ))
                conn.commit()
                
                logger.info(f"✅ 세션 활동 업데이트: {session_id}")
    
    except Exception as e:
        logger.error(f"❌ 세션 활동 업데이트 실패: {e}")
        raise


def check_card_trigger(session_id: str) -> Dict:
    """
    카드 생성 조건 충족 여부 확인
    
    조건:
    - 어코드 선택: 1개 이상
    - 향수 반응: 3개 이상 (liked or interested)
    - 탐색 시간: 60초 이상
    - 상호작용: 5회 이상
    
    Returns:
        ready: 조건 충족 여부
        message: 제안 메시지
    """
    try:
        with get_recom_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT 
                        selected_accords,
                        liked_perfume_ids,
                        interested_perfume_ids,
                        interaction_count,
                        exploration_time
                    FROM TB_SCENT_CARD_SESSION_T
                    WHERE session_id = %s
                """, (session_id,))
                
                session = cur.fetchone()
                if not session:
                    return {"ready": False}
                
                accord_count = len(session['selected_accords'] or [])
                reaction_count = len(session['liked_perfume_ids'] or []) + len(session['interested_perfume_ids'] or [])
                interaction_count = session['interaction_count'] or 0
                exploration_time = session['exploration_time'] or 0
                
                # 조건 체크
                ready = (
                    accord_count >= 1 and
                    reaction_count >= 3 and
                    exploration_time >= 60 and
                    interaction_count >= 5
                )
                
                message = None
                if ready:
                    message = "💫 취향이 쌓였어요! 지금까지 탐색한 향으로 향기카드를 만들어볼까요?"
                
                logger.info(
                    f"🔍 카드 트리거 체크: session={session_id}, "
                    f"accord={accord_count}, reaction={reaction_count}, "
                    f"time={exploration_time}s, interaction={interaction_count}, "
                    f"ready={ready}"
                )
                
                return {"ready": ready, "message": message}
    
    except Exception as e:
        logger.error(f"❌ 카드 트리거 체크 실패: {e}")
        return {"ready": False}


def get_accord_descriptions(accord_names: List[str]) -> List[Dict]:
    """
    어코드 설명 조회 (DB 직접 조회)
    
    Args:
        accord_names: 어코드 이름 리스트
    
    Returns:
        어코드 설명 리스트
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT accord, desc1, desc2, desc3
                    FROM TB_ACCORD_DESC_M
                    WHERE accord = ANY(%s)
                """, (accord_names,))
                
                results = cur.fetchall()
                
                descriptions = []
                for row in results:
                    descriptions.append({
                        "accord": row['accord'],
                        "desc1": row['desc1'],
                        "desc2": row['desc2'],
                        "desc3": row['desc3']
                    })
                
                logger.info(f"✅ 어코드 설명 조회 완료: {len(descriptions)}개")
                return descriptions
    
    except Exception as e:
        logger.error(f"❌ 어코드 설명 조회 실패: {e}")
        return []


def generate_template_card(session_id: str) -> Dict:
    """
    템플릿 기반 향기카드 생성 (LLM 없이)
    
    Args:
        session_id: 세션 ID
    
    Returns:
        향기카드 데이터
    """
    try:
        # 세션 데이터 조회
        with get_recom_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT 
                        member_id,
                        selected_accords,
                        liked_perfume_ids,
                        interested_perfume_ids
                    FROM TB_SCENT_CARD_SESSION_T
                    WHERE session_id = %s
                """, (session_id,))
                
                session = cur.fetchone()
                if not session:
                    raise ValueError(f"세션을 찾을 수 없습니다: {session_id}")
                
                selected_accords = session['selected_accords'] or []
                if not selected_accords:
                    raise ValueError("선택된 어코드가 없습니다")
        
        # 어코드 설명 조회
        descriptions = get_accord_descriptions(selected_accords)
        
        if not descriptions:
            raise ValueError("어코드 설명을 찾을 수 없습니다")
        
        # 템플릿 카드 생성
        primary_accord = descriptions[0]
        accord_list = [d['accord'] for d in descriptions]
        
        # 간단한 제목 생성
        if len(accord_list) == 1:
            title = f"{accord_list[0]}의 향기"
        elif len(accord_list) == 2:
            title = f"{accord_list[0]}와 {accord_list[1]}"
        else:
            title = f"{accord_list[0]} 외 {len(accord_list)-1}가지 향"
        
        # 스토리 생성 (템플릿)
        story = f"당신이 선택한 {primary_accord['accord']}는 {primary_accord['desc1']}. "
        if len(descriptions) > 1:
            story += f"함께 선택한 향들이 조화를 이루며 당신만의 분위기를 만들어냅니다."
        else:
            story += f"{primary_accord['desc2']}이 특징입니다."
        
        # 어코드 정보 구성
        accords = []
        for desc in descriptions:
            accords.append({
                "name": desc['accord'],
                "description": desc['desc1']
            })
        
        card_data = {
            "title": title,
            "story": story,
            "accords": accords,
            "created_at": datetime.now().isoformat()
        }
        
        # 카드 결과 저장
        with get_recom_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO TB_SCENT_CARD_RESULT_T (
                        session_id,
                        member_id,
                        card_data,
                        generation_method
                    ) VALUES (%s, %s, %s, %s)
                """, (
                    session_id,
                    session['member_id'],
                    psycopg2.extras.Json(card_data),
                    'template'
                ))
                
                # 세션 업데이트
                cur.execute("""
                    UPDATE TB_SCENT_CARD_SESSION_T
                    SET 
                        card_generated = TRUE,
                        card_generated_dt = CURRENT_TIMESTAMP
                    WHERE session_id = %s
                """, (session_id,))
                
                conn.commit()
        
        logger.info(f"✅ 템플릿 카드 생성 완료: {session_id}")
        
        return {
            "card": card_data,
            "session_id": session_id,
            "generation_method": "template"
        }
    
    except Exception as e:
        logger.error(f"❌ 템플릿 카드 생성 실패: {e}")
        raise
