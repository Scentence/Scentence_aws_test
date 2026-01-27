# backend/agent/database.py
import os
import traceback
import json
import asyncio
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2 import pool  # [최적화] 커넥션 풀 도입
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from openai import OpenAI, AsyncOpenAI  # [최적화] 비동기 클라이언트 추가

# 오탈자 보정 라이브러리
try:
    from Levenshtein import distance
except ImportError:

    def distance(s1, s2):
        return 0 if s1 == s2 else 100


load_dotenv()

# ==========================================
# 0. 설정 및 초기화 (커넥션 풀 및 비동기 클라이언트)
# ==========================================
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "perfume_db"),
    "user": os.getenv("DB_USER", "scentence"),
    "password": os.getenv("DB_PASSWORD", "scentence"),
    "host": os.getenv("DB_HOST", "host.docker.internal"),
    "port": os.getenv("DB_PORT", "5432"),
}

# [최적화] 병렬 처리를 위한 커넥션 풀 생성 (최소 1개, 최대 20개 유지)
perfume_db_pool = pool.ThreadedConnectionPool(1, 20, **DB_CONFIG)

RECOM_DB_CONFIG = {
    **DB_CONFIG,
    "dbname": os.getenv("RECOM_DB_NAME", "recom_db"),
}
recom_db_pool = pool.ThreadedConnectionPool(1, 20, **RECOM_DB_CONFIG)

# [최적화] 동기/비동기 OpenAI 클라이언트 이원화
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

BRAND_CACHE = []


# [복구 및 최적화] 커넥션 풀을 사용하는 핵심 함수 4인방

# [함수 수정] 풀에서 연결 가져오기 및 반납 로직
def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def get_embedding(text: str) -> List[float]:
    try:
        if not text:
            return []
        return (
            client.embeddings.create(
                input=text.replace("\n", " "), model="text-embedding-3-small"
            )
            .data[0]
            .embedding
        )
    except Exception as e:
        print(f"⚠️ Sync Embedding Error: {e}")
        return []


# ==========================================
# 1. 브랜드 및 메타데이터 관리
# ==========================================
def get_all_brands() -> List[str]:
    global BRAND_CACHE
    if BRAND_CACHE:
        return BRAND_CACHE

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT DISTINCT perfume_brand FROM TB_PERFUME_BASIC_M")
        BRAND_CACHE = [r[0] for r in cur.fetchall() if r[0]]
        return BRAND_CACHE
    finally:
        cur.close()
        release_db_connection(conn)


def match_brand_name(user_input: str) -> str:
    if not user_input:
        return user_input
    all_brands = get_all_brands()
    for b in all_brands:
        if b.lower() == user_input.lower():
            return b

    try:
        brands_str = ", ".join(all_brands)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a Brand Matcher. Return ONLY the exact brand name or 'None'.",
                },
                {
                    "role": "user",
                    "content": f"List: [{brands_str}]\nInput: {user_input}",
                },
            ],
            temperature=0,
        )
        matched = response.choices[0].message.content.strip()
        if matched and matched != "None" and matched in all_brands:
            return matched
    except Exception:
        pass
    return user_input


def fetch_meta_data() -> Dict[str, str]:
    meta = {}
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT season FROM TB_PERFUME_SEASON_R")
        meta["seasons"] = ", ".join([str(r[0]) for r in cur.fetchall() if r[0]])
        cur.execute("SELECT DISTINCT occasion FROM TB_PERFUME_OCA_R")
        meta["occasions"] = ", ".join([str(r[0]) for r in cur.fetchall() if r[0]])
        cur.execute("SELECT DISTINCT accord FROM TB_PERFUME_ACCORD_R LIMIT 100")
        meta["accords"] = ", ".join([str(r[0]) for r in cur.fetchall() if r[0]])
        meta["genders"] = "Women, Men, Unisex"
    except Exception:
        meta = {}
    finally:
        if conn:
            cur.close()
            release_db_connection(conn)
    return meta


