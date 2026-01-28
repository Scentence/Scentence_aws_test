import logging
import uuid
import os
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import psycopg2.extras
from openai import OpenAI
from scentmap.db import get_recom_db_connection, get_db_connection
from scentmap.app.schemas.ncard_schemas import ScentCard as NCard, MBTIComponent, AccordDetail, ScentCardBase
from pydantic import BaseModel, Field
from typing import Dict, List, Optional

class AccordInfo(BaseModel):
    """어코드 정보"""
    name: str = Field(..., description="어코드 이름")
    description: str = Field(..., description="어코드 설명")

class ScentTypeInfo(BaseModel):
    """향 타입 정보 (4축 통합)"""
    type_name: str = Field(..., description="향 타입 이름")
    type_description: str = Field(..., description="향 타입 설명")
    main_accords: List[str] = Field(..., description="핵심 어코드")
    harmonious_accords: List[str] = Field(..., description="보조 향")
    avoid_accords: Optional[List[str]] = Field(None, description="기피 향")
    axis_scores: Optional[Dict[str, float]] = Field(None, description="4축 점수")
    scent_code: Optional[str] = Field(None, description="향 MBTI 코드")
    derived_mbti: Optional[str] = Field(None, description="인간 MBTI")
    axis_keywords: Optional[List[str]] = Field(None, description="4축 키워드")
    mbti_profile: Optional[Dict] = Field(None, description="MBTI 프로필")
    mbti_story: Optional[str] = Field(None, description="MBTI 스토리")

class LLMCardOutput(BaseModel):
    """LLM 생성 결과 검증용 스키마"""
    title: str
    summary: str
    story: str
    accords: List[AccordInfo]
    mbti_code: Optional[str] = None

logger = logging.getLogger(__name__)

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 데이터 캐시
_mbti_data_cache = None
_accord_type_mapping_cache = None
_accord_mbti_mapping_cache = None

# 카드 생성 제한 (환경 변수로 조정 가능)
DAILY_MEMBER_CARD_LIMIT = int(os.getenv("SCENT_MEMBER_DAILY_LIMIT", "3"))
GUEST_SESSION_CARD_LIMIT = int(os.getenv("SCENT_GUEST_SESSION_LIMIT", "1"))


class DailyLimitExceededError(ValueError):
    """일일 카드 생성 제한 초과"""
    pass


def get_mbti_image_url(mbti_code: Optional[str]) -> str:
    """
    MBTI 코드별 이미지 URL 반환
    
    Args:
        mbti_code: MBTI 향 코드 (예: "FN", "CW", "SF", "WT")
    
    Returns:
        이미지 URL (현재는 고정 이미지 반환)
    
    TODO: MBTI 코드별 이미지 준비 후 매핑 로직 구현
    예정 매핑:
    - "FN" (Floral Natural): /images/mbti/floral-natural.jpg
    - "CW" (Citrus Woody): /images/mbti/citrus-woody.jpg
    - "SF" (Spicy Fresh): /images/mbti/spicy-fresh.jpg
    - "WT" (Woody Transparent): /images/mbti/woody-transparent.jpg
    ... (16종)
    """
    # TODO: MBTI별 이미지가 준비되면 아래 로직 활성화
    # mbti_image_mapping = {
    #     "FN": "/images/mbti/floral-natural.jpg",
    #     "CW": "/images/mbti/citrus-woody.jpg",
    #     "SF": "/images/mbti/spicy-fresh.jpg",
    #     "WT": "/images/mbti/woody-transparent.jpg",
    #     # ... 나머지 12종
    # }
    # return mbti_image_mapping.get(mbti_code, "/perfumes/perfume_wiki_default.png")
    
    # 현재는 고정 이미지 반환
    return "/perfumes/intp.png"


def load_mbti_data() -> List[Dict]:
    """
    MBTI 데이터 로드 (캐싱)
    
    Returns:
        MBTI 데이터 리스트
    """
    global _mbti_data_cache
    
    if _mbti_data_cache is not None:
        return _mbti_data_cache
    
    try:
        # data 폴더의 perfume_mbti.json 파일 읽기
        data_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data",
            "perfume_mbti.json"
        )
        
        with open(data_path, 'r', encoding='utf-8') as f:
            _mbti_data_cache = json.load(f)
        
        logger.info(f"MBTI 데이터 로드 완료: {len(_mbti_data_cache)}개")
        return _mbti_data_cache
    
    except Exception as e:
        logger.error(f"MBTI 데이터 로드 실패: {e}")
        return []


def load_accord_type_mapping() -> Dict:
    """
    어코드 타입 매핑 데이터 로드 (캐싱)
    
    Returns:
        어코드 타입 매핑 딕셔너리
    """
    global _accord_type_mapping_cache
    
    if _accord_type_mapping_cache is not None:
        return _accord_type_mapping_cache
    
    try:
        # data 폴더의 accord_type_mapping.json 파일 읽기
        data_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data",
            "accord_type_mapping.json"
        )
        
        with open(data_path, 'r', encoding='utf-8') as f:
            _accord_type_mapping_cache = json.load(f)
        
        logger.info(f"어코드 타입 매핑 데이터 로드 완료: {len(_accord_type_mapping_cache.get('accord_types', {}))}개")
        return _accord_type_mapping_cache
    
    except Exception as e:
        logger.error(f"어코드 타입 매핑 데이터 로드 실패: {e}")
        # 기본 구조 반환
        return {
            "accord_types": {},
            "default_type": {
                "type_name": "독특한 탐험가",
                "type_description_template": "당신만의 독특한 취향을 가진",
                "harmonious_accords": [],
                "avoid_accords": []
            }
        }


def load_accord_mbti_mapping() -> Dict:
    """
    어코드 MBTI 4축 매핑 데이터 로드 (캐싱)
    
    Returns:
        어코드 MBTI 매핑 딕셔너리
    """
    global _accord_mbti_mapping_cache
    
    if _accord_mbti_mapping_cache is not None:
        return _accord_mbti_mapping_cache
    
    try:
        # data 폴더의 accord_mbti_mapping.json 파일 읽기
        data_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data",
            "accord_mbti_mapping.json"
        )
        
        with open(data_path, 'r', encoding='utf-8') as f:
            _accord_mbti_mapping_cache = json.load(f)
        
        logger.info(f"어코드 MBTI 매핑 데이터 로드 완료: {len(_accord_mbti_mapping_cache.get('accord_axis_scores', {}))}개")
        return _accord_mbti_mapping_cache
    
    except Exception as e:
        logger.error(f"어코드 MBTI 매핑 데이터 로드 실패: {e}")
        # 기본 구조 반환
        return {
            "accord_axis_scores": {},
            "axis_descriptions": {},
            "mbti_code_mapping": {}
        }


def get_mbti_profile(mbti: str) -> Optional[Dict]:
    """
    특정 MBTI의 향 프로필 조회
    
    Args:
        mbti: MBTI 유형 (예: "INFJ")
    
    Returns:
        MBTI 향 프로필 또는 None
    """
    mbti_data = load_mbti_data()
    
    for profile in mbti_data:
        if profile.get("mbti") == mbti.upper():
            return profile
    
    logger.warning(f"MBTI 프로필을 찾을 수 없음: {mbti}")
    return None


