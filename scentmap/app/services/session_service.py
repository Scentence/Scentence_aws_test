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


def generate_llm_card(session_id: str, use_simple_model: bool = False) -> Dict:
    """
    LLM 기반 향기카드 생성
    
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
        
        # LLM 프롬프트 구성
        accord_info = ""
        for desc in descriptions:
            accord_info += f"- {desc['accord']}: {desc['desc1']}, {desc['desc2']}, {desc['desc3']}\n"
        
        prompt = f"""사용자가 향수맵에서 다음 분위기를 선택했습니다:

{accord_info}

위 설명을 바탕으로 짧고 자연스러운 향기카드를 작성하세요.

[규칙]
- 주어진 설명만 사용 (과장 금지, 새로운 정보 추가 금지)
- 2-3문장으로 간결하게
- 친근하고 따뜻한 톤
- 제목은 5-7자로 짧고 감성적으로

[출력 형식 - JSON]
{{
  "title": "카드 제목 (5-7자)",
  "story": "짧은 스토리 (2-3문장, 주어진 설명만 활용)",
  "accords": [
    {{"name": "{descriptions[0]['accord']}", "description": "{descriptions[0]['desc1']}"}}
  ]
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
                "created_at": datetime.now().isoformat()
            }
            
            generation_time_ms = int((time.time() - start_time) * 1000)
            
            # 카드 결과 저장
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
                    """, (
                        session_id,
                        session['member_id'],
                        psycopg2.extras.Json(card_data),
                        'llm_full',
                        model,
                        generation_time_ms
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
            
            logger.info(f"✅ LLM 카드 생성 완료: {session_id}, 소요시간: {generation_time_ms}ms")
            
            return {
                "card": card_data,
                "session_id": session_id,
                "generation_method": "llm_full",
                "generation_time_ms": generation_time_ms
            }
        
        except Exception as validation_error:
            logger.warning(f"⚠️ Pydantic 검증 실패, 템플릿으로 폴백: {validation_error}")
            return generate_template_card(session_id)
    
    except Exception as e:
        logger.error(f"❌ LLM 카드 생성 실패, 템플릿으로 폴백: {e}")
        # 폴백: 템플릿 카드 생성
        return generate_template_card(session_id)
