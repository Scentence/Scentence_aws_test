import time
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from psycopg2.extras import RealDictCursor
from scentmap.db import get_db_connection

# 캐시는 기존과 동일하게 유지
CACHE = {
    "data": None,
    "built_at": None,
    "params": None,
}


# [변경 없음] 향수 기본 정보 가져오기 (Legacy 로직 유지)
def _fetch_perfume_basic(max_perfumes: Optional[int]) -> List[Dict]:
    # Context Manager 사용으로 안전성 강화
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


# [변경 없음] 어코드 정보 가져오기 (Legacy 로직 유지)
def _fetch_perfume_accords(perfume_ids: List[int]) -> List[Dict]:
    if not perfume_ids:
        return []
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = """
                SELECT perfume_id, accord, vote
                FROM TB_PERFUME_ACCORD_M
                WHERE perfume_id = ANY(%s)
            """
            cur.execute(sql, (perfume_ids,))
            return [dict(row) for row in cur.fetchall()]


# [변경 없음] 프로필 구축 (Legacy 로직 유지)
def _build_profiles(
    perfume_rows: List[Dict], accord_rows: List[Dict]
) -> Dict[int, Dict]:
    accords_by_perfume: Dict[int, List[Tuple[str, int]]] = defaultdict(list)
    for row in accord_rows:
        accords_by_perfume[row["perfume_id"]].append((row["accord"], row["vote"] or 0))

    perfume_map: Dict[int, Dict] = {}
    for row in perfume_rows:
        perfume_id = int(row["perfume_id"])
        accord_list = accords_by_perfume.get(perfume_id, [])
        total_vote = sum(v for _, v in accord_list)
        accord_profile: Dict[str, float] = {}
        if total_vote > 0:
            for accord, vote in accord_list:
                accord_profile[accord] = float(vote) / float(total_vote)

        primary_accord = None
        if accord_profile:
            primary_accord = max(accord_profile.items(), key=lambda x: x[1])[0]

        perfume_map[perfume_id] = {
            "perfume_id": perfume_id,
            "perfume_name": row["perfume_name"],
            "brand": row["perfume_brand"],
            "image": row["img_link"],
            "accord_profile": accord_profile,
            "primary_accord": primary_accord or "Unknown",
        }
    return perfume_map


# [핵심 변경] DB에서 미리 계산된 유사도를 가져오는 함수
def _fetch_similarity_edges_from_db(
    perfume_ids: List[int], min_similarity: float
) -> List[Dict]:
    if not perfume_ids:
        return []

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 선택된 향수들(perfume_ids) 끼리의 연결만 가져옵니다.
            # 배치로 미리 계산된 테이블(TB_PERFUME_SIMILARITY)을 조회하므로 매우 빠릅니다.
            sql = """
                SELECT perfume_id_a, perfume_id_b, score
                FROM TB_PERFUME_SIMILARITY
                WHERE score >= %s
                  AND perfume_id_a = ANY(%s)
                  AND perfume_id_b = ANY(%s)
            """
            cur.execute(sql, (min_similarity, perfume_ids, perfume_ids))
            rows = cur.fetchall()

    return rows