def get_member_mbti(member_id: int) -> Optional[str]:
    """
    회원 MBTI 조회
    
    Args:
        member_id: 회원 ID
    
    Returns:
        MBTI 유형 또는 None
    """
    try:
        # TODO: 실제 회원 DB에서 MBTI 조회
        # 현재는 더미 데이터 반환 (테스트용)
        # 추후 TB_MEMBER_MBTI_T 또는 TB_MEMBER_PROFILE_T에서 조회
        
        with get_recom_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # 임시: 회원 ID를 MBTI로 매핑 (테스트용)
                # 실제 구현 시 아래 쿼리를 사용
                # cur.execute("""
                #     SELECT mbti 
                #     FROM TB_MEMBER_MBTI_T 
                #     WHERE member_id = %s
                # """, (member_id,))
                # 
                # result = cur.fetchone()
                # return result['mbti'] if result else None
                
                # 임시 매핑 (테스트용)
                test_mbtis = {
                    1: "INFJ",
                    2: "ENFP",
                    3: "INTJ",
                    4: "ISFJ",
                    5: "ESTP"
                }
                
                mbti = test_mbtis.get(member_id)
                if mbti:
                    logger.debug(f"회원 MBTI 조회: member_id={member_id}, mbti={mbti}")
                else:
                    logger.debug(f"회원 MBTI 없음: member_id={member_id}")
                
                return mbti
    
    except Exception as e:
        logger.error(f"회원 MBTI 조회 실패: {e}")
        return None


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
        
        logger.info(f"세션 생성: {session_id}")
        return {"session_id": session_id, "member_id": member_id}
    
    except Exception as e:
        logger.error(f"세션 생성 실패: {e}")
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
                    logger.warning(f"세션을 찾을 수 없음: {session_id}")
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
                
                logger.debug(f"세션 활동 업데이트: {session_id}")
    
    except Exception as e:
        logger.error(f"세션 활동 업데이트 실패: {e}")
        raise


def check_card_trigger(session_id: str) -> Dict:
    """
    카드 생성 조건 충족 여부 확인
    
    조건 (완화됨):
    - 어코드 선택: 1개 이상
    - 향수 반응: 2개 이상 (liked or interested)
    - 탐색 시간: 30초 이상
    - 상호작용: 3회 이상
    
    Returns:
        ready: 조건 충족 여부
        message: 제안 메시지
    """
    try:
        with get_recom_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT 
                        member_id,
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
                
                usage = get_daily_card_usage(session.get('member_id'), session_id)
                
                # 조건 체크 (완화됨)
                ready = (
                    accord_count >= 1 and
                    reaction_count >= 2 and
                    exploration_time >= 30 and
                    interaction_count >= 3
                )
                
                message = None
                if usage["reached"]:
                    ready = False
                    if session.get('member_id'):
                        message = f"오늘은 향기카드를 {usage['limit']}번까지 확인할 수 있어요. 내일 다시 시도해주세요."
                    else:
                        message = f"비회원은 세션당 향기카드를 {usage['limit']}번까지만 확인할 수 있어요."
                elif ready:
                    message = "취향이 쌓였어요! 지금까지 탐색한 향으로 향기카드를 만들어볼까요?"
                
                logger.info(
                    f"카드 트리거 체크: session={session_id}, "
                    f"accord={accord_count}, reaction={reaction_count}, "
                    f"time={exploration_time}s, interaction={interaction_count}, "
                    f"ready={ready}"
                )
                
                return {
                    "ready": ready,
                    "message": message,
                    "daily_limit_reached": usage["reached"],
                    "daily_limit_remaining": usage["remaining"]
                }
    
    except Exception as e:
        logger.error(f"카드 트리거 체크 실패: {e}")
        return {"ready": False}


def get_daily_card_usage(member_id: Optional[int], session_id: str) -> Dict:
    """
    카드 생성 사용량 확인
    
    Args:
        member_id: 회원 ID (비회원은 None)
        session_id: 세션 ID
    
    Returns:
        limit, used, remaining, reached 정보
    """
    used = 0
    try:
        with get_recom_db_connection() as conn:
            with conn.cursor() as cur:
                if member_id:
                    cur.execute("""
                        SELECT COUNT(*) 
                        FROM TB_SCENT_CARD_RESULT_T
                        WHERE member_id = %s
                          AND created_dt::date = CURRENT_DATE
                    """, (member_id,))
                    limit = DAILY_MEMBER_CARD_LIMIT
                else:
                    cur.execute("""
                        SELECT COUNT(*) 
                        FROM TB_SCENT_CARD_RESULT_T
                        WHERE session_id = %s
                    """, (session_id,))
                    limit = GUEST_SESSION_CARD_LIMIT
                used = int(cur.fetchone()[0] or 0)
    except Exception as e:
        logger.error(f"일일 카드 사용량 조회 실패: {e}")
        limit = DAILY_MEMBER_CARD_LIMIT if member_id else GUEST_SESSION_CARD_LIMIT
    
    remaining = max(limit - used, 0)
    return {
        "limit": limit,
        "used": used,
        "remaining": remaining,
        "reached": used >= limit
    }


def build_mbti_story(
    selected_accords: List[str],
    axis_scores: Dict,
    axis_keywords: List[str],
    main_accord_desc: Dict
) -> str:
    """
    향 MBTI 스토리 생성 (이유 설명, 안정성 강화)
    """
    if not axis_scores:
        return "선택한 향의 조합을 기준으로 향 성격을 분석했습니다."
    
    axis_summary = []
    if axis_scores.get("P", 0) >= axis_scores.get("I", 0):
        axis_summary.append("표현적")
    else:
        axis_summary.append("내향적")
    if axis_scores.get("T", 0) >= axis_scores.get("C", 0):
        axis_summary.append("투명한")
    else:
        axis_summary.append("복합적")
    if axis_scores.get("S", 0) >= axis_scores.get("N", 0):
        axis_summary.append("관능적")
    else:
        axis_summary.append("자연적")
    if axis_scores.get("B", 0) >= axis_scores.get("X", 0):
        axis_summary.append("밝은")
    else:
        axis_summary.append("깊은")
    
    main_accord = main_accord_desc.get("accord") or (selected_accords[0] if selected_accords else "대표 어코드")
    desc1 = main_accord_desc.get("desc1", main_accord)
    desc2 = main_accord_desc.get("desc2", "향")
    
    keyword_sentence = "선택한 어코드 구성이 일관되어 결과가 안정적으로 유지돼요."
    if axis_keywords:
        keywords = ", ".join(axis_keywords[:3])
        keyword_sentence = f"선택한 어코드에서 {keywords} 키워드가 반복되어 성향이 흔들리지 않아요."
    
    return (
        f"{main_accord} 중심의 조합은 {desc1} {desc2} 느낌을 강화해 "
        f"{', '.join(axis_summary)} 성향이 두드러집니다. {keyword_sentence}"
    )


def get_accord_descriptions(accord_names: List[str]) -> List[Dict]:
    """
    어코드 설명 조회 (DB 직접 조회, 최적화)
    
    Args:
        accord_names: 어코드 이름 리스트
    
    Returns:
        어코드 설명 리스트
    """
    if not accord_names:
        return []
    
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # IN 절 최적화: 파라미터 바인딩
                placeholders = ','.join(['%s'] * len(accord_names))
                query = f"""
                    SELECT accord, desc1, desc2, desc3
                    FROM TB_ACCORD_DESC_M
                    WHERE accord IN ({placeholders})
                """
                cur.execute(query, tuple(accord_names))
                
                results = cur.fetchall()
                
                desc_map = {
                    row['accord']: {
                        "accord": row['accord'],
                        "desc1": row['desc1'],
                        "desc2": row['desc2'],
                        "desc3": row['desc3']
                    }
                    for row in results
                }
                
                # 입력 순서를 유지해 결과 안정성 강화
                descriptions = [desc_map[acc] for acc in accord_names if acc in desc_map]
                
                logger.debug(f"어코드 설명 조회: {len(descriptions)}개")
                return descriptions
    
    except Exception as e:
        logger.error(f"어코드 설명 조회 실패: {e}")
        return []


def calculate_four_axis_scores(selected_accords: List[str]) -> Dict:
    """
    선택된 어코드를 기반으로 4축 점수 계산
    
    Args:
        selected_accords: 선택된 어코드 리스트
    
    Returns:
        4축 점수 딕셔너리 {axis: score}
        예: {"P": 65, "I": 35, "T": 70, "C": 30, "S": 40, "N": 60, "B": 75, "X": 25}
    """
    try:
        # 어코드 MBTI 매핑 로드
        mapping_data = load_accord_mbti_mapping()
        accord_scores = mapping_data.get('accord_axis_scores', {})
        
        if not selected_accords:
            return {}
        
        # 4축 점수 초기화
        axis_totals = {
            "P": 0, "I": 0,
            "T": 0, "C": 0,
            "S": 0, "N": 0,
            "B": 0, "X": 0
        }
        
        # 각 어코드의 점수를 합산
        valid_accord_count = 0
        for accord in selected_accords:
            if accord in accord_scores:
                for axis, score in accord_scores[accord].items():
                    axis_totals[axis] += score
                valid_accord_count += 1
        
        if valid_accord_count == 0:
            logger.warning(f"유효한 어코드가 없습니다: {selected_accords}")
            return {}
        
        # 평균 계산
        axis_averages = {axis: total / valid_accord_count for axis, total in axis_totals.items()}
        
        logger.debug(f"4축 점수 계산: {valid_accord_count}개 어코드 분석")
        return axis_averages
    
    except Exception as e:
        logger.error(f"4축 점수 계산 실패: {e}")
        return {}


