# backend/agent/tools_info.py
import json
import re
from typing import List, Dict, Any
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from psycopg2.extras import RealDictCursor

# DB 연결 함수
from .database import get_db_connection, release_db_connection

# 스키마 임포트
from .tools_schemas_info import NoteSearchInput, AccordSearchInput, PerfumeIdSearchInput

# [내부 헬퍼 설정] (화면 출력 방지 태그 포함)
NORMALIZER_LLM = ChatOpenAI(
    model="gpt-4o-mini", temperature=0, tags=["internal_helper"]
)

# =================================================================
# [Source A] CSV 기반 감각 표현 사전 로더
# =================================================================
from .expression_loader import ExpressionLoader

# 싱글톤 로더 초기화
_expression_loader = ExpressionLoader()


# =================================================================
# Helper: 어코드 설명 주입기 (Enricher)
# =================================================================
def enrich_accord_description(text: str) -> str:
    """
    텍스트 내에 'Woody', 'Citrus' 같은 어코드 키워드가 있으면
    CSV 사전의 묘사를 괄호 안에 넣어 풍성하게 만듭니다.
    """
    if not text:
        return ""

    enriched_text = text
    
    # 일반적인 어코드 키워드 목록 (CSV에 있는 것들)
    common_accords = [
        "Animal", "Aquatic", "Chypre", "Citrus", "Creamy", "Earthy",
        "Floral", "Fougère", "Fresh", "Fruity", "Gourmand", "Green",
        "Leathery", "Oriental", "Powdery", "Resinous", "Smoky", "Spicy",
        "Sweet", "Synthetic", "Woody"
    ]
    
    for accord in common_accords:
        desc = _expression_loader.get_accord_desc(accord)
        if desc:
            pattern = re.compile(f"\\b{accord}\\b", re.IGNORECASE)
            replacement = f"{accord}({desc})"
            
            # 이미 괄호 설명이 붙어있는지 확인 후 치환
            if f"{accord}(" not in enriched_text:
                enriched_text = pattern.sub(replacement, enriched_text)

    return enriched_text


# =================================================================
# Tool 1. 향수 상세 정보 검색 (브랜드/이름 유연한 매칭 보강)
# =================================================================
@tool
def lookup_perfume_info_tool(user_input: str) -> str:
    """
    사용자가 입력한 향수 이름을 DB(영어명, 한글명, 별칭 포함)에서 정확히 찾아 상세 정보를 반환합니다.
    """
    # 1. AI를 통해 브랜드와 이름을 지능적으로 분리
    normalization_prompt = f"""
    You are a Perfume Database Expert.
    User Input: "{user_input}"
    Task: Identify Brand and Name, Convert to English.
    Example: "조말론 우드세이지" -> {{"brand": "Jo Malone", "name": "Wood Sage & Sea Salt"}}
    Output strictly JSON.
    """
    try:
        norm_result = NORMALIZER_LLM.invoke(normalization_prompt).content
        cleaned_json = norm_result.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(cleaned_json)
        target_brand = parsed.get("brand", "").strip()
        target_name = parsed.get("name", "").strip()
    except Exception as e:
        return f"검색어 분석 실패: {e}"

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # [★개선] 브랜드명 역시 부분 일치(ILIKE %brand%)를 허용하여 매칭률을 높입니다.
        sql = """
            SELECT 
                p.perfume_id, p.perfume_brand, p.perfume_name, p.img_link,
                (SELECT gender FROM TB_PERFUME_GENDER_R WHERE perfume_id = p.perfume_id LIMIT 1) as gender,
                (SELECT STRING_AGG(DISTINCT note, ', ') FROM TB_PERFUME_NOTES_M WHERE perfume_id = p.perfume_id AND type='TOP') as top_notes,
                (SELECT STRING_AGG(DISTINCT note, ', ') FROM TB_PERFUME_NOTES_M WHERE perfume_id = p.perfume_id AND type='MIDDLE') as middle_notes,
                (SELECT STRING_AGG(DISTINCT note, ', ') FROM TB_PERFUME_NOTES_M WHERE perfume_id = p.perfume_id AND type='BASE') as base_notes,
                (SELECT STRING_AGG(accord, ', ' ORDER BY ratio DESC) FROM TB_PERFUME_ACCORD_R WHERE perfume_id = p.perfume_id) as accords,
                (SELECT STRING_AGG(season, ', ' ORDER BY ratio DESC) FROM TB_PERFUME_SEASON_R WHERE perfume_id = p.perfume_id) as seasons,
                (SELECT STRING_AGG(occasion, ', ' ORDER BY ratio DESC) FROM TB_PERFUME_OCA_R WHERE perfume_id = p.perfume_id) as occasions
            FROM TB_PERFUME_BASIC_M p
            LEFT JOIN TB_PERFUME_NAME_KR n ON p.perfume_id = n.perfume_id
            
            WHERE p.perfume_brand ILIKE %s -- [★수정] 브랜드도 부분 일치 허용
              AND (
                  REPLACE(REPLACE(p.perfume_name, ' ', ''), '-', '') ILIKE %s
                  OR REPLACE(REPLACE(n.name_kr, ' ', ''), '-', '') ILIKE %s
                  OR REPLACE(REPLACE(n.search_keywords, ' ', ''), '-', '') ILIKE %s
              )
            
            ORDER BY 
                CASE 
                    WHEN p.perfume_name ILIKE %s THEN 0 
                    WHEN n.name_kr ILIKE %s THEN 1     
                    WHEN n.search_keywords ILIKE %s THEN 2 
                    ELSE 3 
                END,
                LENGTH(p.perfume_name) ASC 
            LIMIT 1
        """

        # 검색어 전처리: 브랜드와 이름 모두 유연하게 매칭되도록 와일드카드 추가
        brand_pattern = (
            f"%{target_brand}%"  # Jo Malone -> %Jo Malone% (London까지 매칭)
        )
        clean_target_name = target_name.replace(" ", "").replace("-", "")
        name_pattern = f"%{clean_target_name}%"

        params = (
            brand_pattern,  # 브랜드 부분 일치
            name_pattern,  # 이름 유연 매칭
            name_pattern,
            name_pattern,
            target_name,  # 정렬용 원본
            target_name,
            f"%,{target_name},%",
        )

        cur.execute(sql, params)
        result = cur.fetchone()

        if result:
            return json.dumps(dict(result), ensure_ascii=False)
        else:
            return f"DB 검색 실패: '{target_brand} - {target_name}'을 찾을 수 없습니다."
    except Exception as e:
        return f"DB 에러: {e}"
    finally:
        cur.close()
        release_db_connection(conn)


