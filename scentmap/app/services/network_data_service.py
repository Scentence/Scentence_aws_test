from collections import defaultdict
from typing import Dict, List, Optional, Tuple
import time

# 결과를 dict 형태로 받기 위해 RealDictCursor 사용
from psycopg2.extras import RealDictCursor
from scentmap.db import get_db_connection


# 향수 기본 정보 가져오기
def _fetch_perfume_basic(max_perfumes: Optional[int]) -> List[Dict]:
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 향수 기본 정보 조회 쿼리
            sql = """
                SELECT perfume_id, perfume_name, perfume_brand, release_year, perfumer, concentration, img_link
                FROM TB_PERFUME_BASIC_M
                ORDER BY perfume_id
            """
            params = []

            # 최대 조회 개수가 지정된 경우 LIMIT 적용
            if max_perfumes:
                sql += " LIMIT %s"
                params.append(max_perfumes)
            
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]


# 향수별 어코드 정보 가져오기
def _fetch_perfume_accords(perfume_ids: List[int]) -> List[Dict]:
    if not perfume_ids:
        return []
    
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 특정 향수 ID 목록에 해당하는 어코드와 투표 수 조회
            sql = """
                SELECT perfume_id, accord, vote
                FROM TB_PERFUME_ACCORD_M
                WHERE perfume_id = ANY(%s)
            """
            cur.execute(sql, (perfume_ids,))
            return [dict(row) for row in cur.fetchall()]