def determine_mbti_code(axis_scores: Dict) -> Optional[str]:
    """
    4축 점수를 기반으로 향 MBTI 코드 결정
    
    Args:
        axis_scores: 4축 점수 딕셔너리
    
    Returns:
        향 MBTI 코드 (예: "PTSB", "INCX")
    """
    try:
        if not axis_scores:
            return None
        
        # 각 축에서 더 높은 점수를 가진 것 선택
        code = ""
        
        # P/I
        code += "P" if axis_scores.get("P", 0) >= axis_scores.get("I", 0) else "I"
        
        # T/C
        code += "T" if axis_scores.get("T", 0) >= axis_scores.get("C", 0) else "C"
        
        # S/N
        code += "S" if axis_scores.get("S", 0) >= axis_scores.get("N", 0) else "N"
        
        # B/X
        code += "B" if axis_scores.get("B", 0) >= axis_scores.get("X", 0) else "X"
        
        logger.debug(f"향 MBTI 코드: {code}")
        return code
    
    except Exception as e:
        logger.error(f"MBTI 코드 결정 실패: {e}")
        return None


def get_mbti_from_scent_code(scent_code: str) -> Optional[str]:
    """
    향 MBTI 코드를 인간 MBTI로 변환
    
    Args:
        scent_code: 향 MBTI 코드 (예: "PTSB")
    
    Returns:
        인간 MBTI (예: "ESTJ")
    """
    try:
        mapping_data = load_accord_mbti_mapping()
        code_mapping = mapping_data.get('mbti_code_mapping', {})
        
        mbti = code_mapping.get(scent_code)
        if mbti:
            logger.debug(f"향 MBTI 코드 변환: {scent_code} → {mbti}")
        else:
            logger.warning(f"매핑되지 않은 향 MBTI 코드: {scent_code}")
        
        return mbti
    
    except Exception as e:
        logger.error(f"MBTI 코드 변환 실패: {e}")
        return None


def generate_axis_keywords(axis_scores: Dict) -> List[str]:
    """
    4축 점수를 기반으로 키워드 생성
    
    Args:
        axis_scores: 4축 점수 딕셔너리
    
    Returns:
        키워드 리스트
    """
    try:
        mapping_data = load_accord_mbti_mapping()
        axis_descriptions = mapping_data.get('axis_descriptions', {})
        
        keywords = []
        
        # 각 축의 지배적인 방향 선택
        if axis_scores.get("P", 0) >= axis_scores.get("I", 0):
            keywords.extend(axis_descriptions.get("P", {}).get("keywords", [])[:1])
        else:
            keywords.extend(axis_descriptions.get("I", {}).get("keywords", [])[:1])
        
        if axis_scores.get("T", 0) >= axis_scores.get("C", 0):
            keywords.extend(axis_descriptions.get("T", {}).get("keywords", [])[:1])
        else:
            keywords.extend(axis_descriptions.get("C", {}).get("keywords", [])[:1])
        
        if axis_scores.get("S", 0) >= axis_scores.get("N", 0):
            keywords.extend(axis_descriptions.get("S", {}).get("keywords", [])[:1])
        else:
            keywords.extend(axis_descriptions.get("N", {}).get("keywords", [])[:1])
        
        if axis_scores.get("B", 0) >= axis_scores.get("X", 0):
            keywords.extend(axis_descriptions.get("B", {}).get("keywords", [])[:1])
        else:
            keywords.extend(axis_descriptions.get("X", {}).get("keywords", [])[:1])
        
        logger.debug(f"4축 키워드: {', '.join(keywords)}")
        return keywords
    
    except Exception as e:
        logger.error(f"4축 키워드 생성 실패: {e}")
        return []


def analyze_scent_type(
    selected_accords: List[str],
    accord_descriptions: List[Dict],
    user_mbti: Optional[str] = None
) -> Dict:
    """
    선택된 어코드를 기반으로 향 타입 분석 (4축 통합 버전)
    
    Args:
        selected_accords: 선택된 어코드 리스트
        accord_descriptions: 어코드 설명 리스트
        user_mbti: 사용자 MBTI (옵션)
    
    Returns:
        향 타입 정보 (4축 정보 포함)
    """
    try:
        if not selected_accords or not accord_descriptions:
            raise ValueError("선택된 어코드나 설명이 없습니다")
        
        # 4축 점수 계산
        axis_scores = calculate_four_axis_scores(selected_accords)
        
        # 향 MBTI 코드 결정
        scent_code = determine_mbti_code(axis_scores) if axis_scores else None
        
        # 향 MBTI 코드를 인간 MBTI로 변환
        derived_mbti = get_mbti_from_scent_code(scent_code) if scent_code else None
        
        # 4축 키워드 생성
        axis_keywords = generate_axis_keywords(axis_scores) if axis_scores else []
        
        # 어코드 타입 매핑 로드 (캐싱됨)
        mapping_data = load_accord_type_mapping()
        accord_types = mapping_data.get('accord_types', {})
        default_type = mapping_data.get('default_type', {})
        mbti_affinity = mapping_data.get('mbti_accord_affinity', {})
        
        # 어코드 빈도수 계산
        from collections import Counter
        accord_counter = Counter(selected_accords)
        
        # MBTI 기반 가중치 적용 (derived_mbti 우선)
        active_mbti = derived_mbti or user_mbti
        if active_mbti and active_mbti in mbti_affinity:
            preferred_accords = mbti_affinity[active_mbti].get('preferred_accords', [])
            for accord in preferred_accords:
                if accord in accord_counter:
                    accord_counter[accord] += 1
        
        # 최빈값 어코드 선택 (동률 시 알파벳 순으로 안정화)
        if accord_counter:
            most_common_accord = sorted(
                accord_counter.items(),
                key=lambda item: (-item[1], item[0])
            )[0][0]
        else:
            most_common_accord = selected_accords[0]
        
        # 메인 어코드 설명 찾기
        main_accord_desc = next(
            (desc for desc in accord_descriptions if desc['accord'] == most_common_accord),
            None
        )
        
        if not main_accord_desc:
            main_accord_desc = accord_descriptions[0] if accord_descriptions else {
                'accord': most_common_accord,
                'desc1': most_common_accord,
                'desc2': '향'
            }
        
        # 타입 정보 가져오기
        type_info = accord_types.get(most_common_accord, None)
        
        if not type_info:
            type_info = default_type.copy()
            type_info['harmonious_accords'] = selected_accords[:3] if len(selected_accords) > 1 else []
            type_info['avoid_accords'] = []
        
        # MBTI 기반 성격 추가 (MBTI 타입은 직접 노출하지 않음)
        mbti_persona_desc = ""
        mbti_mood = ""
        mbti_profile = None
        mbti_profile_summary = None
        
        if active_mbti:
            mbti_profile = get_mbti_profile(active_mbti)
            if mbti_profile:
                # MBTI 타입을 직접 노출하지 않고 성격 특성으로 표현
                mbti_persona_desc = f". {mbti_profile['impression']}"
                mbti_profile_summary = {
                    "headline": mbti_profile.get("headline"),
                    "intro": mbti_profile.get("intro"),
                    "impression": mbti_profile.get("impression"),
                    "strengths": mbti_profile.get("strengths", []),
                    "weaknesses": mbti_profile.get("weaknesses", []),
                    "scent_preferences": mbti_profile.get("scent_preferences", {})
                }
            
            if active_mbti in mbti_affinity:
                preferred_moods = mbti_affinity[active_mbti].get('preferred_moods', [])
                if preferred_moods:
                    mbti_mood = f" {preferred_moods[0]}"
        
        # 타입 설명 생성 (MBTI 타입 대신 성격 특성으로 표현)
        desc1 = main_accord_desc.get('desc1', most_common_accord)
        desc2 = main_accord_desc.get('desc2', '향')
        
        template = type_info.get('type_description_template', '{desc1}의 {desc2}를 좋아하는')
        type_description = f"당신은 {template.format(desc1=desc1, desc2=desc2)} 사람이에요{mbti_persona_desc}"
        
        # 타입 이름
        type_name = type_info.get('type_name', '독특한 탐험가')
        if mbti_mood:
            type_name = f"{mbti_mood} {type_name}"
        
        mbti_story = build_mbti_story(selected_accords, axis_scores, axis_keywords, main_accord_desc)
        
        # 결과 반환 (4축 정보 포함)
        return {
            "type_name": type_name,
            "type_description": type_description,
            "main_accords": selected_accords[:3],
            "harmonious_accords": type_info.get('harmonious_accords', []),
            "avoid_accords": type_info.get('avoid_accords', []),
            "mood": type_info.get('mood', ''),
            "time_of_day": type_info.get('time_of_day', ''),
            "personality_traits": type_info.get('personality_traits', []),
            "axis_scores": axis_scores,
            "scent_code": scent_code,
            "derived_mbti": derived_mbti,  # 내부용 (프론트엔드에서 노출하지 않음)
            "axis_keywords": axis_keywords,
            "mbti_profile": mbti_profile_summary,
            "mbti_story": mbti_story
        }
    
    except Exception as e:
        logger.error(f"❌ 향 타입 분석 실패: {e}", exc_info=True)
        # 기본 타입 반환
        mapping_data = load_accord_type_mapping()
        default_type = mapping_data.get('default_type', {})
        
        return {
            "type_name": default_type.get('type_name', '독특한 탐험가'),
            "type_description": "당신만의 독특한 취향을 가진 사람이에요",
            "main_accords": selected_accords[:3] if selected_accords else [],
            "harmonious_accords": [],
            "avoid_accords": [],
            "axis_scores": {},
            "scent_code": None,
            "derived_mbti": None,
            "axis_keywords": [],
            "mbti_profile": None,
            "mbti_story": "선택한 향의 조합을 기준으로 향 성격을 분석했습니다."
        }