# =================================================================
# Tool 1-2. 향수 ID 기반 상세 조회 (id-first)
# =================================================================
@tool(args_schema=PerfumeIdSearchInput)
async def lookup_perfume_by_id_tool(perfume_id: int) -> str:
    """
    perfume_id를 받아 향수 상세 정보를 반환합니다.
    """
    conn = None
    cur = None
    try:
        conn = await get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        sql = """
            SELECT 
                p.perfume_id, p.perfume_brand, p.perfume_name, p.img_link,
                (SELECT gender FROM TB_PERFUME_GENDER_R WHERE perfume_id = p.perfume_id LIMIT 1) as gender,
                (SELECT STRING_AGG(DISTINCT note, ', ') FROM TB_PERFUME_NOTES_M WHERE perfume_id = p.perfume_id AND type='TOP') as top_notes,
                (SELECT STRING_AGG(DISTINCT note, ', ') FROM TB_PERFUME_NOTES_M WHERE perfume_id = p.perfume_id AND type='MIDDLE') as middle_notes,
                (SELECT STRING_AGG(DISTINCT note, ', ') FROM TB_PERFUME_NOTES_M WHERE perfume_id = p.perfume_id AND type='BASE') as base_notes,
                (SELECT STRING_AGG(accord, ', ' ORDER BY ratio DESC) FROM TB_PERFUME_ACCORD_R WHERE perfume_id = p.perfume_id) as accords,
                (SELECT STRING_AGG(season, ', ' ORDER BY ratio DESC) FROM TB_PERFUME_SEASON_R WHERE perfume_id = p.perfume_id) as seasons,
                (SELECT STRING_AGG(occasion, ', ' ORDER BY ratio DESC) FROM TB_PERFUME_OCA_R WHERE perfume_id = p.perfume_id) as occasions
            FROM TB_PERFUME_BASIC_M p
            WHERE p.perfume_id = %s
        """
        
        cur.execute(sql, (perfume_id,))
        result = cur.fetchone()
        
        if result:
            return json.dumps(dict(result), ensure_ascii=False)
        else:
            return f"DB 검색 실패: perfume_id={perfume_id}"
    except Exception as e:
        return f"DB 에러: {e}"
    finally:
        if cur:
            cur.close()
        if conn:
            release_db_connection(conn)