# ==========================================
# 2. 검색 엔진 (Connection Pool 적용)
# ==========================================
def search_perfumes(
    hard_filters: Dict[str, Any],
    strategy_filters: Dict[str, List[str]],
    exclude_ids: List[int] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        sql = """
            SELECT DISTINCT m.perfume_id as id, m.perfume_brand as brand, m.perfume_name as name, m.img_link as image_url,
            (SELECT STRING_AGG(DISTINCT accord, ', ') FROM TB_PERFUME_ACCORD_R WHERE perfume_id = m.perfume_id) as accords,
            (SELECT gender FROM TB_PERFUME_GENDER_R WHERE perfume_id = m.perfume_id LIMIT 1) as gender,
            (SELECT STRING_AGG(DISTINCT n.note, ', ') FROM TB_PERFUME_NOTES_M n WHERE n.perfume_id = m.perfume_id AND UPPER(n.type) = 'TOP') as top_notes,
            (SELECT STRING_AGG(DISTINCT n.note, ', ') FROM TB_PERFUME_NOTES_M n WHERE n.perfume_id = m.perfume_id AND UPPER(n.type) = 'MIDDLE') as middle_notes,
            (SELECT STRING_AGG(DISTINCT n.note, ', ') FROM TB_PERFUME_NOTES_M n WHERE n.perfume_id = m.perfume_id AND UPPER(n.type) = 'BASE') as base_notes
            FROM TB_PERFUME_BASIC_M m
        """
        params, where_clauses = [], []

        if exclude_ids:
            where_clauses.append(
                f"m.perfume_id NOT IN ({','.join(['%s']*len(exclude_ids))})"
            )
            params.extend(exclude_ids)

        if hard_filters.get("gender"):
            g = hard_filters["gender"].lower()

            if g in ["women", "female"]:
                # 여성용 요청 시: 여성용 + 유니섹스 포함
                where_clauses.append(
                    "m.perfume_id IN (SELECT perfume_id FROM TB_PERFUME_GENDER_R WHERE gender IN (%s, %s))"
                )
                params.extend(["Feminine", "Unisex"])  # 여기서 값을 추가합니다.

            elif g in ["men", "male"]:
                # 남성용 요청 시: 남성용 + 유니섹스 포함
                where_clauses.append(
                    "m.perfume_id IN (SELECT perfume_id FROM TB_PERFUME_GENDER_R WHERE gender IN (%s, %s))"
                )
                params.extend(["Masculine", "Unisex"])  # 여기서 값을 추가합니다.

            else:
                # 유니섹스 요청 시: 오직 'Unisex'만 검색
                where_clauses.append(
                    "m.perfume_id IN (SELECT perfume_id FROM TB_PERFUME_GENDER_R WHERE gender = %s)"
                )
                params.append("Unisex")  # 여기서 값을 추가합니다.

        if hard_filters.get("brand"):
            where_clauses.append("m.perfume_brand ILIKE %s")
            params.append(match_brand_name(hard_filters["brand"]))

        hard_meta_map = {
            "season": ("TB_PERFUME_SEASON_R", "season"),
            "occasion": ("TB_PERFUME_OCA_R", "occasion"),
            "accord": ("TB_PERFUME_ACCORD_R", "accord"),
            "note": ("TB_PERFUME_NOTES_M", "note"),
        }
        for k, (t, c) in hard_meta_map.items():
            if hard_filters.get(k):
                where_clauses.append(
                    f"m.perfume_id IN (SELECT perfume_id FROM {t} WHERE {c} ILIKE %s)"
                )
                params.append(hard_filters[k])

        strategy_map = {
            "accord": ("TB_PERFUME_ACCORD_R", "accord"),
            "season": ("TB_PERFUME_SEASON_R", "season"),
            "occasion": ("TB_PERFUME_OCA_R", "occasion"),
            "note": ("TB_PERFUME_NOTES_M", "note"),
        }
        for k, vals in strategy_filters.items():
            if not vals or k == "gender":
                continue
            mapping = strategy_map.get(k.lower())
            if mapping:
                t, c = mapping
                clauses = [
                    f"m.perfume_id IN (SELECT perfume_id FROM {t} WHERE {c} ILIKE %s)"
                    for v in vals
                ]
                params.extend(vals)
                where_clauses.append(f"({' OR '.join(clauses)})")

        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
        sql += f" LIMIT {limit}"
        cur.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]
    finally:
        cur.close()
        release_db_connection(conn)