def get_note_descriptions(note_names: List[str]) -> Dict[str, Dict]:
    """
    노트 설명 조회 (DB 직접 조회, 최적화)
    
    Args:
        note_names: 노트 이름 리스트
    
    Returns:
        노트별 설명 딕셔너리 {note_name: {category, description}}
    """
    if not note_names:
        return {}
    
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # IN 절 최적화
                placeholders = ','.join(['%s'] * len(note_names))
                query = f"""
                    SELECT note, category, description
                    FROM TB_NOTE_DESC_M
                    WHERE note IN ({placeholders})
                """
                cur.execute(query, tuple(note_names))
                
                results = cur.fetchall()
                
                note_dict = {
                    row['note']: {
                        "category": row['category'],
                        "description": row['description']
                    }
                    for row in results
                }
                
                logger.debug(f"노트 설명 조회: {len(note_dict)}개")
                return note_dict
    
    except Exception as e:
        logger.error(f"노트 설명 조회 실패: {e}")
        return {}


def get_perfume_notes(perfume_id: int) -> Dict[str, List[str]]:
    """
    향수의 노트 정보 조회 (탑/미들/베이스)
    
    Args:
        perfume_id: 향수 ID
    
    Returns:
        노트 정보 딕셔너리 {top: [...], middle: [...], base: [...]}
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT note, type
                    FROM TB_PERFUME_NOTES_M
                    WHERE perfume_id = %s
                    ORDER BY type, note
                """, (perfume_id,))
                
                results = cur.fetchall()
                
                notes = {
                    "top": [],
                    "middle": [],
                    "base": []
                }
                
                for row in results:
                    note_type = row['type'].lower() if row['type'] else ""
                    note_name = row['note']
                    
                    if note_type == 'top':
                        notes['top'].append(note_name)
                    elif note_type == 'middle':
                        notes['middle'].append(note_name)
                    elif note_type == 'base':
                        notes['base'].append(note_name)
                
                logger.debug(f"향수 {perfume_id} 노트 조회: Top {len(notes['top'])}, Middle {len(notes['middle'])}, Base {len(notes['base'])}")
                return notes
    
    except Exception as e:
        logger.error(f"향수 노트 조회 실패: {e}")
        return {"top": [], "middle": [], "base": []}


def get_incompatible_accords(selected_accords: List[str], user_mbti: Optional[str] = None) -> List[str]:
    """
    레이어링 시 어울리지 않는 어코드 제안 (정반대 성향)
    
    Args:
        selected_accords: 현재 선택된 어코드 리스트
        user_mbti: 사용자 MBTI (선택)
    
    Returns:
        비추천 어코드 리스트 (최대 3개)
    """
    try:
        # 4축 점수 계산
        axis_scores = calculate_four_axis_scores(selected_accords)
        if not axis_scores:
            return []
        
        # 정반대 성향 계산 (각 축의 반대편)
        opposite_scores = {
            "P": 100 - axis_scores.get("P", 50),
            "I": 100 - axis_scores.get("I", 50),
            "T": 100 - axis_scores.get("T", 50),
            "C": 100 - axis_scores.get("C", 50),
            "S": 100 - axis_scores.get("S", 50),
            "N": 100 - axis_scores.get("N", 50),
            "B": 100 - axis_scores.get("B", 50),
            "X": 100 - axis_scores.get("X", 50),
        }
        
        # 어코드별 거리 계산
        mapping_data = load_accord_mbti_mapping()
        accord_scores = mapping_data.get('accord_axis_scores', {})
        
        distances = []
        for accord, scores in accord_scores.items():
            if accord in selected_accords:
                continue
            
            # 유클리드 거리 계산
            distance = 0
            for axis in ["P", "I", "T", "C", "S", "N", "B", "X"]:
                distance += (scores.get(axis, 0) - opposite_scores.get(axis, 0)) ** 2
            distance = distance ** 0.5
            
            distances.append((accord, distance))
        
        # 거리가 가까운 순 (= 현재 선택과 정반대인 어코드)
        distances.sort(key=lambda x: x[1])
        incompatible = [acc for acc, _ in distances[:3]]
        
        logger.debug(f"어울리지 않는 어코드: {incompatible}")
        return incompatible
    
    except Exception as e:
        logger.error(f"비호환 어코드 계산 실패: {e}")
        return []


def get_suggested_accords(selected_accords: List[str], user_mbti: Optional[str] = None) -> List[str]:
    """
    다음 탐색을 위한 어코드 제안 (최적화 버전)
    
    Args:
        selected_accords: 현재 선택된 어코드 리스트
        user_mbti: 사용자 MBTI (선택)
    
    Returns:
        추천 어코드 리스트 (최대 3개)
    """
    try:
        # JSON에서 어코드 매핑 로드
        mapping_data = load_accord_type_mapping()
        accord_suggestions = mapping_data.get('accord_suggestions', {})
        mbti_affinity = mapping_data.get('mbti_accord_affinity', {})
        
        suggestions = []
        
        # 1. 현재 선택 어코드와 어울리는 어코드 추천
        for accord in selected_accords:
            if accord in accord_suggestions:
                suggestions.extend(accord_suggestions[accord])
        
        # 2. MBTI 기반 추천 추가
        if user_mbti and user_mbti in mbti_affinity:
            mbti_preferred = mbti_affinity[user_mbti].get('preferred_accords', [])
            suggestions.extend(mbti_preferred)
        
        # 3. 중복 제거 및 이미 선택된 어코드 제외
        suggestions = [s for s in suggestions if s not in selected_accords]
        unique_suggestions = []
        for s in suggestions:
            if s not in unique_suggestions:
                unique_suggestions.append(s)
        
        # 4. 최대 3개 반환
        result = unique_suggestions[:3]
        
        logger.debug(f"어코드 제안: {len(result)}개")
        return result
    
    except Exception as e:
        logger.error(f"어코드 제안 실패: {e}")
        return []


