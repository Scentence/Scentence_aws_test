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
# [Source A] 감각 표현 사전 (Curated Dictionary)
# =================================================================
# 어코드 표현 사전
ACCORD_EXPRESSION_DICT = {
    "Animal": "야생 동물의 가죽이나 털에서 느껴지는 원초적이고 관능적인 체취",
    "Aquatic": "탁 트인 바다나 시원한 계곡물에서 느껴지는 물기 어린 투명한 향",
    "Chypre": "축축한 이끼와 흙, 그리고 꽃향기가 어우러진 클래식하고 성숙한 분위기",
    "Citrus": "한여름의 레몬 에이드처럼 톡 쏘는 상큼함과 청량함",
    "Creamy": "따뜻하게 데운 우유나 버터처럼 부드럽고 녹진하게 감싸는 느낌",
    "Earthy": "비 내린 뒤 젖은 흙이나 숲의 바닥에서 올라오는 자연 그대로의 흙내음",
    "Floral": "다채로운 꽃들이 만발한 정원에 들어선 듯한 화사하고 우아한 향",
    "Fougère": "이발소에서 갓 면도를 마친 뒤 바르는 스킨처럼 깔끔하고 남성적인 젠틀함",
    "Fresh": "아침 공기처럼 맑고 깨끗하며, 갓 씻고 나온 듯한 산뜻한 분위기",
    "Fruity": "잘 익은 복숭아나 베리류를 한 입 베어 문 듯한 달콤하고 귀여운 과즙 향",
    "Gourmand": "바닐라, 초콜릿, 카라멜처럼 먹고 싶을 만큼 달콤하고 맛있는 향",
    "Green": "손으로 으깬 풀잎이나 갓 깎은 잔디에서 나는 싱그러운 풀내음",
    "Leathery": "고급 가죽 자켓이나 새 차 시트에서 나는 거칠면서도 섹시한 가죽 냄새",
    "Oriental": "신비로운 향신료와 진득한 달콤함이 섞인 관능적이고 깊은 밤의 분위기",
    "Powdery": "아기 분 냄새나 화장품 파우더처럼 보송보송하고 포근한 느낌",
    "Resinous": "소나무 송진이나 굳은 호박석에서 느껴지는 끈적하고 깊이 있는 따뜻함",
    "Smoky": "타닥타닥 타오르는 장작불이나 향에서 피어오르는 그윽하고 매캐한 연기 향",
    "Spicy": "후추나 계피처럼 코끝을 톡 쏘는 알싸하고 이국적인 매력",
    "Sweet": "설탕 시럽이나 솜사탕처럼 기분 좋게 녹아드는 직관적인 달콤함",
    "Synthetic": "차가운 금속이나 잘 다림질된 옷감처럼 현대적이고 인공적인 세련미",
    "Woody": "비 온 뒤 숲속을 거닐 때 느껴지는 묵직하고 차분한 나무의 기운",
}

# 노트 표현 사전
NOTE_EXPRESSION_DICT = {
    "Vetiver": "비 온 뒤 촉촉하게 젖은 흙내음과 마른 풀의 스모키함이 섞인 향",
    "Tonka Bean": "달콤한 바닐라와 아몬드, 그리고 약간의 계피 향이 섞인 따뜻하고 파우더리한 향",
    "Aldehyde": "갓 세탁하고 나온 셔츠에서 나는 쨍하고 깨끗한 비누 거품 향",
    "Musk": "아기 살결처럼 보송보송하고 포근하게 감싸주는 따뜻한 살냄새",
    "Rose": "새벽 이슬을 머금은 생장미의 싱그러움과 벨벳 같은 우아함",
    "Bergamot": "홍차(얼그레이)를 마실 때 느껴지는 쌉싸름하면서도 고급스러운 시트러스 향",
    "Sandalwood": "오래된 사찰이나 절에서 느껴지는 부드럽고 크리미한 나무 향",
    "Oud": "깊고 어두운 숲속의 젖은 나무와 가죽이 연상되는 중후하고 콤콤한 향",
    "Vanilla": "따뜻하게 데워진 우유에 설탕을 녹인 듯한 부드럽고 달콤한 향",
    "Amber": "호박석처럼 따뜻하고 달콤하며 파우더리한, 신비로운 동양의 향",
    "Patchouli": "젖은 흙과 낙엽이 쌓인 숲 바닥에서 올라오는 쌉싸름하고 어두운 풀내음",
    "Fig": "무화과 나무의 잎사귀에서 나는 쌉싸름한 풀내음과 과육의 크리미한 달콤함",
}


# =================================================================
# Helper: 어코드 설명 주입기 (Enricher)
# =================================================================
def enrich_accord_description(text: str) -> str:
    """
    텍스트 내에 'Woody', 'Citrus' 같은 어코드 키워드가 있으면
    사전의 묘사를 괄호 안에 넣어 풍성하게 만듭니다.
    """
    if not text:
        return ""

    enriched_text = text
    for accord, desc in ACCORD_EXPRESSION_DICT.items():
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

            # (A) 사전 조회
            dict_desc = ""
            for key, val in NOTE_EXPRESSION_DICT.items():
                if key.lower() in note.lower() or note.lower() in key.lower():
                    dict_desc = val
                    break

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

            # (A) 사전 조회
            desc = "특정한 분위기를 자아내는 향의 계열입니다."
            for key, val in ACCORD_EXPRESSION_DICT.items():
                if key.lower() == accord.lower():
                    desc = f"{key}: {val}"
                    break

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
