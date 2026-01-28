# 비즈니스 로직
from collections import defaultdict
from typing import Dict, List, Optional, Tuple
import time
import logging
from psycopg2.extras import RealDictCursor
from scentmap.db import get_db_connection, get_recom_db_connection
from scentmap.app.schemas.nmap_schema import NMapResponse, NMapNode, NMapEdge, NMapAnalysisSummary

logger = logging.getLogger(__name__)

SIMILARITY_TOP_K = 30

def _fetch_perfume_basic(max_perfumes: Optional[int]) -> List[Dict]:
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = """
                SELECT perfume_id, perfume_name, perfume_brand, img_link
                FROM TB_PERFUME_BASIC_M
                ORDER BY perfume_id
            """
            params = []
            if max_perfumes:
                sql += " LIMIT %s"
                params.append(max_perfumes)
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]

def _fetch_perfume_accords(perfume_ids: Optional[List[int]]) -> List[Dict]:
    if perfume_ids is not None and not perfume_ids:
        return []
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if perfume_ids is None:
                sql = "SELECT perfume_id, accord, vote FROM TB_PERFUME_ACCORD_M"
                cur.execute(sql)
            else:
                sql = "SELECT perfume_id, accord, vote FROM TB_PERFUME_ACCORD_M WHERE perfume_id = ANY(%s)"
                cur.execute(sql, (perfume_ids,))
            return [dict(row) for row in cur.fetchall()]

def _fetch_perfume_tags(perfume_ids: Optional[List[int]]) -> Dict[int, Dict[str, List[str]]]:
    if perfume_ids is not None and not perfume_ids:
        return {}
    tags_by_perfume = defaultdict(lambda: {"seasons": set(), "occasions": set(), "genders": set()})
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Seasons
            sql = "SELECT perfume_id, season FROM TB_PERFUME_SEASON_R"
            if perfume_ids: sql += " WHERE perfume_id = ANY(%s)"
            cur.execute(sql, (perfume_ids,) if perfume_ids else ())
            for row in cur.fetchall():
                if row["season"]: tags_by_perfume[int(row["perfume_id"])]["seasons"].add(row["season"])
            # Occasions
            sql = "SELECT perfume_id, occasion FROM TB_PERFUME_OCA_R"
            if perfume_ids: sql += " WHERE perfume_id = ANY(%s)"
            cur.execute(sql, (perfume_ids,) if perfume_ids else ())
            for row in cur.fetchall():
                if row["occasion"]: tags_by_perfume[int(row["perfume_id"])]["occasions"].add(row["occasion"])
            # Genders
            sql = "SELECT perfume_id, gender FROM TB_PERFUME_GENDER_R"
            if perfume_ids: sql += " WHERE perfume_id = ANY(%s)"
            cur.execute(sql, (perfume_ids,) if perfume_ids else ())
            for row in cur.fetchall():
                if row["gender"]: tags_by_perfume[int(row["perfume_id"])]["genders"].add(row["gender"])
    return {pid: {k: sorted(list(v)) for k, v in tags.items()} for pid, tags in tags_by_perfume.items()}

def _fetch_member_statuses(member_id: Optional[int], perfume_ids: List[int]) -> Dict[int, str]:
    if not member_id or not perfume_ids:
        return {}
    with get_recom_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT perfume_id, register_status FROM TB_MEMBER_MY_PERFUME_T WHERE member_id = %s AND perfume_id = ANY(%s)",
                (member_id, perfume_ids)
            )
            return {int(row["perfume_id"]): row["register_status"] for row in cur.fetchall() if row.get("register_status")}

def _fetch_similarity_edges(perfume_ids: Optional[List[int]], min_similarity: float, is_full: bool) -> List[Dict]:
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if is_full:
                sql = """
                    WITH all_edges AS (
                        SELECT perfume_id_a AS src, perfume_id_b AS dst, score FROM TB_PERFUME_SIMILARITY WHERE score >= %s
                        UNION ALL
                        SELECT perfume_id_b AS src, perfume_id_a AS dst, score FROM TB_PERFUME_SIMILARITY WHERE score >= %s
                    ), ranked AS (
                        SELECT src, dst, score, ROW_NUMBER() OVER (PARTITION BY src ORDER BY score DESC) AS rn FROM all_edges
                    )
                    SELECT src AS perfume_id_a, dst AS perfume_id_b, score FROM ranked WHERE rn <= %s
                """
                cur.execute(sql, (min_similarity, min_similarity, SIMILARITY_TOP_K))
            else:
                sql = "SELECT perfume_id_a, perfume_id_b, score FROM TB_PERFUME_SIMILARITY WHERE score >= %s AND perfume_id_a = ANY(%s) AND perfume_id_b = ANY(%s)"
                cur.execute(sql, (min_similarity, perfume_ids, perfume_ids))
            return [dict(row) for row in cur.fetchall()]