def generate_mbti_components(axis_scores: Dict, scent_code: str) -> List[Dict]:
    """
    4축 점수와 향 코드를 기반으로 프론트엔드용 MBTI 컴포넌트 생성
    """
    if not axis_scores or not scent_code or len(scent_code) != 4:
        return []
    
    mapping_data = load_accord_mbti_mapping()
    axis_descriptions = mapping_data.get('axis_descriptions', {})
    
    components = []
    
    # 축 매핑 (순서 고정)
    axes = [
        ("존재방식", scent_code[0]), # P or I
        ("인식방식", scent_code[1]), # T or C
        ("감정질감", scent_code[2]), # S or N
        ("취향안정성", scent_code[3]) # B or X
    ]
    
    for axis_name, code in axes:
        desc_info = axis_descriptions.get(code, {})
        components.append({
            "axis": axis_name,
            "code": code,
            "desc": desc_info.get("description", f"{code} 성향이 두드러집니다.")
        })
        
    return components


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
                # 기존 카드가 있는지 먼저 확인
                cur.execute("""
                    SELECT 
                        card_id,
                        card_data,
                        generation_method
                    FROM TB_SCENT_CARD_RESULT_T
                    WHERE session_id = %s
                    ORDER BY created_dt DESC
                    LIMIT 1
                """, (session_id,))
                
                existing_card = cur.fetchone()
                if existing_card:
                    existing_card_id = str(existing_card['card_id'])
                    logger.info(f"기존 카드 반환: session={session_id}, card_id={existing_card_id}")
                    
                    result_dict = {
                        "card": existing_card['card_data'],
                        "session_id": session_id,
                        "card_id": existing_card_id,
                        "generation_method": existing_card['generation_method']
                    }
                    
                    return result_dict
                
                # 기존 카드가 없으면 새로 생성
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
                
                usage = get_daily_card_usage(session['member_id'], session_id)
                if usage["reached"]:
                    if session['member_id']:
                        raise DailyLimitExceededError(f"오늘은 향기카드를 {usage['limit']}번까지 확인할 수 있어요. 내일 다시 시도해주세요.")
                    raise DailyLimitExceededError(f"비회원은 세션당 향기카드를 {usage['limit']}번까지만 확인할 수 있어요.")
                
                selected_accords = session['selected_accords'] or []
                if not selected_accords:
                    raise ValueError("선택된 어코드가 없습니다")
        
        # 어코드 설명 조회
        descriptions = get_accord_descriptions(selected_accords)
        
        if not descriptions:
            raise ValueError("어코드 설명을 찾을 수 없습니다")
        
        # [NEW] 향 타입 분석
        user_mbti = None
        if session['member_id']:
            user_mbti = get_member_mbti(session['member_id'])
        
        scent_type = analyze_scent_type(selected_accords, descriptions, user_mbti)
        
        # [NEW] 향 타입 기반 제목 생성
        primary_accord = descriptions[0]
        title = f"{primary_accord['desc1']}를 사랑하는 {scent_type['type_name']}"
        
        # [NEW] 향 타입 기반 스토리 생성
        story = scent_type['type_description']
        if len(descriptions) > 1:
            story += f" {primary_accord['desc2']}을 중심으로, 함께 선택한 향들이 조화를 이루며 당신만의 분위기를 만들어냅니다."
        
        # 어코드 정보 구성
        accords = []
        for desc in descriptions:
            accords.append({
                "name": desc['accord'],
                "description": desc['desc1']
            })
        
        # [NEW] 다음 탐색 제안 어코드
        suggested_accords = get_suggested_accords(selected_accords, None)
        
        # [NEW] 추천 향수 정보 추가 (관심 표시한 향수 중 첫 번째)
        recommended_perfume = None
        interested_ids = session['interested_perfume_ids'] or []
        liked_ids = session['liked_perfume_ids'] or []
        candidate_ids = liked_ids + interested_ids
        
        if candidate_ids:
            # 가장 먼저 관심 표시한 향수 선택
            perfume_id = candidate_ids[0]
            
            try:
                # 향수 기본 정보 조회
                with get_db_connection() as conn:
                    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                        cur.execute("""
                            SELECT perfume_id, perfume_name, perfume_brand, img_link
                            FROM TB_PERFUME_BASIC_M
                            WHERE perfume_id = %s
                        """, (perfume_id,))
                        
                        perfume_row = cur.fetchone()
                        
                        if perfume_row:
                            # 향수 노트 정보 조회
                            notes = get_perfume_notes(perfume_id)
                            
                            # 노트 설명 조회
                            all_notes = notes['top'] + notes['middle'] + notes['base']
                            note_descs = get_note_descriptions(all_notes) if all_notes else {}
                            
                            # 노트 정보 구성 (설명 포함)
                            notes_with_desc = {
                                "top": [{"name": n, "description": note_descs.get(n, {}).get("description", "")} for n in notes['top'][:3]],
                                "middle": [{"name": n, "description": note_descs.get(n, {}).get("description", "")} for n in notes['middle'][:3]],
                                "base": [{"name": n, "description": note_descs.get(n, {}).get("description", "")} for n in notes['base'][:3]]
                            }
                            
                            recommended_perfume = {
                                "perfume_id": perfume_id,
                                "perfume_name": perfume_row['perfume_name'],
                                "brand": perfume_row['perfume_brand'],
                                "image": perfume_row['img_link'],
                                "notes": notes_with_desc
                            }
            
            except Exception as e:
                logger.warning(f"추천 향수 정보 조회 실패: {e}")
        
        # 어울리지 않는 어코드 계산
        user_mbti_for_calc = None
        if session['member_id']:
            user_mbti_for_calc = get_member_mbti(session['member_id'])
        incompatible_accords = get_incompatible_accords(selected_accords, user_mbti_for_calc)
        
        # [NEW] 프론트엔드 요구 필드 생성
        mbti_code = scent_type.get('scent_code', 'INCX')
        derived_mbti = scent_type.get('derived_mbti', 'INFP')
        components = generate_mbti_components(scent_type.get('axis_scores', {}), mbti_code)
        
        # 추천/기피 어코드 상세 구성
        recommends = []
        harmonious = scent_type.get('harmonious_accords', []) or suggested_accords
        for acc_name in harmonious[:2]:
            recommends.append({
                "name": acc_name,
                "reason": f"{derived_mbti} 성향과 조화를 이루는 추천 향입니다."
            })
            
        avoids = []
        for acc_name in incompatible_accords[:2]:
            avoids.append({
                "name": acc_name,
                "reason": f"현재의 분위기와 상충될 수 있는 향입니다."
            })

        # [NEW] 프론트엔드 최신 스키마(NCard)로 검증
        ncard_data = {
            "mbti": derived_mbti,
            "components": components,
            "recommends": recommends,
            "avoids": avoids,
            "story": story,
            "summary": f"{scent_type['type_name']}인 당신에게 어울리는 향기 리포트입니다."
        }
        
        # 최신 스키마 검증 (필드 누락 방지)
        ScentCardBase(**ncard_data)
        
        # ScentCardBase 필드들을 포함하도록 구성
        card_data = ncard_data.copy()
        card_data.update({
            # 향 타입 정보 (핵심!)
            "scent_type": {
                "type_name": scent_type['type_name'],
                "type_description": scent_type['type_description'],
                "main_accords": scent_type['main_accords'],
                "harmonious_accords": scent_type['harmonious_accords'],
                "avoid_accords": incompatible_accords,  # 계산된 비호환 어코드
                # [NEW] 4축 정보
                "axis_scores": scent_type.get('axis_scores', {}),
                "scent_code": scent_type.get('scent_code'),
                "derived_mbti": scent_type.get('derived_mbti'),
                "axis_keywords": scent_type.get('axis_keywords', []),
                "mbti_profile": scent_type.get('mbti_profile'),
                "mbti_story": scent_type.get('mbti_story')
            },
            "mbti_code": scent_type.get('scent_code'),
            "title": title,
            "story": story,
            "accords": accords,
            "created_at": datetime.now().isoformat(),
            # 추천 향수 (있는 경우)
            "recommended_perfume": recommended_perfume,
            # 다음 탐색 제안 어코드 (향 타입과 어울리는 향)
            "suggested_accords": scent_type['harmonious_accords'][:3] if scent_type['harmonious_accords'] else suggested_accords,
            # 다음 단계 CTA
            "next_actions": [
                {
                    "type": "chatbot",
                    "title": "더 정확한 추천을 받고싶나요?",
                    "description": "센텐스의 추천챗봇을 이용해보세요!",
                    "button_text": "추천챗봇 시작하기",
                    "link": "/chat"
                },
                {
                    "type": "layering",
                    "title": "레이어링에 관심있으신가요?",
                    "description": "레이어링추천서비스도 이용해보세요!",
                    "button_text": "레이어링 추천받기",
                    "link": "/layering"
                }
            ],
            # 카드 이미지 (derived_mbti 기반, 없으면 고정)
            "image_url": get_mbti_image_url(scent_type.get('scent_code'))
        })
        
        # [NEW] MBTI 안내 (회원이지만 MBTI 없는 경우)
        if session['member_id']:
            card_data["mbti_prompt"] = {
                "message": "MBTI를 알려주시면 더 좋아요!",
                "options": ["ISTJ", "ISFJ", "INFJ", "INTJ", "ISTP", "ISFP", "INFP", "INTP",
                           "ESTJ", "ESFJ", "ENFJ", "ENTJ", "ESTP", "ESFP", "ENFP", "ENTP"]
            }
        
        # 카드 결과 저장
        card_id = None
        with get_recom_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO TB_SCENT_CARD_RESULT_T (
                        session_id,
                        member_id,
                        card_data,
                        generation_method
                    ) VALUES (%s, %s, %s, %s)
                    RETURNING card_id
                """, (
                    session_id,
                    session['member_id'],
                    psycopg2.extras.Json(card_data),
                    'template'
                ))
                result = cur.fetchone()
                if not result or not result[0]:
                    logger.error(f"INSERT 후 card_id를 받지 못함")
                    raise ValueError("DB에서 card_id를 받아오지 못했습니다")
                
                card_id = result[0]
                
                # 세션 업데이트
                cur.execute("""
                    UPDATE TB_SCENT_CARD_SESSION_T
                    SET 
                        card_generated = TRUE,
                        card_generated_dt = CURRENT_TIMESTAMP
                    WHERE session_id = %s
                """, (session_id,))
                
                conn.commit()
        
        if not card_id:
            logger.error(f"card_id가 None입니다")
            raise ValueError("카드 ID 생성에 실패했습니다")
        
        logger.info(f"카드 생성 완료: session={session_id}, card_id={card_id}, method=template")
        
        result_dict = {
            "card": card_data,
            "session_id": session_id,
            "card_id": str(card_id),
            "generation_method": "template"
        }
        
        return result_dict
    
    except Exception as e:
        logger.error(f"템플릿 카드 생성 실패: {e}", exc_info=True)
        raise


def generate_llm_card(session_id: str, use_simple_model: bool = False) -> Dict:
    """
    LLM 기반 향기카드 생성 (MBTI 통합)
    
    Args:
        session_id: 세션 ID
        use_simple_model: 간단한 모델 사용 여부 (gpt-4o-mini vs gpt-4o)
    
    Returns:
        향기카드 데이터
    """
    start_time = time.time()
    
    try:
        # 세션 데이터 조회
        with get_recom_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # 기존 카드가 있는지 먼저 확인
                cur.execute("""
                    SELECT 
                        card_id,
                        card_data,
                        generation_method,
                        generation_time_ms
                    FROM TB_SCENT_CARD_RESULT_T
                    WHERE session_id = %s
                    ORDER BY created_dt DESC
                    LIMIT 1
                """, (session_id,))
                
                existing_card = cur.fetchone()
                if existing_card:
                    existing_card_id = str(existing_card['card_id'])
                    logger.info(f"♻️ 기존 LLM 카드 반환: session={session_id}, card_id={existing_card_id}")
                    
                    result_dict = {
                        "card": existing_card['card_data'],
                        "session_id": session_id,
                        "card_id": existing_card_id,
                        "generation_method": existing_card['generation_method'],
                        "generation_time_ms": existing_card['generation_time_ms']
                    }
                    
                    logger.info(f"📦 기존 LLM 카드 반환 데이터 검증: card_id={result_dict.get('card_id')}, keys={list(result_dict.keys())}")
                    return result_dict
                
                # 기존 카드가 없으면 새로 생성
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
                
                usage = get_daily_card_usage(session['member_id'], session_id)
                if usage["reached"]:
                    if session['member_id']:
                        raise DailyLimitExceededError(f"오늘은 향기카드를 {usage['limit']}번까지 확인할 수 있어요. 내일 다시 시도해주세요.")
                    raise DailyLimitExceededError(f"비회원은 세션당 향기카드를 {usage['limit']}번까지만 확인할 수 있어요.")
                
                selected_accords = session['selected_accords'] or []
                if not selected_accords:
                    raise ValueError("선택된 어코드가 없습니다")
        
        # 어코드 설명 조회
        descriptions = get_accord_descriptions(selected_accords)
        
        if not descriptions:
            raise ValueError("어코드 설명을 찾을 수 없습니다")
        
        # 회원 MBTI 조회
        user_mbti = None
        if session['member_id']:
            user_mbti = get_member_mbti(session['member_id'])
        
        # 4축 점수 계산
        axis_scores = calculate_four_axis_scores(selected_accords)
        scent_code = determine_mbti_code(axis_scores) if axis_scores else None
        derived_mbti = get_mbti_from_scent_code(scent_code) if scent_code else None
        axis_keywords = generate_axis_keywords(axis_scores) if axis_scores else []

        from collections import Counter
        accord_counter = Counter(selected_accords)
        if accord_counter:
            main_accord = sorted(
                accord_counter.items(),
                key=lambda item: (-item[1], item[0])
            )[0][0]
        else:
            main_accord = selected_accords[0]
        main_accord_desc = next((desc for desc in descriptions if desc['accord'] == main_accord), descriptions[0])
        mbti_story = build_mbti_story(selected_accords, axis_scores, axis_keywords, main_accord_desc)
        
        # 다음 탐색 제안 어코드
        active_mbti = derived_mbti or user_mbti
        suggested_accords = get_suggested_accords(selected_accords, active_mbti)
        
        # 추천 향수 정보 조회
        recommended_perfume = None
        interested_ids = session['interested_perfume_ids'] or []
        liked_ids = session['liked_perfume_ids'] or []
        candidate_ids = liked_ids + interested_ids
        
        if candidate_ids:
            perfume_id = candidate_ids[0]
            
            try:
                with get_db_connection() as conn:
                    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                        cur.execute("""
                            SELECT perfume_id, perfume_name, perfume_brand, img_link
                            FROM TB_PERFUME_BASIC_M
                            WHERE perfume_id = %s
                        """, (perfume_id,))
                        
                        perfume_row = cur.fetchone()
                        
                        if perfume_row:
                            notes = get_perfume_notes(perfume_id)
                            all_notes = notes['top'] + notes['middle'] + notes['base']
                            note_descs = get_note_descriptions(all_notes) if all_notes else {}
                            
                            notes_with_desc = {
                                "top": [{"name": n, "description": note_descs.get(n, {}).get("description", "")} for n in notes['top'][:3]],
                                "middle": [{"name": n, "description": note_descs.get(n, {}).get("description", "")} for n in notes['middle'][:3]],
                                "base": [{"name": n, "description": note_descs.get(n, {}).get("description", "")} for n in notes['base'][:3]]
                            }
                            
                            recommended_perfume = {
                                "perfume_id": perfume_id,
                                "perfume_name": perfume_row['perfume_name'],
                                "brand": perfume_row['perfume_brand'],
                                "image": perfume_row['img_link'],
                                "notes": notes_with_desc
                            }
            
            except Exception as e:
                logger.warning(f"LLM 카드 - 추천 향수 정보 조회 실패: {e}")
        
        # MBTI 프로필 조회 (derived_mbti 우선)
        mbti_profile = None
        if active_mbti:
            mbti_profile = get_mbti_profile(active_mbti)
        
        # LLM 프롬프트 구성 (4축 정보 포함, MBTI 타입 노출 제거)
        accord_info = "\n".join([
            f"- {desc['accord']}: {desc['desc1']}, {desc['desc2']}, {desc['desc3']}"
            for desc in descriptions
        ])
        
        # 4축 정보 추가 (MBTI 타입 대신 성격 특성 표현)
        axis_section = ""
        if axis_scores and scent_code:
            axis_info = []
            # P/I
            if axis_scores.get("P", 0) >= axis_scores.get("I", 0):
                axis_info.append(f"표현적 ({int(axis_scores.get('P', 0))}점)")
            else:
                axis_info.append(f"내향적 ({int(axis_scores.get('I', 0))}점)")
            
            # T/C
            if axis_scores.get("T", 0) >= axis_scores.get("C", 0):
                axis_info.append(f"투명한 ({int(axis_scores.get('T', 0))}점)")
            else:
                axis_info.append(f"복합적 ({int(axis_scores.get('C', 0))}점)")
            
            # S/N
            if axis_scores.get("S", 0) >= axis_scores.get("N", 0):
                axis_info.append(f"관능적 ({int(axis_scores.get('S', 0))}점)")
            else:
                axis_info.append(f"자연적 ({int(axis_scores.get('N', 0))}점)")
            
            # B/X
            if axis_scores.get("B", 0) >= axis_scores.get("X", 0):
                axis_info.append(f"밝은 ({int(axis_scores.get('B', 0))}점)")
            else:
                axis_info.append(f"깊은 ({int(axis_scores.get('X', 0))}점)")
            
            axis_section = f"""

