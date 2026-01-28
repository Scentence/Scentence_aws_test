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
            cur.execute("SELECT perfume_brand, COUNT(*) as cnt FROM TB_PERFUME_BASIC_M GROUP BY perfume_brand ORDER BY cnt DESC")
            brands = [r["perfume_brand"] for r in cur.fetchall() if r["perfume_brand"]]
            # 계절
            cur.execute("SELECT season, COUNT(*) as cnt FROM TB_PERFUME_SEASON_R GROUP BY season ORDER BY cnt DESC")
            seasons = [r["season"] for r in cur.fetchall() if r["season"]]
            # 상황
            cur.execute("SELECT occasion, COUNT(*) as cnt FROM TB_PERFUME_OCA_R GROUP BY occasion ORDER BY cnt DESC")
            occasions = [r["occasion"] for r in cur.fetchall() if r["occasion"]]
            # 성별
            cur.execute("SELECT gender, COUNT(*) as cnt FROM TB_PERFUME_GENDER_R GROUP BY gender ORDER BY cnt DESC")
            genders = [r["gender"] for r in cur.fetchall() if r["gender"]]
            # 어코드
            cur.execute("SELECT accord, COUNT(*) as cnt FROM TB_PERFUME_ACCORD_M GROUP BY accord ORDER BY cnt DESC")
            accords = [r["accord"] for r in cur.fetchall() if r["accord"]]

    _filter_cache = {"brands": brands, "seasons": seasons, "occasions": occasions, "genders": genders, "accords": accords}
    _filter_cache_time = time.time()
    return _filter_cache

def _fetch_perfume_basic(max_perfumes: Optional[int]) -> List[Dict]:
    """향수 기본 정보 DB 조회"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = "SELECT perfume_id, perfume_name, perfume_brand, img_link FROM TB_PERFUME_BASIC_M ORDER BY perfume_id"
            if max_perfumes:
                sql += f" LIMIT {max_perfumes}"
            cur.execute(sql)
            return [dict(row) for row in cur.fetchall()]

def _fetch_perfume_accords(perfume_ids: Optional[List[int]]) -> List[Dict]:
    """향수별 어코드 정보 DB 조회"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = "SELECT perfume_id, accord, vote FROM TB_PERFUME_ACCORD_M"
            if perfume_ids:
                sql += " WHERE perfume_id = ANY(%s)"
                cur.execute(sql, (perfume_ids,))
            else:
                cur.execute(sql)
            return [dict(row) for row in cur.fetchall()]

def _fetch_perfume_tags(perfume_ids: Optional[List[int]]) -> Dict[int, Dict]:
    """향수별 태그(계절, 상황, 성별) 정보 DB 조회"""
    tags = defaultdict(lambda: {"seasons": set(), "occasions": set(), "genders": set()})
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Seasons
            sql = "SELECT perfume_id, season FROM TB_PERFUME_SEASON_R"
            if perfume_ids: sql += " WHERE perfume_id = ANY(%s)"
            cur.execute(sql, (perfume_ids,) if perfume_ids else ())
            for r in cur.fetchall(): tags[int(r["perfume_id"])]["seasons"].add(r["season"])
            # Occasions
            sql = "SELECT perfume_id, occasion FROM TB_PERFUME_OCA_R"
            if perfume_ids: sql += " WHERE perfume_id = ANY(%s)"
            cur.execute(sql, (perfume_ids,) if perfume_ids else ())
            for r in cur.fetchall(): tags[int(r["perfume_id"])]["occasions"].add(r["occasion"])
            # Genders
            sql = "SELECT perfume_id, gender FROM TB_PERFUME_GENDER_R"
            if perfume_ids: sql += " WHERE perfume_id = ANY(%s)"
            cur.execute(sql, (perfume_ids,) if perfume_ids else ())
            for r in cur.fetchall(): tags[int(r["perfume_id"])]["genders"].add(r["gender"])
    return {pid: {k: sorted(list(v)) for k, v in t.items()} for pid, t in tags.items()}

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

def get_nmap_data(member_id: Optional[int] = None, max_perfumes: Optional[int] = 100, min_similarity: float = 0.45, top_accords: int = 2) -> NMapResponse:
    """향수 맵 전체 데이터 및 분석 요약 정보 조회"""
    start = time.time()
    p_rows = _fetch_perfume_basic(max_perfumes)
    p_ids = [int(r["perfume_id"]) for r in p_rows]
    a_rows = _fetch_perfume_accords(p_ids)
    t_data = _fetch_perfume_tags(p_ids)
    
    # 프로필 구축
    acc_by_p = defaultdict(list)
    for r in a_rows: acc_by_p[r["perfume_id"]].append((r["accord"], r["vote"] or 0))
    
    nodes, edges, used_accords = [], [], set()
    p_map = {}
    for r in p_rows:
        pid = int(r["perfume_id"])
        acc_list = acc_by_p[pid]
        total_v = sum(v for _, v in acc_list)
        acc_prof = {a: float(v)/total_v for a, v in acc_list} if total_v > 0 else {}
        tags = t_data.get(pid, {"seasons": [], "occasions": [], "genders": []})
        
        p_info = {
            "id": str(pid), "type": "perfume", "label": r["perfume_name"], "brand": r["perfume_brand"], "image": r["img_link"],
            "primary_accord": max(acc_prof.items(), key=lambda x: x[1])[0] if acc_prof else "Unknown",
            "accords": sorted(acc_prof.keys(), key=lambda x: acc_prof[x], reverse=True),
            "seasons": tags["seasons"], "occasions": tags["occasions"], "genders": tags["genders"]
        }
        p_map[pid] = p_info
        nodes.append(NMapNode(**p_info))
        
        for acc in p_info["accords"][:top_accords]:
            used_accords.add(acc)
            edges.append(NMapEdge(**{"from": str(pid), "to": f"accord_{acc}", "type": "HAS_ACCORD", "weight": 1.0}))
            
    for acc in used_accords:
        nodes.append(NMapNode(id=f"accord_{acc}", type="accord", label=acc))
        
    sim_rows = _fetch_similarity_edges(p_ids, min_similarity, max_perfumes is None)
    for r in sim_rows:
        edges.append(NMapEdge(**{"from": str(r["perfume_id_a"]), "to": str(r["perfume_id_b"]), "type": "SIMILAR_TO", "weight": r["score"]}))
        
    # 요약 생성
    acc_cnt, mood_cnt = defaultdict(int), defaultdict(int)
    for p in p_map.values():
        for a in p["accords"][:3]: acc_cnt[a] += 1
        for m in p["occasions"] + p["seasons"]: mood_cnt[m] += 1
    
    summary = NMapAnalysisSummary(
        top_notes=sorted(acc_cnt.keys(), key=lambda x: acc_cnt[x], reverse=True)[:3],
        middle_notes=sorted(acc_cnt.keys(), key=lambda x: acc_cnt[x], reverse=True)[3:6],
        base_notes=sorted(acc_cnt.keys(), key=lambda x: acc_cnt[x], reverse=True)[6:9],
        mood_keywords=sorted(mood_cnt.keys(), key=lambda x: mood_cnt[x], reverse=True)[:5],
        analysis_text="탐색하신 향기들의 주요 특징입니다."
    )
    
    return NMapResponse(nodes=nodes, edges=edges, summary=summary, meta={"build_time": round(time.time()-start, 3)})
