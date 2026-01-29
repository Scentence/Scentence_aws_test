import logging
import uuid
import json
import os
from typing import Dict, List, Optional
import psycopg2.extras
from scentmap.db import get_recom_db_connection

"""
SessionService: 사용자 탐색 세션 관리 및 활동 추적 서비스
"""

logger = logging.getLogger(__name__)

def create_session(member_id: Optional[int] = None, mbti: Optional[str] = None) -> Dict:
    """새로운 탐색 세션 생성 및 세션 ID 발급"""
    session_id = str(uuid.uuid4())
    try:
        with get_recom_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO TB_SCENT_CARD_SESSION_T (session_id, member_id, selected_accords, clicked_perfume_ids, liked_perfume_ids, interested_perfume_ids, passed_perfume_ids, exploration_time, interaction_count)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (session_id, member_id, [], [], [], [], [], 0, 0))
                conn.commit()
        return {"session_id": session_id, "member_id": member_id}
    except Exception as e:
        logger.error(f"세션 생성 실패: {e}")
        raise

def update_session_activity(
    session_id: str,
    accord_selected: Optional[str] = None,
    selected_accords: Optional[List[str]] = None,
    perfume_id: Optional[int] = None,
    dwell_time: Optional[int] = None,
    interaction_count: Optional[int] = None
):
    """세션 내 사용자 활동 데이터 업데이트"""
    try:
        with get_recom_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("SELECT selected_accords, clicked_perfume_ids, interaction_count FROM TB_SCENT_CARD_SESSION_T WHERE session_id = %s", (session_id,))
                session = cur.fetchone()
                if not session: return

                # 어코드 업데이트 로직
                accords_to_save = list(session['selected_accords'] or [])

                # 1. 프론트에서 selected_accords 배열을 보낸 경우: 전체 배열로 덮어쓰기
                if selected_accords is not None:
                    accords_to_save = selected_accords
                    logger.info(f"세션 {session_id}: 어코드 배열 업데이트됨 - {accords_to_save}")
                # 2. 개별 어코드 클릭인 경우: 기존 배열에 추가
                elif accord_selected and accord_selected not in accords_to_save:
                    accords_to_save.append(accord_selected)
                    logger.info(f"세션 {session_id}: 어코드 '{accord_selected}' 추가됨")

                # 향수 클릭 처리: clicked_perfume_ids 배열에 추가
                clicked_perfumes = list(session['clicked_perfume_ids'] or [])
                if perfume_id and perfume_id not in clicked_perfumes:
                    clicked_perfumes.append(perfume_id)
                    logger.info(f"세션 {session_id}: 향수 ID {perfume_id} 클릭됨 (총 {len(clicked_perfumes)}개)")

                updated_interaction_count = interaction_count or session['interaction_count'] + 1
                cur.execute("""
                    UPDATE TB_SCENT_CARD_SESSION_T
                    SET selected_accords = %s, clicked_perfume_ids = %s, interaction_count = %s, exploration_time = %s, last_activity_dt = CURRENT_TIMESTAMP
                    WHERE session_id = %s
                """, (accords_to_save, clicked_perfumes, updated_interaction_count, dwell_time or 0, session_id))
                conn.commit()
                logger.info(f"✅ 세션 {session_id} DB 저장 완료 - 어코드: {len(accords_to_save)}개, 향수 클릭: {len(clicked_perfumes)}개, 총 클릭: {updated_interaction_count}회")
    except Exception as e:
        logger.error(f"세션 활동 업데이트 실패: {e}")
        raise

def update_session_context(session_id: str, member_id: Optional[int] = None, mbti: Optional[str] = None, selected_accords: List[str] = [], filters: dict = {}, visible_perfume_ids: List[int] = []):
    """분석을 위한 상세 세션 컨텍스트 정보 저장"""
    try:
        # device_type 컬럼이 없는 경우를 대비하여 member_id와 selected_accords만 업데이트
        with get_recom_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE TB_SCENT_CARD_SESSION_T
                    SET member_id = COALESCE(%s, member_id), selected_accords = %s, last_activity_dt = CURRENT_TIMESTAMP
                    WHERE session_id = %s
                """, (member_id, selected_accords, session_id))
                conn.commit()
    except Exception as e:
        logger.error(f"세션 컨텍스트 업데이트 실패: {e}")
        raise

def check_card_trigger(session_id: str) -> Dict:
    """세션 활동 기준 카드 생성 제안 가능 여부 확인"""
    try:
        with get_recom_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("SELECT interaction_count, exploration_time FROM TB_SCENT_CARD_SESSION_T WHERE session_id = %s", (session_id,))
                session = cur.fetchone()
                if not session: return {"ready": False}
                
                ready = session['exploration_time'] >= 30 or session['interaction_count'] >= 15
                return {"ready": ready, "message": "취향이 충분히 쌓였어요! 나의 향 MBTI를 확인해볼까요?" if ready else None}
    except Exception as e:
        logger.error(f"트리거 체크 실패: {e}")
        return {"ready": False}