# ==========================================
# 3. 비동기 리랭킹 엔진
# ==========================================
async def rerank_perfumes_async(
    candidates: List[Dict[str, Any]], query_text: str, top_k: int = 5
) -> List[Dict[str, Any]]:
    if not candidates or not query_text:
        return candidates[:top_k]
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # [최적화] 비동기 번역 및 스타일링
        system_prompt = "You are a Perfume Data Analyst. Transform the Korean logic into a sensory description..."
        translation = await async_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query_text},
            ],
            temperature=0,
        )
        stylized_query = translation.choices[0].message.content.strip()
        query_vector = await get_embedding_async(stylized_query)
        if not query_vector:
            return candidates[:top_k]

        candidate_ids = [p["id"] for p in candidates]
        placeholders = ",".join(["%s"] * len(candidate_ids))
        sql = f"""
            SELECT m.perfume_id, MAX(1 - (e.embedding <=> %s::vector)) as similarity_score,
            (ARRAY_AGG(m.content ORDER BY (e.embedding <=> %s::vector) ASC))[1] as best_review
            FROM TB_PERFUME_REVIEW_M m
            JOIN TB_REVIEW_EMBEDDING_M e ON m.review_id = e.review_id
            WHERE m.perfume_id IN ({placeholders})
            GROUP BY m.perfume_id
            ORDER BY similarity_score DESC
        """
        cur.execute(sql, [query_vector, query_vector] + candidate_ids)
        scores = {row["perfume_id"]: row for row in cur.fetchall()}

        reranked = []
        for p in candidates:
            sc = scores.get(
                p["id"], {"similarity_score": 0, "best_review": "관련 리뷰 없음"}
            )
            p.update(
                {
                    "review_score": sc["similarity_score"],
                    "best_review": sc["best_review"],
                }
            )
            reranked.append(p)
        reranked.sort(key=lambda x: x.get("review_score", 0), reverse=True)
        return reranked[:top_k]
    finally:
        cur.close()
        release_db_connection(conn)


# ==========================================
# 6. Recom DB 연결 및 저장 함수 (디버깅 강화판)
# ==========================================

# [설정] 추천/회원 데이터용 DB 설정
RECOM_DB_CONFIG = {
    **DB_CONFIG,
    "dbname": os.getenv("RECOM_DB_NAME", "recom_db"),
}


def get_recom_db_connection():
    # 연결 시도 직전에 접속 정보 출력
    print(
        f"   🔌 [DB접속시도] DB명: {RECOM_DB_CONFIG['dbname']} | Host: {RECOM_DB_CONFIG['host']}",
        flush=True,
    )
    return psycopg2.connect(**RECOM_DB_CONFIG)


def save_recommendation_log(
    member_id: int, perfumes: List[Dict[str, Any]], reason: str
):
    if not member_id or not perfumes:
        return
    conn = get_recom_db_connection()
    try:
        cur = conn.cursor()
        sql = "INSERT INTO TB_MEMBER_RECOM_RESULT_T (MEMBER_ID, PERFUME_ID, PERFUME_NAME, RECOM_TYPE, RECOM_REASON, INTEREST_YN) VALUES (%s, %s, %s, 'GENERAL', %s, 'N')"
        for p in perfumes:
            cur.execute(sql, (member_id, p.get("id"), p.get("name"), reason))
        conn.commit()
        print(
            f"   ✅ [Success] 추천 이력 저장 완료! (DB: {RECOM_DB_CONFIG['dbname']})",
            flush=True,
        )

    except Exception as e:
        print(f"   🔥 [Error] 추천 이력 저장 실패: {e}", flush=True)
        if conn:
            conn.rollback()
    finally:
        cur.close()
        release_recom_db_connection(conn)


def add_my_perfume(member_id: int, perfume_id: int, perfume_name: str):
    conn = get_recom_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM TB_MEMBER_MY_PERFUME_T WHERE MEMBER_ID = %s AND PERFUME_ID = %s",
            (member_id, perfume_id),
        )
        if cur.fetchone():
            return {"status": "already_exists", "message": "이미 저장된 향수입니다."}

        # 2. 신규 저장
        insert_sql = """
            INSERT INTO TB_MEMBER_MY_PERFUME_T
            (MEMBER_ID, PERFUME_ID, PERFUME_NAME, REGISTER_STATUS, PREFERENCE)
            VALUES (%s, %s, %s, 'HAVE', 'GOOD')
        """
        cur.execute(insert_sql, (member_id, perfume_id, perfume_name))
        conn.commit()
        return {"status": "success", "message": "향수가 저장되었습니다."}
    finally:
        cur.close()
        release_recom_db_connection(conn)


