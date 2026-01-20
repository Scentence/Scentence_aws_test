import math
import time
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from psycopg2.extras import RealDictCursor

from scentmap.db import get_db_connection


CACHE = {
    "data": None,
    "built_at": None,
    "params": None,
}


def calculate_similarity(profile1: Dict[str, float], profile2: Dict[str, float]) -> float:
    keys = set(profile1.keys()) | set(profile2.keys())
    if not keys:
        return 0.0

    vec1 = [profile1.get(k, 0.0) for k in keys]
    vec2 = [profile2.get(k, 0.0) for k in keys]

    dot = sum(a * b for a, b in zip(vec1, vec2))
    mag1 = math.sqrt(sum(a * a for a in vec1))
    mag2 = math.sqrt(sum(b * b for b in vec2))

    if mag1 * mag2 == 0:
        return 0.0

    return dot / (mag1 * mag2)


def _fetch_perfume_basic(max_perfumes: Optional[int]) -> List[Dict]:
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
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
    finally:
        cur.close()
        conn.close()


def _fetch_perfume_accords(perfume_ids: List[int]) -> List[Dict]:
    if not perfume_ids:
        return []
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        sql = """
            SELECT perfume_id, accord, vote
            FROM TB_PERFUME_ACCORD_M
            WHERE perfume_id = ANY(%s)
        """
        cur.execute(sql, (perfume_ids,))
        return [dict(row) for row in cur.fetchall()]
    finally:
        cur.close()
        conn.close()


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


def _build_network(
    perfume_map: Dict[int, Dict],
    min_similarity: float,
    top_accords: int,
    debug: bool,
) -> Dict:
    nodes: List[Dict] = []
    edges: List[Dict] = []
    accord_nodes: Dict[str, None] = {}
    accord_to_perfumes: Dict[str, List[int]] = defaultdict(list)

    for perfume in perfume_map.values():
        accord_profile = perfume["accord_profile"]
        sorted_accords = sorted(
            accord_profile.items(), key=lambda x: x[1], reverse=True
        )
        top_accord_list = [acc for acc, _ in sorted_accords[:top_accords]]
        perfume["top_accords"] = top_accord_list

        for acc in top_accord_list:
            accord_nodes[acc] = None
            accord_to_perfumes[acc].append(perfume["perfume_id"])

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

    for acc in sorted(accord_nodes.keys()):
        nodes.append({"id": f"accord_{acc}", "type": "accord", "label": acc})

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

    candidate_pairs = set()
    for perfume_ids in accord_to_perfumes.values():
        size = len(perfume_ids)
        for i in range(size):
            for j in range(i + 1, size):
                a = perfume_ids[i]
                b = perfume_ids[j]
                if a != b:
                    candidate_pairs.add((min(a, b), max(a, b)))

    similarity_edges = 0
    high_similarity_edges = 0
    for pid1, pid2 in candidate_pairs:
        p1 = perfume_map[pid1]
        p2 = perfume_map[pid2]
        sim = calculate_similarity(p1["accord_profile"], p2["accord_profile"])
        if sim >= min_similarity:
            edges.append(
                {
                    "from": str(pid1),
                    "to": str(pid2),
                    "type": "SIMILAR_TO",
                    "weight": sim,
                }
            )
            similarity_edges += 1
            if sim >= 0.8:
                high_similarity_edges += 1

    meta = {
        "perfume_count": len(perfume_map),
        "accord_count": len(accord_nodes),
        "edge_count": len(edges),
        "accord_edges": accord_edge_count,
        "similarity_edges": similarity_edges,
        "similarity_edges_high": high_similarity_edges,
        "min_similarity": min_similarity,
        "top_accords": top_accords,
        "candidate_pairs": len(candidate_pairs),
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
    params = (min_similarity, top_accords, max_perfumes)
    if (
        not refresh
        and CACHE["data"]
        and CACHE["params"] == params
        and CACHE["data"].get("nodes")
    ):
        return CACHE["data"]

    started_at = time.time()
    perfume_rows = _fetch_perfume_basic(max_perfumes)
    perfume_ids = [int(row["perfume_id"]) for row in perfume_rows]
    accord_rows = _fetch_perfume_accords(perfume_ids)
    perfume_map = _build_profiles(perfume_rows, accord_rows)
    network = _build_network(perfume_map, min_similarity, top_accords, debug)
    network["meta"]["built_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    network["meta"]["build_seconds"] = round(time.time() - started_at, 3)
    network["meta"]["max_perfumes"] = max_perfumes

    CACHE["data"] = network
    CACHE["built_at"] = network["meta"]["built_at"]
    CACHE["params"] = params

    return network