# 향수별 계절/상황/성별 정보 가져오기
def _fetch_perfume_tags(perfume_ids: List[int]) -> Dict[int, Dict[str, List[str]]]:
    if not perfume_ids:
        return {}

    tags_by_perfume: Dict[int, Dict[str, set]] = defaultdict(
        lambda: {"seasons": set(), "occasions": set(), "genders": set()}
    )

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT perfume_id, season
                FROM TB_PERFUME_SEASON_R
                WHERE perfume_id = ANY(%s)
                """,
                (perfume_ids,),
            )
            for row in cur.fetchall():
                season = row["season"]
                if season:
                    tags_by_perfume[int(row["perfume_id"])]["seasons"].add(season)

            cur.execute(
                """
                SELECT perfume_id, occasion
                FROM TB_PERFUME_OCA_R
                WHERE perfume_id = ANY(%s)
                """,
                (perfume_ids,),
            )
            for row in cur.fetchall():
                occasion = row["occasion"]
                if occasion:
                    tags_by_perfume[int(row["perfume_id"])]["occasions"].add(occasion)

            cur.execute(
                """
                SELECT perfume_id, gender
                FROM TB_PERFUME_GENDER_R
                WHERE perfume_id = ANY(%s)
                """,
                (perfume_ids,),
            )
            for row in cur.fetchall():
                gender = row["gender"]
                if gender:
                    tags_by_perfume[int(row["perfume_id"])]["genders"].add(gender)

    return {
        perfume_id: {
            "seasons": sorted(tags["seasons"]),
            "occasions": sorted(tags["occasions"]),
            "genders": sorted(tags["genders"]),
        }
        for perfume_id, tags in tags_by_perfume.items()
    }


# 향수 기본 정보와 어코드(투표수) 데이터를 결합하여
# 향수별 어코드(비중)와 대표 어코드를 생성
def _build_profiles(
    perfume_rows: List[Dict],
    accord_rows: List[Dict],
    tags_by_perfume: Dict[int, Dict[str, List[str]]],
) -> Dict[int, Dict]:

    accords_by_perfume: Dict[int, List[Tuple[str, int]]] = defaultdict(list)
    for row in accord_rows:
        # vote가 NULL인 경우 0으로 보정
        accords_by_perfume[row["perfume_id"]].append((row["accord"], row["vote"] or 0))

    perfume_map: Dict[int, Dict] = {}
    for row in perfume_rows:
        perfume_id = int(row["perfume_id"])

        # 해당 향수의 어코드 목록 조회
        accord_list = accords_by_perfume.get(perfume_id, [])
        
        # 전체 vote 합계
        total_vote = sum(v for _, v in accord_list)
        
        # 어코드별 비중
        accord_profile: Dict[str, float] = {}
        if total_vote > 0:
            for accord, vote in accord_list:
                accord_profile[accord] = float(vote) / float(total_vote)

        # 가장 비중이 높은 어코드를 대표 어코드로 선택
        primary_accord = None
        if accord_profile:
            primary_accord = max(accord_profile.items(), key=lambda x: x[1])[0]

        # 향수 단위 어코드 프로필 구성
        tags = tags_by_perfume.get(
            perfume_id, {"seasons": [], "occasions": [], "genders": []}
        )
        sorted_accords = sorted(
            accord_profile.keys(), key=lambda x: accord_profile[x], reverse=True
        )
        perfume_map[perfume_id] = {
            "perfume_id": perfume_id,
            "perfume_name": row["perfume_name"],
            "brand": row["perfume_brand"],
            "image": row["img_link"],
            "accord_profile": accord_profile,
            "primary_accord": primary_accord or "Unknown",
            "accords": sorted_accords,
            "seasons": tags["seasons"],
            "occasions": tags["occasions"],
            "genders": tags["genders"],
        }
    return perfume_map


# 배치 작업으로 미리 계산되어 저장된 향수 간 유사도 테이블을 조회하여
# 실시간 계산 없이 edge 데이터 구성
def _fetch_similarity_edges_from_db(perfume_ids: List[int], min_similarity: float) -> List[Dict]:
    if not perfume_ids:
        return []

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 선택된 향수 ID 목록 내에서만
            # 유사도(score)가 임계값 이상인 쌍을 조회
            sql = """
                SELECT perfume_id_a, perfume_id_b, score
                FROM TB_PERFUME_SIMILARITY
                WHERE score >= %s
                  AND perfume_id_a = ANY(%s)
                  AND perfume_id_b = ANY(%s)
            """
            # min_similarity: edge 필터 기준
            # perfume_ids: 그래프에 포함할 노드 집합 제한
            cur.execute(sql, (min_similarity, perfume_ids, perfume_ids))
            rows = cur.fetchall()

    # [{perfume_id_a, perfume_id_b, score}, ...] 형태 반환
    return rows


# 네트워크 그래프 시각화용 데이터 구성
def _build_network(
    perfume_map: Dict[int, Dict],
    min_similarity: float,
    top_accords: int,
    debug: bool,
) -> Dict:
    
    nodes: List[Dict] = []
    edges: List[Dict] = []
    accord_nodes: Dict[str, None] = {}

    # 1. 향수 노드 생성
    # 각 향수의 N개 어코드 노드 데이터 구성
    for perfume in perfume_map.values():
        accord_profile = perfume["accord_profile"]
        sorted_accords = sorted(accord_profile.items(), key=lambda x: x[1], reverse=True)
        top_accord_list = [acc for acc, _ in sorted_accords[:top_accords]]

        for acc in top_accord_list:
            accord_nodes[acc] = None

        nodes.append(
            {
                "id": str(perfume["perfume_id"]),
                "type": "perfume",
                "label": perfume["perfume_name"][:30],
                "brand": perfume["brand"],
                "image": perfume["image"],
                "primary_accord": perfume["primary_accord"],
                "accords": perfume["accords"],
                "seasons": perfume["seasons"],
                "occasions": perfume["occasions"],
                "genders": perfume["genders"],
            }
        )

    # 2. 어코드 노드 생성
    for acc in sorted(accord_nodes.keys()):
        nodes.append({"id": f"accord_{acc}", "type": "accord", "label": acc})

    # 3. 향수–어코드 관계 엣지 생성
    # N개 어코드만 HAS_ACCORD 엣지로 연결
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

    # 4. 향수–향수 유사도 SIMILAR_TO 엣지 생성
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

    # 5. 메타 정보 구성
    # 그래프 규모 및 필터 조건을 함께 반환
    meta = {
        "perfume_count": len(perfume_map),
        "accord_count": len(accord_nodes),
        "edge_count": len(edges),
        "accord_edges": accord_edge_count,
        "similarity_edges": similarity_edges,
        "similarity_edges_high": high_similarity_edges,
        "min_similarity": min_similarity,
        "top_accords": top_accords,
        "candidate_pairs": len(similarity_rows),
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
    debug: bool = False,
) -> Dict:
    started_at = time.time()

    # max_perfumes 미지정 시 안전한 기본 상한 적용
    safe_max_perfumes = max_perfumes if max_perfumes is not None else 100

    # 1. 향수 기본 정보 및 어코드 데이터 가져오기
    perfume_rows = _fetch_perfume_basic(safe_max_perfumes)
    perfume_ids = [int(row["perfume_id"]) for row in perfume_rows]
    accord_rows = _fetch_perfume_accords(perfume_ids)

    # 2. 향수별 어코드 프로필 생성
    tags_by_perfume = _fetch_perfume_tags(perfume_ids)
    perfume_map = _build_profiles(perfume_rows, accord_rows, tags_by_perfume)

    # 3. 노드, 엣지 기반 네트워크 그래프 구성
    network = _build_network(perfume_map, min_similarity, top_accords, debug)

    # 4. 빌드 메타 정보 추가
    network["meta"]["built_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    network["meta"]["build_seconds"] = round(time.time() - started_at, 3)
    network["meta"]["max_perfumes"] = safe_max_perfumes

    return network