# ==========================================
# 5. 채팅 시스템 (Connection Pool 적용)
# ==========================================
def save_chat_message(
    thread_id: str, member_id: int, role: str, message: str, meta: dict = None
):
    conn = get_recom_db_connection()
    try:
        cur = conn.cursor()
        title_snippet = message[:30] + "..." if len(message) > 30 else message
        cur.execute(
            """
            INSERT INTO TB_CHAT_THREAD_T (THREAD_ID, MEMBER_ID, TITLE, LAST_CHAT_DT) VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (THREAD_ID) DO UPDATE SET LAST_CHAT_DT = CURRENT_TIMESTAMP, TITLE = CASE WHEN TB_CHAT_THREAD_T.TITLE IS NULL OR TB_CHAT_THREAD_T.TITLE = '' THEN EXCLUDED.TITLE ELSE TB_CHAT_THREAD_T.TITLE END
        """,
            (thread_id, member_id, title_snippet),
        )
        cur.execute(
            "INSERT INTO TB_CHAT_MESSAGE_T (THREAD_ID, MEMBER_ID, ROLE, MESSAGE, META_DATA) VALUES (%s, %s, %s, %s, %s)",
            (
                thread_id,
                member_id,
                role,
                message,
                json.dumps(meta, ensure_ascii=False) if meta else None,
            ),
        )
        conn.commit()
    finally:
        cur.close()
        release_recom_db_connection(conn)