[향 분석 결과 - 4축]
- 향 코드: {scent_code}
- 4축 특성: {', '.join(axis_info)}
- 핵심 키워드: {', '.join(axis_keywords)}

위 4축 정보를 바탕으로 향의 성격을 풍부하게 표현해주세요."""
        
        # MBTI 성격 특성 추가 (MBTI 타입 노출하지 않음)
        mbti_section = ""
        if mbti_profile:
            mbti_section = f"""

[성격 특성 정보]
- 향 성격: {mbti_profile['headline']}
- 인상: {mbti_profile['impression']}

위 성격 특성을 자연스럽게 스토리에 녹여주세요. 단, MBTI 타입(예: ENFP, ISFP 등)은 절대 언급하지 마세요."""
        
        # 어코드 & 노트 기반 풍부한 설명 생성용 데이터
        accord_details = "\n".join([
            f"- {desc['accord']}: {desc['desc1']}, {desc['desc2']}, {desc['desc3']}"
            for desc in descriptions
        ])
        
        # 추천 향수의 노트 정보 (있는 경우)
        perfume_note_context = ""
        if recommended_perfume and recommended_perfume.get("notes"):
            top_notes = ", ".join([n["name"] for n in recommended_perfume["notes"].get("top", [])[:3]])
            middle_notes = ", ".join([n["name"] for n in recommended_perfume["notes"].get("middle", [])[:3]])
            if top_notes or middle_notes:
                perfume_note_context = f"""