# =================================================================
# Tool 2. 노트 정보 검색 (사전 + DB 병합)
# =================================================================
@tool(args_schema=NoteSearchInput)
def lookup_note_info_tool(keywords: List[str]) -> str:
    """
    노트(원료) 리스트를 받아 [감각적 묘사]와 [관련 어코드 설명]을 포함한 상세 정보를 반환합니다.
    """
    # 1. 노트 이름 정규화
    normalization_prompt = f"""
    You are a Fragrance Ingredient Expert.
    User Keywords: {keywords}
    Task: Translate keywords to official English Perfumery Notes (Singular, Capitalized).
    Strictly interpret in PERFUME context (e.g., '통카' -> "Tonka Bean").
    Output strictly JSON List.
    """
    try:
        norm_result = NORMALIZER_LLM.invoke(normalization_prompt).content
        cleaned = norm_result.replace("```json", "").replace("```", "").strip()
        target_notes = json.loads(cleaned)
    except:
        target_notes = keywords

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    final_info = {}

    try:
        for note in target_notes:
            # (D) [대표 향수 조회]
            # [유지] GROUP BY를 추가하여 한 향수가 여러 번 잡히는 문제(Top/Middle 등) 해결
            sql_perfumes = """
                SELECT 
                    m.perfume_brand, 
                    m.perfume_name
                FROM TB_PERFUME_NOTES_M n
                JOIN TB_PERFUME_BASIC_M m ON n.perfume_id = m.perfume_id
                LEFT JOIN (
                    SELECT PERFUME_ID, SUM(VOTE) as total_votes
                    FROM TB_PERFUME_ACCORD_M
                    GROUP BY PERFUME_ID
                ) pop ON m.perfume_id = pop.PERFUME_ID
                WHERE n.note ILIKE %s
                GROUP BY m.perfume_id, m.perfume_brand, m.perfume_name, pop.total_votes
                ORDER BY pop.total_votes DESC NULLS LAST
                LIMIT 3
            """
            cur.execute(sql_perfumes, (f"%{note}%",))
            examples = [
                f"{r['perfume_brand']} {r['perfume_name']}" for r in cur.fetchall()
            ]

            if not examples:
                continue

            # (A) 사전 조회 (CSV 로더 사용)
            dict_desc = _expression_loader.get_note_desc(note)

            # (B) DB 상세 설명 조회
            sql_desc = "SELECT description FROM TB_NOTE_EMBEDDING_M WHERE note ILIKE %s LIMIT 1"
            cur.execute(sql_desc, (note,))
            row = cur.fetchone()
            db_desc = row["description"] if row else ""

            # (C) 병합 및 어코드 설명 주입
            enriched_db_desc = enrich_accord_description(db_desc)

            if dict_desc and enriched_db_desc:
                full_description = f"{dict_desc}\n\n[상세 특징]: {enriched_db_desc}"
            elif dict_desc:
                full_description = dict_desc
            elif enriched_db_desc:
                full_description = enriched_db_desc
            else:
                full_description = "상세 설명 정보가 없습니다."

            final_info[note] = {
                "description": full_description,
                "representative_perfumes": examples,
            }

        return json.dumps(final_info, ensure_ascii=False)
    except Exception as e:
        return f"Error: {e}"
    finally:
        cur.close()
        release_db_connection(conn)


# =================================================================
# Tool 3. 어코드 정보 검색 (수정: 중복 제거 GROUP BY 추가)
# =================================================================
@tool(args_schema=AccordSearchInput)
def lookup_accord_info_tool(keywords: List[str]) -> str:
    """
    어코드(향조) 리스트를 받아 [사전적 분위기 묘사]와 [대표 향수]를 반환합니다.
    """
    normalization_prompt = f"""
    You are a Fragrance Accord Expert.
    User Keywords: {keywords}
    Task: Translate to official English Accords.
    Output strictly JSON List.
    """
    try:
        norm_result = NORMALIZER_LLM.invoke(normalization_prompt).content
        cleaned = norm_result.replace("```json", "").replace("```", "").strip()
        target_accords = json.loads(cleaned)
    except:
        target_accords = keywords

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    final_info = {}

    try:
        for accord in target_accords:
            # (B) 대표 향수 조회
            # [유지] ILIKE 매칭으로 인한 중복 가능성을 제거하기 위해 GROUP BY 추가
            sql = """
                SELECT m.perfume_brand, m.perfume_name
                FROM TB_PERFUME_ACCORD_M a
                JOIN TB_PERFUME_BASIC_M m ON a.perfume_id = m.perfume_id
                WHERE a.accord ILIKE %s
                GROUP BY m.perfume_id, m.perfume_brand, m.perfume_name
                ORDER BY MAX(a.vote) DESC NULLS LAST
                LIMIT 3
            """
            cur.execute(sql, (f"%{accord}%",))
            examples = [
                f"{r['perfume_brand']} {r['perfume_name']}" for r in cur.fetchall()
            ]

            if not examples:
                continue

            # (A) 사전 조회 (CSV 로더 사용)
            desc = _expression_loader.get_accord_desc(accord)
            if not desc:
                desc = "특정한 분위기를 자아내는 향의 계열입니다."
            else:
                desc = f"{accord}: {desc}"

            final_info[accord] = {
                "description": desc,
                "representative_perfumes": examples,
            }

        return json.dumps(final_info, ensure_ascii=False)
    except Exception as e:
        return f"Error: {e}"
    finally:
        cur.close()
        release_db_connection(conn)