def get_chat_history(thread_id: str) -> List[Dict[str, Any]]:
    conn = get_recom_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(
            "SELECT ROLE as role, MESSAGE as text, META_DATA as metadata FROM TB_CHAT_MESSAGE_T WHERE THREAD_ID = %s ORDER BY CREATED_DT ASC",
            (thread_id,),
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        cur.close()
        release_recom_db_connection(conn)


def get_user_chat_list(member_id: int) -> List[Dict[str, Any]]:
    if not member_id:
        return []
    conn = get_recom_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(
            "SELECT THREAD_ID as thread_id, TITLE as title, LAST_CHAT_DT as last_chat_dt FROM TB_CHAT_THREAD_T WHERE MEMBER_ID = %s AND IS_DELETED = 'N' ORDER BY LAST_CHAT_DT DESC LIMIT 30",
            (member_id,),
        )
        rows = cur.fetchall()
        results = []
        for r in rows:
            res = dict(r)
            if res["last_chat_dt"]:
                res["last_chat_dt"] = res["last_chat_dt"].isoformat()
            results.append(res)
        return results
    finally:
        cur.close()
        release_recom_db_connection(conn)


def lookup_note_by_string(keyword: str) -> List[str]:
    """사용자 입력 텍스트와 일치하거나 유사한 노트를 DB에서 찾습니다."""
    conn = get_db_connection()
    cur = conn.cursor()
    keyword_clean = keyword.strip().lower()
    found_notes = set()

    try:
        # 1. 완전 일치 확인
        cur.execute(
            "SELECT note FROM TB_PERFUME_NOTES_M WHERE LOWER(note) = %s LIMIT 1",
            (keyword_clean,),
        )
        row = cur.fetchone()
        if row:
            return [row[0]]

        # 2. 유사도 기반 검색 (Levenshtein distance)
        cur.execute("SELECT DISTINCT note FROM TB_PERFUME_NOTES_M")
        all_notes = [r[0] for r in cur.fetchall() if r[0]]

        for db_note in all_notes:
            if len(keyword_clean) < 3:
                if keyword_clean == db_note.lower():
                    found_notes.add(db_note)
                continue
            if distance(keyword_clean, db_note.lower()) <= 2:
                found_notes.add(db_note)

        return list(found_notes)
    except Exception as e:
        print(f"⚠️ Lookup String Note Error: {e}")
        return []
    finally:
        cur.close()
        release_db_connection(conn)


def lookup_note_by_vector(keyword: str) -> List[str]:
    """벡터 검색을 통해 유사한 노트 후보군을 찾습니다."""
    # 비동기가 아닌 동기식 도구에서 호출되므로 동기 방식으로 구현
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # get_embedding은 동기 함수 사용
        query_vector = get_embedding(keyword)
        if not query_vector:
            return []
        sql = "SELECT note FROM TB_NOTE_EMBEDDING_M ORDER BY embedding <=> %s::vector LIMIT 10"
        cur.execute(sql, (query_vector,))
        return [r[0] for r in cur.fetchall()]
    except Exception as e:
        print(f"⚠️ Lookup Vector Note Error: {e}")
        return []
    finally:
        cur.close()
        release_db_connection(conn)

# ==========================================
# 7. 채팅 시스템 (Connection Pool 적용)
# ==========================================

def save_chat_message(
    thread_id: str, member_id: int, role: str, message: str, meta: dict = None
):
    conn = get_recom_db_connection()
    try:
        cur = conn.cursor()
        # 제목으로 쓸 내용을 50자로 잡고 공백을 제거합니다.
        title_snippet = message[:50].strip()

        cur.execute(
            """
            INSERT INTO TB_CHAT_THREAD_T (THREAD_ID, MEMBER_ID, TITLE, LAST_CHAT_DT, IS_DELETED) 
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP, 'N')
            ON CONFLICT (THREAD_ID) DO UPDATE SET 
                MEMBER_ID = EXCLUDED.MEMBER_ID,
                LAST_CHAT_DT = CURRENT_TIMESTAMP, 
                IS_DELETED = 'N',
                -- [수정] 유저가 질문했을 때만, 그리고 제목이 없거나 '-'일 때만 업데이트
                TITLE = CASE 
                    WHEN %s = 'user' AND (TB_CHAT_THREAD_T.TITLE IS NULL OR TB_CHAT_THREAD_T.TITLE IN ('', '-'))
                    THEN EXCLUDED.TITLE 
                    ELSE TB_CHAT_THREAD_T.TITLE 
                END
        """,
            (thread_id, member_id, title_snippet, role), # role 파라미터 추가 완료
        )

        cur.execute(
            "INSERT INTO TB_CHAT_MESSAGE_T (THREAD_ID, MEMBER_ID, ROLE, MESSAGE, META_DATA) VALUES (%s, %s, %s, %s, %s)",
            (
                thread_id,
                member_id,
                role,
                message,
                json.dumps(meta, ensure_ascii=False) if meta else None,
            ),
        )

        print(f"📡 [DEBUG] 저장 성공 - 역할: {role}, 방ID: {thread_id}", flush=True)

        conn.commit()
    finally:
        cur.close()
        release_recom_db_connection(conn)


def get_chat_history(thread_id: str) -> List[Dict[str, Any]]:
    conn = get_recom_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(
            "SELECT ROLE as role, MESSAGE as text, META_DATA as metadata FROM TB_CHAT_MESSAGE_T WHERE THREAD_ID = %s ORDER BY CREATED_DT ASC",
            (thread_id,),
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        cur.close()
        release_recom_db_connection(conn)


def get_user_chat_list(member_id: int) -> List[Dict[str, Any]]:
    if not member_id:
        return []
    conn = get_recom_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(
            "SELECT THREAD_ID as thread_id, TITLE as title, LAST_CHAT_DT as last_chat_dt FROM TB_CHAT_THREAD_T WHERE MEMBER_ID = %s AND IS_DELETED = 'N' ORDER BY LAST_CHAT_DT DESC LIMIT 30",
            (member_id,),
        )
        rows = cur.fetchall()
        results = []
        for r in rows:
            res = dict(r)
            if res["last_chat_dt"]:
                res["last_chat_dt"] = res["last_chat_dt"].isoformat()
            results.append(res)
        return results
    finally:
        cur.close()
        release_recom_db_connection(conn)


def lookup_note_by_string(keyword: str) -> List[str]:
    """사용자 입력 텍스트와 일치하거나 유사한 노트를 DB에서 찾습니다."""
    conn = get_db_connection()
    cur = conn.cursor()
    keyword_clean = keyword.strip().lower()
    found_notes = set()

    try:
        # 1. 완전 일치 확인
        cur.execute(
            "SELECT note FROM TB_PERFUME_NOTES_M WHERE LOWER(note) = %s LIMIT 1",
            (keyword_clean,),
        )
        row = cur.fetchone()
        if row:
            return [row[0]]

        # 2. 유사도 기반 검색 (Levenshtein distance)
        cur.execute("SELECT DISTINCT note FROM TB_PERFUME_NOTES_M")
        all_notes = [r[0] for r in cur.fetchall() if r[0]]

        for db_note in all_notes:
            if len(keyword_clean) < 3:
                if keyword_clean == db_note.lower():
                    found_notes.add(db_note)
                continue
            if distance(keyword_clean, db_note.lower()) <= 2:
                found_notes.add(db_note)

        return list(found_notes)
    except Exception as e:
        print(f"⚠️ Lookup String Note Error: {e}")
        return []
    finally:
        cur.close()
        release_db_connection(conn)


def lookup_note_by_vector(keyword: str) -> List[str]:
    """벡터 검색을 통해 유사한 노트 후보군을 찾습니다."""
    # 비동기가 아닌 동기식 도구에서 호출되므로 동기 방식으로 구현
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # get_embedding은 동기 함수 사용
        query_vector = get_embedding(keyword)
        if not query_vector:
            return []
        sql = "SELECT note FROM TB_NOTE_EMBEDDING_M ORDER BY embedding <=> %s::vector LIMIT 10"
        cur.execute(sql, (query_vector,))
        return [r[0] for r in cur.fetchall()]
    except Exception as e:
        print(f"⚠️ Lookup Vector Note Error: {e}")
        return []
    finally:
        cur.close()
        release_db_connection(conn)