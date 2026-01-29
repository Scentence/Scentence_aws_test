import time
import logging
from collections import defaultdict
from typing import Dict, List, Optional, Tuple
from psycopg2.extras import RealDictCursor
from scentmap.db import get_db_connection, get_recom_db_connection
from scentmap.app.schemas.nmap_schema import NMapResponse, NMapNode, NMapEdge, NMapAnalysisSummary

"""
NMapService: 향수 맵(NMap) 데이터 구축 및 분석 서비스
"""

logger = logging.getLogger(__name__)

SIMILARITY_TOP_K = 30
FILTER_OPTIONS_TTL = 300
_filter_cache: Optional[Dict] = None
_filter_cache_time: float = 0

def get_filter_options() -> Dict[str, List[str]]:
    """향수 맵 필터링을 위한 옵션 목록 조회"""
    global _filter_cache, _filter_cache_time
    if _filter_cache and (time.time() - _filter_cache_time < FILTER_OPTIONS_TTL):
        return _filter_cache

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 브랜드
            cur.execute("""
                SELECT perfume_brand, COUNT(*) as cnt 
                FROM TB_PERFUME_BASIC_M 
                WHERE perfume_brand IS NOT NULL 
                GROUP BY perfume_brand 
                ORDER BY cnt DESC, perfume_brand
            """)
            brands = [r["perfume_brand"] for r in cur.fetchall()]
            
            # 계절
            cur.execute("""
                SELECT season, COUNT(DISTINCT perfume_id) as cnt 
                FROM TB_PERFUME_SEASON_R 
                WHERE season IS NOT NULL 
                GROUP BY season 
                ORDER BY cnt DESC, season
            """)
            seasons = [r["season"] for r in cur.fetchall()]
            
            # 상황
            cur.execute("""
                SELECT occasion, COUNT(DISTINCT perfume_id) as cnt 
                FROM TB_PERFUME_OCA_R 
                WHERE occasion IS NOT NULL 
                GROUP BY occasion 
                ORDER BY cnt DESC, occasion
            """)
            occasions = [r["occasion"] for r in cur.fetchall()]
            
            # 성별
            cur.execute("""
                SELECT gender, COUNT(DISTINCT perfume_id) as cnt 
                FROM TB_PERFUME_GENDER_R 
                WHERE gender IS NOT NULL 
                GROUP BY gender 
                ORDER BY cnt DESC, gender
            """)
            genders = [r["gender"] for r in cur.fetchall()]
            
            # 어코드
            cur.execute("""
                SELECT accord, COUNT(DISTINCT perfume_id) as cnt 
                FROM TB_PERFUME_ACCORD_M 
                WHERE accord IS NOT NULL 
                GROUP BY accord 
                ORDER BY cnt DESC, accord
            """)
            accords = [r["accord"] for r in cur.fetchall()]

    _filter_cache = {
        "brands": brands, 
        "seasons": seasons, 
        "occasions": occasions, 
        "genders": genders, 
        "accords": accords
    }
    _filter_cache_time = time.time()
    return _filter_cache

def _fetch_perfume_basic(max_perfumes: Optional[int]) -> List[Dict]:
    """향수 기본 정보 DB 조회"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = "SELECT perfume_id, perfume_name, perfume_brand, img_link FROM TB_PERFUME_BASIC_M ORDER BY perfume_id"
            params = []
            if max_perfumes:
                sql += " LIMIT %s"
                params.append(max_perfumes)
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]

def _fetch_perfume_accords(perfume_ids: Optional[List[int]]) -> List[Dict]:
    """향수별 어코드 정보 DB 조회"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if perfume_ids is None:
                sql = "SELECT perfume_id, accord, vote FROM TB_PERFUME_ACCORD_M"
                cur.execute(sql)
            else:
                sql = "SELECT perfume_id, accord, vote FROM TB_PERFUME_ACCORD_M WHERE perfume_id = ANY(%s)"
                cur.execute(sql, (perfume_ids,))
            return [dict(row) for row in cur.fetchall()]

def _fetch_perfume_tags(perfume_ids: Optional[List[int]]) -> Dict[int, Dict]:
    """향수별 태그(계절, 상황, 성별) 정보 DB 조회"""
    tags = defaultdict(lambda: {"seasons": set(), "occasions": set(), "genders": set()})
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Seasons
            sql = "SELECT perfume_id, season FROM TB_PERFUME_SEASON_R"
            if perfume_ids:
                sql += " WHERE perfume_id = ANY(%s)"
                cur.execute(sql, (perfume_ids,))
            else:
                cur.execute(sql)
            for r in cur.fetchall(): tags[int(r["perfume_id"])]["seasons"].add(r["season"])
            
            # Occasions
            sql = "SELECT perfume_id, occasion FROM TB_PERFUME_OCA_R"
            if perfume_ids:
                sql += " WHERE perfume_id = ANY(%s)"
                cur.execute(sql, (perfume_ids,))
            else:
                cur.execute(sql)
            for r in cur.fetchall(): tags[int(r["perfume_id"])]["occasions"].add(r["occasion"])
            
            # Genders
            sql = "SELECT perfume_id, gender FROM TB_PERFUME_GENDER_R"
            if perfume_ids:
                sql += " WHERE perfume_id = ANY(%s)"
                cur.execute(sql, (perfume_ids,))
            else:
                cur.execute(sql)
            for r in cur.fetchall(): tags[int(r["perfume_id"])]["genders"].add(r["gender"])
            
    return {pid: {k: sorted(list(v)) for k, v in t.items()} for pid, t in tags.items()}