# [로직 유지 + 연산 교체] 네트워크 구축
def _build_network(
    perfume_map: Dict[int, Dict],
    min_similarity: float,
    top_accords: int,
    debug: bool,
) -> Dict:
    nodes: List[Dict] = []
    edges: List[Dict] = []
    accord_nodes: Dict[str, None] = {}

    # 1. 향수 노드 생성 (Legacy 로직과 100% 동일)
    for perfume in perfume_map.values():
        accord_profile = perfume["accord_profile"]
        sorted_accords = sorted(
            accord_profile.items(), key=lambda x: x[1], reverse=True
        )
        top_accord_list = [acc for acc, _ in sorted_accords[:top_accords]]
        perfume["top_accords"] = top_accord_list

        for acc in top_accord_list:
            accord_nodes[acc] = None

        # [Legacy 스키마 준수] type, label, brand 등 모든 필드 유지
        nodes.append(
            {
                "id": str(perfume["perfume_id"]),
                "type": "perfume",
                "label": perfume["perfume_name"][:30],
                "brand": perfume["brand"],
                "image": perfume["image"],
                "primary_accord": perfume["primary_accord"],
                "accord_profile": perfume["accord_profile"],
            }
        )

    # 2. 어코드 노드 생성 (Legacy 로직과 100% 동일)
    for acc in sorted(accord_nodes.keys()):
        nodes.append({"id": f"accord_{acc}", "type": "accord", "label": acc})

    # 3. 향수-어코드(HAS_ACCORD) 엣지 생성 (Legacy 로직과 100% 동일)
    accord_edge_count = 0
    for perfume in perfume_map.values():
        sorted_accords = sorted(
            perfume["accord_profile"].items(), key=lambda x: x[1], reverse=True
        )
        for accord, weight in sorted_accords[:top_accords]:
            edges.append(
                {
                    "from": str(perfume["perfume_id"]),
                    "to": f"accord_{accord}",
                    "type": "HAS_ACCORD",
                    "weight": weight,
                }
            )
            accord_edge_count += 1

    # 4. [수술 부위] 향수-향수(SIMILAR_TO) 엣지 생성
    # 기존: 이중 for문으로 직접 계산 (서버 다운 원인)
    # 변경: DB에서 정답지 조회 (부하 없음)

    perfume_ids_list = list(perfume_map.keys())
    similarity_rows = _fetch_similarity_edges_from_db(perfume_ids_list, min_similarity)

    similarity_edges = 0
    high_similarity_edges = 0

    for row in similarity_rows:
        sim = row["score"]
        edges.append(
            {
                "from": str(row["perfume_id_a"]),
                "to": str(row["perfume_id_b"]),
                "type": "SIMILAR_TO",
                "weight": sim,
            }
        )
        similarity_edges += 1
        if sim >= 0.8:
            high_similarity_edges += 1

    # 5. Meta 정보 채우기 (Legacy 스키마 요구사항 충족)
    meta = {
        "perfume_count": len(perfume_map),
        "accord_count": len(accord_nodes),
        "edge_count": len(edges),
        "accord_edges": accord_edge_count,
        "similarity_edges": similarity_edges,
        "similarity_edges_high": high_similarity_edges,
        "min_similarity": min_similarity,
        "top_accords": top_accords,
        "candidate_pairs": len(similarity_rows),  # 이제는 DB 조회 건수가 후보군임
    }

    if debug:
        meta["debug_samples"] = {
            "nodes": nodes[:3],
            "edges": edges[:3],
        }

    return {"nodes": nodes, "edges": edges, "meta": meta}


def get_perfume_network(
    min_similarity: float = 0.45,
    top_accords: int = 2,
    max_perfumes: Optional[int] = None,
    refresh: bool = False,
    debug: bool = False,
) -> Dict:
    # 파라미터가 같으면 캐시된 데이터 반환 (Legacy 로직 유지)
    params = (min_similarity, top_accords, max_perfumes)
    if (
        not refresh
        and CACHE["data"]
        and CACHE["params"] == params
        and CACHE["data"].get("nodes")
    ):
        return CACHE["data"]

    started_at = time.time()
    safe_max_perfumes = max_perfumes if max_perfumes is not None else 100
    # 1. 데이터 가져오기 (Legacy 로직)
    perfume_rows = _fetch_perfume_basic(safe_max_perfumes)
    perfume_ids = [int(row["perfume_id"]) for row in perfume_rows]
    accord_rows = _fetch_perfume_accords(perfume_ids)

    # 2. 프로필 빌드 (Legacy 로직)
    perfume_map = _build_profiles(perfume_rows, accord_rows)

    # 3. 네트워크 빌드 (DB 조회 방식 적용됨)
    network = _build_network(perfume_map, min_similarity, top_accords, debug)

    # 4. Meta 정보 마무리
    network["meta"]["built_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    network["meta"]["build_seconds"] = round(time.time() - started_at, 3)
    network["meta"]["max_perfumes"] = safe_max_perfumes

    # 캐시 갱신
    CACHE["data"] = network
    CACHE["built_at"] = network["meta"]["built_at"]
    CACHE["params"] = params

    return network