[참고 향수 노트 정보]
- 탑 노트: {top_notes if top_notes else "없음"}
- 미들 노트: {middle_notes if middle_notes else "없음"}

이 노트들이 왜 사용자의 취향과 잘 어울리는지 설명에 자연스럽게 녹여주세요."""

        mbti_code_fragment = f',\n  "mbti_code": "{mbti_profile["code"]}"' if mbti_profile else ""

        prompt = f"""사용자가 향수맵에서 다음 분위기를 선택했습니다:

{accord_details}{axis_section}{mbti_section}{perfume_note_context}

위 설명과 분석 결과를 바탕으로 MBTI 궁합 설명처럼 풍부하고 설득력 있는 향기카드를 작성하세요.

[작성 스타일]
- 마치 향수 조향사가 사용자의 취향을 분석하듯이 전문적이면서도 따뜻하게
- "당신은 ○○한 향에 끌리는 사람이에요. 왜냐하면..." 형식으로 이유와 근거 제시
- 어코드가 주는 감각적 경험과 그것이 사용자 성격과 어떻게 연결되는지 설명
- 구체적인 상황이나 감정을 떠올리게 하는 서술
{"- 4축 키워드(" + ", ".join(axis_keywords) + ")를 자연스럽게 녹여주세요" if axis_keywords else ""}
{"- 성격 특성을 자연스럽게 스토리에 녹여주세요. 단, MBTI 타입명(예: ENFP)은 절대 언급하지 마세요" if mbti_profile else ""}

[규칙]
- 3-4문장으로 설득력 있게 (기존보다 1-2문장 더 길게)
- 친근하고 따뜻하지만 전문적인 톤
- 제목은 5-8자로 짧고 감성적으로
- 추상적 표현보다는 구체적인 감각 묘사 우선
- 같은 입력에서는 표현 구조를 크게 바꾸지 말고 핵심 구성을 유지

[출력 형식 - JSON]
{{
  "title": "카드 제목 (5-8자)",
  "summary": "한 줄 요약 (15-20자)",
  "story": "풍부한 스토리 (3-4문장, 어코드 설명과 이유 포함)",
  "accords": [
    {{"name": "{descriptions[0]['accord']}", "description": "{descriptions[0]['desc1']}"}}
  ]{mbti_code_fragment}
}}

