# backend/agent/tools_similarity.py
import json
from langchain_core.tools import tool
from psycopg2.extras import RealDictCursor
from langchain_openai import ChatOpenAI

# 기존 DB 연결 함수 재사용
from .database import get_db_connection, release_db_connection

# 정규화용 LLM (가볍게 설정)
NORMALIZER_LLM = ChatOpenAI(
    model="gpt-4o-mini", 
    temperature=0,
    tags=["internal_helper"] 
)

@tool
def lookup_similar_perfumes_tool(user_input: str) -> str:
    """
    사용자가 언급한 향수와 '가장 유사한 향수' 3개를 찾아서 반환합니다.
    (기준: 어코드와 노트의 구성이 얼마나 겹치는지 분석)
    """
    
    # 1. 대상 향수 이름 정규화
    normalization_prompt = f"""
    User Input: "{user_input}"
    Task: Extract the Target Perfume Name user likes.
    Output JSON: {{"brand": "Brand", "name": "Name"}}
    """
    try:
        norm_result = NORMALIZER_LLM.invoke(normalization_prompt).content
        cleaned_json = norm_result.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(cleaned_json)
        target_brand = parsed.get("brand", "")
        target_name = parsed.get("name", "")
    except:
        return "검색 대상을 찾을 수 없습니다."

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # 2. 유사도 분석 쿼리 (Weighted Scoring Algorithm)
        # - 어코드 일치: +3점
        # - 노트 일치: +1점
        # - 본인 제외
        sql = """
            WITH TARGET_PERFUME AS (
                SELECT PERFUME_ID, PERFUME_NAME 
                FROM TB_PERFUME_BASIC_M 
                WHERE PERFUME_NAME ILIKE %s OR (PERFUME_BRAND ILIKE %s AND PERFUME_NAME ILIKE %s)
                LIMIT 1
            ),
            TARGET_ACCORDS AS (
                SELECT ACCORD FROM TB_PERFUME_ACCORD_R 
                WHERE PERFUME_ID = (SELECT PERFUME_ID FROM TARGET_PERFUME)
            ),
            TARGET_NOTES AS (
                SELECT NOTE FROM TB_PERFUME_NOTES_M 
                WHERE PERFUME_ID = (SELECT PERFUME_ID FROM TARGET_PERFUME)
            ),
            SIMILARITY_SCORE AS (
                SELECT 
                    p.perfume_id,
                    p.perfume_brand,
                    p.perfume_name,
                    p.img_link,
                    -- 점수 산출
                    (
                        (SELECT COUNT(*) FROM TB_PERFUME_ACCORD_R a 
                         WHERE a.perfume_id = p.perfume_id 
                         AND a.accord IN (SELECT ACCORD FROM TARGET_ACCORDS)) * 3  -- 어코드 가중치 3
                        +
                        (SELECT COUNT(*) FROM TB_PERFUME_NOTES_M n 
                         WHERE n.perfume_id = p.perfume_id 
                         AND n.note IN (SELECT NOTE FROM TARGET_NOTES)) * 1    -- 노트 가중치 1
                    ) as score
                FROM TB_PERFUME_BASIC_M p
                WHERE p.perfume_id != (SELECT PERFUME_ID FROM TARGET_PERFUME) -- 자기 자신 제외
            )
            SELECT * FROM SIMILARITY_SCORE
            WHERE score > 0
            ORDER BY score DESC
            LIMIT 3;
        """
        
        cur.execute(sql, (target_name, target_brand, f"%{target_name}%"))
        results = cur.fetchall()
        
        if not results:
            return f"'{target_brand} {target_name}'과 유사한 향수를 찾지 못했습니다."

        return json.dumps({
            "target_perfume": f"{target_brand} - {target_name}",
            "similar_list": [dict(r) for r in results]
        }, ensure_ascii=False)

    except Exception as e:
        return f"유사 향수 검색 실패: {e}"
    finally:
        cur.close()
        release_db_connection(conn)