def _generate_analysis_summary(perfume_map: Dict[int, Dict]) -> NMapAnalysisSummary:
    """향수 맵 데이터를 기반으로 향기 카드용 요약 정보 생성"""
    # 상위 빈도 어코드를 추출하여 요약 생성
    accord_counts = defaultdict(int)
    mood_counts = defaultdict(int)
    
    for p in perfume_map.values():
        for acc in p["accords"][:3]:
            accord_counts[acc] += 1
        for mood in p["occasions"] + p["seasons"]:
            mood_counts[mood] += 1
            
    sorted_accords = sorted(accord_counts.keys(), key=lambda x: accord_counts[x], reverse=True)
    sorted_moods = sorted(mood_counts.keys(), key=lambda x: mood_counts[x], reverse=True)
    
    return NMapAnalysisSummary(
        top_notes=sorted_accords[:3],
        middle_notes=sorted_accords[3:6],
        base_notes=sorted_accords[6:9],
        mood_keywords=sorted_moods[:5],
        representative_color="#7C3AED",
        analysis_text="당신의 향기 분석 결과입니다."
    )

def get_nmap_data(
    member_id: Optional[int] = None,
    max_perfumes: Optional[int] = 100,
    min_similarity: float = 0.45,
    top_accords: int = 2
) -> NMapResponse:
    """향수 맵 데이터 생성"""
    start_time = time.time()
    
    # 1. 데이터 페칭
    perfume_rows = _fetch_perfume_basic(max_perfumes)
    perfume_ids = [int(row["perfume_id"]) for row in perfume_rows]
    accord_rows = _fetch_perfume_accords(perfume_ids)
    tag_data = _fetch_perfume_tags(perfume_ids)
    member_statuses = _fetch_member_statuses(member_id, perfume_ids)
    
    # 2. 프로필 구축
    accords_by_p = defaultdict(list)
    for r in accord_rows:
        accords_by_p[r["perfume_id"]].append((r["accord"], r["vote"] or 0))
        
    perfume_map = {}
    for r in perfume_rows:
        pid = int(r["perfume_id"])
        acc_list = accords_by_p[pid]
        total_v = sum(v for _, v in acc_list)
        acc_profile = {acc: float(v)/total_v for acc, v in acc_list} if total_v > 0 else {}
        
        tags = tag_data.get(pid, {"seasons": [], "occasions": [], "genders": []})
        
        perfume_map[pid] = {
            "perfume_id": pid,
            "perfume_name": r["perfume_name"],
            "brand": r["perfume_brand"],
            "image": r["img_link"],
            "accords": sorted(acc_profile.keys(), key=lambda x: acc_profile[x], reverse=True),
            "primary_accord": max(acc_profile.items(), key=lambda x: x[1])[0] if acc_profile else "Unknown",
            "seasons": tags["seasons"],
            "occasions": tags["occasions"],
            "genders": tags["genders"],
            "register_status": member_statuses.get(pid)
        }
    
    # 3. 노드 및 엣지 생성
    nodes = []
    edges = []
    used_accords = set()
    
    for p in perfume_map.values():
        nodes.append(NMapNode(
            id=str(p["perfume_id"]),
            type="perfume",
            label=p["perfume_name"],
            brand=p["brand"],
            image=p["image"],
            primary_accord=p["primary_accord"],
            accords=p["accords"],
            seasons=p["seasons"],
            occasions=p["occasions"],
            genders=p["genders"],
            register_status=p["register_status"]
        ))
        
        # 향수-어코드 엣지
        for acc in p["accords"][:top_accords]:
            used_accords.add(acc)
            edges.append(NMapEdge(
                **{"from": str(p["perfume_id"]), "to": f"accord_{acc}"},
                type="HAS_ACCORD",
                weight=1.0 # 가중치 로직은 필요시 보완
            ))
            
    for acc in used_accords:
        nodes.append(NMapNode(id=f"accord_{acc}", type="accord", label=acc))
        
    # 향수-향수 유사도 엣지
    sim_rows = _fetch_similarity_edges(perfume_ids, min_similarity, max_perfumes is None)
    for r in sim_rows:
        edges.append(NMapEdge(
            **{"from": str(r["perfume_id_a"]), "to": str(r["perfume_id_b"])},
            type="SIMILAR_TO",
            weight=r["score"]
        ))
        
    # 4. 요약 정보 생성
    summary = _generate_analysis_summary(perfume_map)
    
    build_time = time.time() - start_time
    meta = {
        "perfume_count": len(perfume_rows),
        "edge_count": len(edges),
        "build_time": round(build_time, 3),
        "built_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    return NMapResponse(nodes=nodes, edges=edges, summary=summary, meta=meta)