def _fetch_member_statuses(member_id: Optional[int], perfume_ids: List[int]) -> Dict[int, str]:
    """회원별 향수 등록 상태 조회"""
    if not member_id or not perfume_ids:
        return {}
    with get_recom_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT perfume_id, register_status FROM TB_MEMBER_MY_PERFUME_T WHERE member_id = %s AND perfume_id = ANY(%s)",
                (member_id, perfume_ids),
            )
            return {int(row["perfume_id"]): row["register_status"] for row in cur.fetchall() if row.get("register_status")}

def _fetch_similarity_edges(perfume_ids: Optional[List[int]], min_sim: float, is_full: bool) -> List[Dict]:
    """향수 간 유사도 엣지 DB 조회"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if is_full:
                sql = """
                    WITH all_edges AS (
                        SELECT perfume_id_a as src, perfume_id_b as dst, score FROM TB_PERFUME_SIMILARITY WHERE score >= %s
                        UNION ALL
                        SELECT perfume_id_b as src, perfume_id_a as dst, score FROM TB_PERFUME_SIMILARITY WHERE score >= %s
                    ), ranked AS (
                        SELECT src, dst, score, ROW_NUMBER() OVER (PARTITION BY src ORDER BY score DESC) as rn FROM all_edges
                    )
                    SELECT src as perfume_id_a, dst as perfume_id_b, score FROM ranked WHERE rn <= %s
                """
                cur.execute(sql, (min_sim, min_sim, SIMILARITY_TOP_K))
            else:
                sql = "SELECT perfume_id_a, perfume_id_b, score FROM TB_PERFUME_SIMILARITY WHERE score >= %s AND perfume_id_a = ANY(%s) AND perfume_id_b = ANY(%s)"
                cur.execute(sql, (min_sim, perfume_ids, perfume_ids))
            return [dict(row) for row in cur.fetchall()]

def get_nmap_data(
    member_id: Optional[int] = None, 
    max_perfumes: Optional[int] = None, 
    min_similarity: float = 0.0, 
    top_accords: int = 5,
    debug: bool = False
) -> NMapResponse:
    """향수 맵 전체 데이터 및 분석 요약 정보 조회"""
    start = time.time()
    
    # 1. 데이터 조회
    p_rows = _fetch_perfume_basic(max_perfumes)
    p_ids = [int(r["perfume_id"]) for r in p_rows]
    is_full = max_perfumes is None
    
    a_rows = _fetch_perfume_accords(None if is_full else p_ids)
    t_data = _fetch_perfume_tags(None if is_full else p_ids)
    m_statuses = _fetch_member_statuses(member_id, p_ids)
    
    # 2. 프로필 및 노드 구축
    acc_by_p = defaultdict(list)
    for r in a_rows: 
        acc_by_p[r["perfume_id"]].append((r["accord"], r["vote"] or 0))
    
    nodes, edges, used_accords = [], [], set()
    p_map = {}
    
    for r in p_rows:
        pid = int(r["perfume_id"])
        acc_list = acc_by_p[pid]
        total_v = sum(v for _, v in acc_list)
        acc_prof = {a: float(v)/total_v for a, v in acc_list} if total_v > 0 else {}
        tags = t_data.get(pid, {"seasons": [], "occasions": [], "genders": []})
        
        sorted_accords = sorted(acc_prof.keys(), key=lambda x: acc_prof[x], reverse=True)
        primary_accord = sorted_accords[0] if sorted_accords else "Unknown"
        
        p_info = {
            "id": str(pid), 
            "type": "perfume", 
            "label": r["perfume_name"], 
            "brand": r["perfume_brand"], 
            "image": r["img_link"],
            "primary_accord": primary_accord,
            "accords": sorted_accords,
            "seasons": tags["seasons"], 
            "occasions": tags["occasions"], 
            "genders": tags["genders"],
            "register_status": m_statuses.get(pid)
        }
        p_map[pid] = p_info
        nodes.append(NMapNode(**p_info))
        
        # 향수-어코드 엣지
        for acc in sorted_accords[:top_accords]:
            used_accords.add(acc)
            edges.append(NMapEdge(**{
                "from": str(pid), 
                "to": f"accord_{acc}", 
                "type": "HAS_ACCORD", 
                "weight": acc_prof.get(acc, 0.0)
            }))
            
    # 어코드 노드 추가
    for acc in sorted(list(used_accords)):
        nodes.append(NMapNode(id=f"accord_{acc}", type="accord", label=acc))
        
    # 3. 유사도 엣지 조회 및 추가
    sim_rows = _fetch_similarity_edges(p_ids, min_similarity, is_full)
    for r in sim_rows:
        edges.append(NMapEdge(**{
            "from": str(r["perfume_id_a"]), 
            "to": str(r["perfume_id_b"]), 
            "type": "SIMILAR_TO", 
            "weight": r["score"]
        }))
        
    # 4. 분석 요약 생성
    acc_cnt, mood_cnt = defaultdict(int), defaultdict(int)
    for p in p_map.values():
        for a in p["accords"][:3]: acc_cnt[a] += 1
        for m in p["occasions"] + p["seasons"]: mood_cnt[m] += 1
    
    sorted_accs = sorted(acc_cnt.keys(), key=lambda x: acc_cnt[x], reverse=True)
    summary = NMapAnalysisSummary(
        top_notes=sorted_accs[:3],
        middle_notes=sorted_accs[3:6],
        base_notes=sorted_accs[6:9],
        mood_keywords=sorted(mood_cnt.keys(), key=lambda x: mood_cnt[x], reverse=True)[:5],
        analysis_text="탐색하신 향기들의 주요 특징입니다."
    )
    
    meta = {
        "build_time": round(time.time()-start, 3),
        "perfume_count": len(p_map),
        "edge_count": len(edges),
        "min_similarity": min_similarity,
        "top_accords": top_accords
    }
    
    return NMapResponse(nodes=nodes, edges=edges, summary=summary, meta=meta)
