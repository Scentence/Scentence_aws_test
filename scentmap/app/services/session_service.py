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
                    INSERT INTO TB_SCENT_CARD_SESSION_T (session_id, member_id, selected_accords, liked_perfume_ids, interested_perfume_ids, passed_perfume_ids, exploration_time, interaction_count)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (session_id, member_id, [], [], [], [], 0, 0))
                conn.commit()
        return {"session_id": session_id, "member_id": member_id}
    except Exception as e:
        logger.error(f"세션 생성 실패: {e}")
        raise

def update_session_activity(session_id: str, accord_selected: Optional[str] = None, dwell_time: Optional[int] = None, interaction_count: Optional[int] = None):
    """세션 내 사용자 활동 데이터 업데이트"""
    try:
        with get_recom_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("SELECT selected_accords, interaction_count FROM TB_SCENT_CARD_SESSION_T WHERE session_id = %s", (session_id,))
                session = cur.fetchone()
                if not session: return

                selected_accords = list(session['selected_accords'] or [])
                if accord_selected and accord_selected not in selected_accords:
                    selected_accords.append(accord_selected)

                cur.execute("""
                    UPDATE TB_SCENT_CARD_SESSION_T
                    SET selected_accords = %s, interaction_count = %s, exploration_time = %s, last_activity_dt = CURRENT_TIMESTAMP
                    WHERE session_id = %s
                """, (selected_accords, interaction_count or session['interaction_count'] + 1, dwell_time or 0, session_id))
                conn.commit()
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