중요: accords 배열에는 반드시 위에서 제공된 모든 어코드를 포함하세요."""

        # LLM 호출 (안정성 강화: temperature 낮춤)
        model = "gpt-4o-mini" if use_simple_model else "gpt-4o"
        logger.info(f"🤖 LLM 카드 생성 시작: model={model}, session={session_id}")
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system", 
                    "content": "당신은 20년 경력의 향수 전문가이자 조향사입니다. 사용자의 향 취향을 분석하고, 그 취향이 어떤 성격과 라이프스타일을 반영하는지 섬세하게 설명합니다. MBTI 궁합처럼 설득력 있고 구체적으로 표현하세요."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.4,  # 안정성 강화
            top_p=0.9,
            max_tokens=700  # 더 긴 설명 가능
        )
        
        # 응답 파싱
        llm_output = json.loads(response.choices[0].message.content)
        logger.debug(f"LLM 응답 수신")
        
        # Pydantic 검증
        try:
            llm_card = LLMCardOutput(
                title=llm_output['title'],
                summary=llm_output['summary'],
                story=llm_output['story'],
                accords=[AccordInfo(**acc) for acc in llm_output['accords']]
            )
            
            # 어울리지 않는 어코드 계산
            incompatible_accords = get_incompatible_accords(selected_accords, active_mbti)
            
            # [NEW] 향 타입 정보 구성 (4축 포함)
            mbti_profile_summary = None
            if mbti_profile:
                mbti_profile_summary = {
                    "headline": mbti_profile.get("headline"),
                    "intro": mbti_profile.get("intro"),
                    "impression": mbti_profile.get("impression"),
                    "strengths": mbti_profile.get("strengths", []),
                    "weaknesses": mbti_profile.get("weaknesses", []),
                    "scent_preferences": mbti_profile.get("scent_preferences", {})
                }
            
            scent_type_info = {
                "type_name": llm_card.title,
                "type_description": llm_card.story,
                "main_accords": [acc.name for acc in llm_card.accords],
                "harmonious_accords": suggested_accords,
                "avoid_accords": incompatible_accords,
                "axis_scores": axis_scores,
                "scent_code": scent_code,
                "derived_mbti": derived_mbti,
                "axis_keywords": axis_keywords,
                "mbti_profile": mbti_profile_summary,
                "mbti_story": mbti_story
            }

            # [NEW] 프론트엔드 요구 필드 구성
            mbti_code = scent_code or 'INCX'
            active_mbti = derived_mbti or user_mbti or 'INFP'
            components = generate_mbti_components(axis_scores, mbti_code)
            
            # 추천/기피 어코드 상세 구성
            recommends = []
            for acc_name in suggested_accords[:2]:
                recommends.append({
                    "name": acc_name,
                    "reason": f"{active_mbti} 성향의 깊이를 더해주는 추천 향입니다."
                })
                
            avoids = []
            for acc_name in incompatible_accords[:2]:
                avoids.append({
                    "name": acc_name,
                    "reason": f"현재의 조화로운 분위기를 흩뜨릴 수 있는 향입니다."
                })

            # [NEW] 프론트엔드 최신 스키마(NCard) 구조로 구성
            card_data = {
                # 프론트엔드 필수 필드
                "mbti": active_mbti,
                "components": components,
                "recommends": recommends,
                "avoids": avoids,
                "story": llm_card.story,
                "summary": llm_card.summary,
                
                "scent_type": scent_type_info,
                "title": llm_card.title,
                "accords": [{"name": acc.name, "description": acc.description} for acc in llm_card.accords],
                "created_at": datetime.now().isoformat(),
                "recommended_perfume": recommended_perfume,
                "suggested_accords": suggested_accords,
                "next_actions": [
                    {
                        "type": "chatbot",
                        "title": "더 정확한 추천을 받고싶나요?",
                        "description": "센텐스의 추천챗봇을 이용해보세요!",
                        "button_text": "추천챗봇 시작하기",
                        "link": "/chat"
                    },
                    {
                        "type": "layering",
                        "title": "레이어링에 관심있으신가요?",
                        "description": "레이어링추천서비스도 이용해보세요!",
                        "button_text": "레이어링 추천받기",
                        "link": "/layering"
                    }
                ],
                "image_url": get_mbti_image_url(scent_code)
            }
            
            # 최신 스키마 검증
            ScentCardBase(
                mbti=card_data["mbti"],
                components=card_data["components"],
                recommends=card_data["recommends"],
                avoids=card_data["avoids"],
                story=card_data["story"],
                summary=card_data["summary"]
            )
            
            # MBTI 정보 추가 (있는 경우, MBTI 타입은 내부용)
            if mbti_profile:
                card_data["mbti"] = active_mbti
                card_data["mbti_code"] = llm_output.get("mbti_code", mbti_profile['code'])
                card_data["mbti_headline"] = mbti_profile['headline']
            elif session['member_id']:
                # MBTI 입력 프롬프트 (회원이지만 MBTI 없는 경우)
                card_data["mbti_prompt"] = {
                    "message": "MBTI를 알려주시면 더 좋아요!",
                    "options": ["ISTJ", "ISFJ", "INFJ", "INTJ", "ISTP", "ISFP", "INFP", "INTP",
                               "ESTJ", "ESFJ", "ENFJ", "ENTJ", "ESTP", "ESFP", "ENFP", "ENTP"]
                }
            
            generation_time_ms = int((time.time() - start_time) * 1000)
            
            # 카드 결과 저장
            card_id = None
            with get_recom_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO TB_SCENT_CARD_RESULT_T (
                            session_id,
                            member_id,
                            card_data,
                            generation_method,
                            llm_model,
                            generation_time_ms
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING card_id
                    """, (
                        session_id,
                        session['member_id'],
                        psycopg2.extras.Json(card_data),
                        'llm_full',
                        model,
                        generation_time_ms
                    ))
                    result = cur.fetchone()
                    if not result or not result[0]:
                        logger.error(f"❌ CRITICAL: INSERT 후 card_id를 받지 못함!")
                        raise ValueError("DB에서 card_id를 받아오지 못했습니다")
                    
                    card_id = result[0]
                    logger.info(f"🆔 LLM 카드 INSERT 완료: card_id={card_id} (type: {type(card_id)})")
                    
                    # 세션 업데이트
                    cur.execute("""
                        UPDATE TB_SCENT_CARD_SESSION_T
                        SET 
                            card_generated = TRUE,
                            card_generated_dt = CURRENT_TIMESTAMP
                        WHERE session_id = %s
                    """, (session_id,))
                    
                    conn.commit()
            
            if not card_id:
                logger.error(f"card_id가 None입니다")
                raise ValueError("카드 ID 생성에 실패했습니다")
            
            logger.info(f"LLM 카드 생성 완료: session={session_id}, card_id={card_id}, time={generation_time_ms}ms")
            
            result_dict = {
                "card": card_data,
                "session_id": session_id,
                "card_id": str(card_id),
                "generation_method": "llm_full",
                "generation_time_ms": generation_time_ms
            }
            
            return result_dict
        
        except Exception as validation_error:
            logger.warning(f"Pydantic 검증 실패, 템플릿으로 폴백: {validation_error}")
            return generate_template_card(session_id)
    
    except Exception as e:
        logger.error(f"LLM 카드 생성 실패, 템플릿으로 폴백: {e}")
        return generate_template_card(session_id)


def save_card(card_id: str, member_id: int) -> Dict:
    """
    생성된 카드 저장 (회원용)
    
    Args:
        card_id: 카드 ID (UUID)
        member_id: 회원 ID
    
    Returns:
        저장 결과
    """
    try:
        with get_recom_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # 카드 존재 여부 및 소유권 확인
                cur.execute("""
                    SELECT card_id, member_id 
                    FROM TB_SCENT_CARD_RESULT_T
                    WHERE card_id = %s
                """, (card_id,))
                
                card = cur.fetchone()
                if not card:
                    raise ValueError(f"카드를 찾을 수 없습니다: {card_id}")
                
                if card['member_id'] and card['member_id'] != member_id:
                    raise ValueError("본인의 카드만 저장할 수 있습니다")
                
                # 카드 저장 상태 업데이트
                cur.execute("""
                    UPDATE TB_SCENT_CARD_RESULT_T
                    SET 
                        saved = TRUE,
                        member_id = %s
                    WHERE card_id = %s
                """, (member_id, card_id))
                
                conn.commit()
        
        logger.info(f"✅ 카드 저장 완료: card_id={card_id}, member_id={member_id}")
        
        return {
            "success": True,
            "message": "카드가 저장되었습니다",
            "card_id": card_id
        }
    
    except ValueError as e:
        logger.warning(f"⚠️ 카드 저장 실패: {e}")
        return {
            "success": False,
            "message": str(e),
            "card_id": card_id
        }
    except Exception as e:
        logger.error(f"❌ 카드 저장 실패: {e}")
        return {
            "success": False,
            "message": "카드 저장에 실패했습니다",
            "card_id": card_id
        }


def get_my_cards(member_id: int, limit: int = 20, offset: int = 0) -> Dict:
    """
    내 카드 조회
    
    Args:
        member_id: 회원 ID
        limit: 조회 개수
        offset: 오프셋
    
    Returns:
        카드 리스트 및 총 개수
    """
    try:
        with get_recom_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # 총 개수 조회
                cur.execute("""
                    SELECT COUNT(*) as total
                    FROM TB_SCENT_CARD_RESULT_T
                    WHERE member_id = %s AND saved = TRUE
                """, (member_id,))
                
                total_count = cur.fetchone()['total']
                
                # 카드 리스트 조회
                cur.execute("""
                    SELECT 
                        card_id,
                        card_data,
                        generation_method,
                        created_dt,
                        last_viewed_dt
                    FROM TB_SCENT_CARD_RESULT_T
                    WHERE member_id = %s AND saved = TRUE
                    ORDER BY created_dt DESC
                    LIMIT %s OFFSET %s
                """, (member_id, limit, offset))
                
                cards = []
                for row in cur.fetchall():
                    card_item = {
                        "card_id": str(row['card_id']),
                        "card_data": row['card_data'],
                        "generation_method": row['generation_method'],
                        "created_at": row['created_dt'].isoformat() if row['created_dt'] else None,
                        "last_viewed_at": row['last_viewed_dt'].isoformat() if row['last_viewed_dt'] else None
                    }
                    cards.append(card_item)
                
                logger.info(f"내 카드 조회 완료: member_id={member_id}, count={len(cards)}/{total_count}")
                
                return {
                    "cards": cards,
                    "total_count": total_count
                }
    
    except Exception as e:
        logger.error(f"내 카드 조회 실패: {e}")
        return {
            "cards": [],
            "total_count": 0
        }
