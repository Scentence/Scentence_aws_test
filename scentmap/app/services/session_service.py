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
from scentmap.app.schemas.card_schema import ScentCard, AccordInfo

logger = logging.getLogger(__name__)

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# MBTI 데이터 캐시
_mbti_data_cache = None


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
        
        logger.info(f"✅ MBTI 데이터 로드 완료: {len(_mbti_data_cache)}개")
        return _mbti_data_cache
    
    except Exception as e:
        logger.error(f"❌ MBTI 데이터 로드 실패: {e}")
        return []


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
    
    logger.warning(f"⚠️ MBTI 프로필을 찾을 수 없음: {mbti}")
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
                    logger.info(f"✅ 회원 MBTI 조회 완료: member_id={member_id}, mbti={mbti}")
                else:
                    logger.warning(f"⚠️ 회원 MBTI 없음: member_id={member_id}")
                
                return mbti
    
    except Exception as e:
        logger.error(f"❌ 회원 MBTI 조회 실패: {e}")
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
                    logger.info(f"♻️ 기존 템플릿 카드 반환: session={session_id}, card_id={existing_card_id}")
                    
                    result_dict = {
                        "card": existing_card['card_data'],
                        "session_id": session_id,
                        "card_id": existing_card_id,
                        "generation_method": existing_card['generation_method']
                    }
                    
                    logger.info(f"📦 기존 템플릿 카드 반환 데이터 검증: card_id={result_dict.get('card_id')}, keys={list(result_dict.keys())}")
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
            "created_at": datetime.now().isoformat(),
            
            # [NEW] 다음 단계 CTA
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
            
            # [NEW] 카드 이미지 (MBTI별 이미지, 현재는 고정)
            "image_url": get_mbti_image_url(None)
        }
        
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
                    logger.error(f"❌ CRITICAL: INSERT 후 card_id를 받지 못함!")
                    raise ValueError("DB에서 card_id를 받아오지 못했습니다")
                
                card_id = result[0]
                logger.info(f"🆔 템플릿 카드 INSERT 완료: card_id={card_id} (type: {type(card_id)})")
                
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
            logger.error(f"❌ CRITICAL: card_id가 None입니다!")
            raise ValueError("카드 ID 생성에 실패했습니다")
        
        logger.info(f"✅ 템플릿 카드 생성 완료: session={session_id}, card_id={card_id}")
        
        result_dict = {
            "card": card_data,
            "session_id": session_id,
            "card_id": str(card_id),
            "generation_method": "template"
        }
        
        logger.info(f"📦 템플릿 카드 반환 데이터 검증: card_id={result_dict.get('card_id')}, keys={list(result_dict.keys())}")
        
        return result_dict
    
    except Exception as e:
        logger.error(f"❌ 템플릿 카드 생성 실패: {e}", exc_info=True)
        logger.error(f"   session_id: {session_id}")
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
                
                selected_accords = session['selected_accords'] or []
                if not selected_accords:
                    raise ValueError("선택된 어코드가 없습니다")
        
        # 어코드 설명 조회
        descriptions = get_accord_descriptions(selected_accords)
        
        if not descriptions:
            raise ValueError("어코드 설명을 찾을 수 없습니다")
        
        # 회원 MBTI 조회 (회원인 경우)
        mbti_profile = None
        user_mbti = None
        if session['member_id']:
            user_mbti = get_member_mbti(session['member_id'])
            if user_mbti:
                mbti_profile = get_mbti_profile(user_mbti)
        
        # LLM 프롬프트 구성
        accord_info = ""
        for desc in descriptions:
            accord_info += f"- {desc['accord']}: {desc['desc1']}, {desc['desc2']}, {desc['desc3']}\n"
        
        # MBTI 정보 추가 (회원인 경우)
        mbti_section = ""
        if mbti_profile:
            mbti_section = f"""

[사용자 MBTI 정보]
- MBTI: {mbti_profile['mbti']}
- 향 코드: {mbti_profile['code']}
- 향 성격: {mbti_profile['headline']}
- 인상: {mbti_profile['impression']}

위 MBTI 정보를 활용하여 "{mbti_profile['mbti']}인 당신은..."과 같이 자연스럽게 스토리에 녹여주세요."""
        
        mbti_code_fragment = f',\n  "mbti_code": "{mbti_profile["code"]}"' if mbti_profile else ""

        prompt = f"""사용자가 향수맵에서 다음 분위기를 선택했습니다:

{accord_info}{mbti_section}

위 설명을 바탕으로 짧고 자연스러운 향기카드를 작성하세요.

[규칙]
- 주어진 설명만 사용 (과장 금지, 새로운 정보 추가 금지)
- 2-3문장으로 간결하게
- 친근하고 따뜻한 톤
- 제목은 5-7자로 짧고 감성적으로
{"- MBTI 정보가 있다면 자연스럽게 스토리에 녹여주세요" if mbti_profile else ""}

[출력 형식 - JSON]
{{
  "title": "카드 제목 (5-7자)",
  "story": "짧은 스토리 (2-3문장, 주어진 설명만 활용{', MBTI 정보 포함' if mbti_profile else ''})",
  "accords": [
    {{"name": "{descriptions[0]['accord']}", "description": "{descriptions[0]['desc1']}"}}
  ]{mbti_code_fragment}
}}

중요: accords 배열에는 반드시 위에서 제공된 모든 어코드를 포함하세요."""

        # LLM 호출
        model = "gpt-4o-mini" if use_simple_model else "gpt-4o"
        logger.info(f"🤖 LLM 카드 생성 시작: model={model}, session={session_id}")
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system", 
                    "content": "당신은 향수 전문가입니다. 사용자의 취향을 바탕으로 자연스럽고 감성적인 향기카드를 작성합니다."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
            max_tokens=500
        )
        
        # 응답 파싱
        llm_output = json.loads(response.choices[0].message.content)
        logger.info(f"✅ LLM 응답 수신: {llm_output}")
        
        # Pydantic 검증
        try:
            card = ScentCard(
                title=llm_output['title'],
                story=llm_output['story'],
                accords=[AccordInfo(**acc) for acc in llm_output['accords']]
            )
            
            card_data = {
                "title": card.title,
                "story": card.story,
                "accords": [{"name": acc.name, "description": acc.description} for acc in card.accords],
                "created_at": datetime.now().isoformat(),
                
                # [NEW] 다음 단계 CTA
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
                
                # [NEW] 카드 이미지 (MBTI별 이미지, 현재는 고정)
                "image_url": get_mbti_image_url(mbti_profile['code'] if mbti_profile else None)
            }
            
            # MBTI 정보 추가 (있는 경우)
            if mbti_profile:
                card_data["mbti"] = user_mbti
                card_data["mbti_code"] = llm_output.get("mbti_code", mbti_profile['code'])
                card_data["mbti_headline"] = mbti_profile['headline']
            else:
                # [NEW] MBTI 안내 (회원이지만 MBTI 없는 경우)
                if session['member_id']:
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
                logger.error(f"❌ CRITICAL: card_id가 None입니다!")
                raise ValueError("카드 ID 생성에 실패했습니다")
            
            logger.info(f"✅ LLM 카드 생성 완료: session={session_id}, card_id={card_id}, 소요시간: {generation_time_ms}ms")
            
            result_dict = {
                "card": card_data,
                "session_id": session_id,
                "card_id": str(card_id),
                "generation_method": "llm_full",
                "generation_time_ms": generation_time_ms
            }
            
            logger.info(f"📦 LLM 카드 반환 데이터 검증: card_id={result_dict.get('card_id')}, keys={list(result_dict.keys())}")
            
            return result_dict
        
        except Exception as validation_error:
            logger.warning(f"⚠️ Pydantic 검증 실패, 템플릿으로 폴백: {validation_error}", exc_info=True)
            fallback_result = generate_template_card(session_id)
            logger.info(f"📦 폴백 결과 (Pydantic 실패): card_id={fallback_result.get('card_id')}")
            return fallback_result
    
    except Exception as e:
        logger.error(f"❌ LLM 카드 생성 실패, 템플릿으로 폴백: {e}", exc_info=True)
        # 폴백: 템플릿 카드 생성
        fallback_result = generate_template_card(session_id)
        logger.info(f"📦 폴백 결과 (LLM 실패): card_id={fallback_result.get('card_id')}")
        return fallback_result


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
                
                logger.info(f"✅ 내 카드 조회 완료: member_id={member_id}, count={len(cards)}/{total_count}")
                
                return {
                    "cards": cards,
                    "total_count": total_count
                }
    
    except Exception as e:
        logger.error(f"❌ 내 카드 조회 실패: {e}")
        return {
            "cards": [],
            "total_count": 0
        }
