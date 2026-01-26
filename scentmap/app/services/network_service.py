from collections import defaultdict
from typing import Dict, List, Optional, Tuple
import time
import logging

# 결과를 dict 형태로 받기 위해 RealDictCursor 사용
from psycopg2.extras import RealDictCursor
from scentmap.db import get_db_connection, get_recom_db_connection

logger = logging.getLogger(__name__)

# 전체 데이터 요청 시 유사도 엣지 상한 (perfume 당 상위 K개만)
# UI는 유사 엣지를 직접 표시하지 않고 Top 유사 향수만 사용하므로
# 이 값을 충분히 크게 잡으면 화면 결과는 동일하게 유지됩니다.
SIMILARITY_TOP_K = 30

# 필터 옵션 캐시 (짧은 TTL)
_filter_options_cache: Optional[Dict[str, List[str]]] = None
_filter_options_cached_at: Optional[float] = None
FILTER_OPTIONS_TTL_SECONDS = 300


# 필터 옵션 조회 (DB 기준 향수 카운트순)
def get_filter_options() -> Dict[str, List[str]]:
    global _filter_options_cache, _filter_options_cached_at
    now = time.time()
    if _filter_options_cache and _filter_options_cached_at:
        if now - _filter_options_cached_at < FILTER_OPTIONS_TTL_SECONDS:
            return _filter_options_cache

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT perfume_brand, COUNT(*) AS cnt
                FROM TB_PERFUME_BASIC_M
                WHERE perfume_brand IS NOT NULL
                GROUP BY perfume_brand
                ORDER BY cnt DESC, perfume_brand
                """
            )
            brands = [row["perfume_brand"] for row in cur.fetchall()]

            cur.execute(
                """
                SELECT season, COUNT(DISTINCT perfume_id) AS cnt
                FROM TB_PERFUME_SEASON_R
                WHERE season IS NOT NULL
                GROUP BY season
                ORDER BY cnt DESC, season
                """
            )
            seasons = [row["season"] for row in cur.fetchall()]

            cur.execute(
                """
                SELECT occasion, COUNT(DISTINCT perfume_id) AS cnt
                FROM TB_PERFUME_OCA_R
                WHERE occasion IS NOT NULL
                GROUP BY occasion
                ORDER BY cnt DESC, occasion
                """
            )
            occasions = [row["occasion"] for row in cur.fetchall()]

            cur.execute(
                """
                SELECT gender, COUNT(DISTINCT perfume_id) AS cnt
                FROM TB_PERFUME_GENDER_R
                WHERE gender IS NOT NULL
                GROUP BY gender
                ORDER BY cnt DESC, gender
                """
            )
            genders = [row["gender"] for row in cur.fetchall()]

            cur.execute(
                """
                SELECT accord, COUNT(DISTINCT perfume_id) AS cnt
                FROM TB_PERFUME_ACCORD_M
                WHERE accord IS NOT NULL
                GROUP BY accord
                ORDER BY cnt DESC, accord
                """
            )
            accords = [row["accord"] for row in cur.fetchall()]

    data = {
        "brands": brands,
        "seasons": seasons,
        "occasions": occasions,
        "genders": genders,
        "accords": accords,
    }
    _filter_options_cache = data
    _filter_options_cached_at = now
    return data


# 향수 기본 정보 가져오기
def _fetch_perfume_basic(max_perfumes: Optional[int]) -> List[Dict]:
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 향수 기본 정보 조회 쿼리 (필요한 필드만 선택)
            sql = """
                SELECT perfume_id, perfume_name, perfume_brand, img_link
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
def _fetch_perfume_accords(perfume_ids: Optional[List[int]]) -> List[Dict]:
    if perfume_ids is not None and not perfume_ids:
        return []

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 전체 조회 시에는 ANY 필터를 제거해 불필요한 배열 전달을 피함
            if perfume_ids is None:
                sql = """
                    SELECT perfume_id, accord, vote
                    FROM TB_PERFUME_ACCORD_M
                """
                cur.execute(sql)
            else:
                sql = """
                    SELECT perfume_id, accord, vote
                    FROM TB_PERFUME_ACCORD_M
                    WHERE perfume_id = ANY(%s)
                """
                cur.execute(sql, (perfume_ids,))
            return [dict(row) for row in cur.fetchall()]


# 향수별 계절/상황/성별 정보 가져오기
def _fetch_perfume_tags(perfume_ids: Optional[List[int]]) -> Dict[int, Dict[str, List[str]]]:
    if perfume_ids is not None and not perfume_ids:
        return {}

    tags_by_perfume: Dict[int, Dict[str, set]] = defaultdict(
        lambda: {"seasons": set(), "occasions": set(), "genders": set()}
    )

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if perfume_ids is None:
                cur.execute(
                    """
                    SELECT perfume_id, season
                    FROM TB_PERFUME_SEASON_R
                    """
                )
            else:
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

            if perfume_ids is None:
                cur.execute(
                    """
                    SELECT perfume_id, occasion
                    FROM TB_PERFUME_OCA_R
                    """
                )
            else:
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

            if perfume_ids is None:
                cur.execute(
                    """
                    SELECT perfume_id, gender
                    FROM TB_PERFUME_GENDER_R
                    """
                )
            else:
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

# 회원별 향수 상태 조회
def _fetch_member_statuses(member_id: Optional[int], perfume_ids: List[int]) -> Dict[int, str]:

    if not member_id or not perfume_ids:
        return {}

    # 회원 향수 상태는 recom_db에서 조회
    with get_recom_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT perfume_id, register_status
                FROM TB_MEMBER_MY_PERFUME_T
                WHERE member_id = %s
                  AND perfume_id = ANY(%s)
                """,
                (member_id, perfume_ids),
            )
            rows = cur.fetchall()

    return {
        int(row["perfume_id"]): row["register_status"]
        for row in rows
        if row.get("register_status")
    }


# 향수 기본 정보와 어코드(투표수) 데이터를 결합하여
# 향수별 어코드(비중)와 대표 어코드를 생성
def _build_profiles(
    perfume_rows: List[Dict],
    accord_rows: List[Dict],
    tags_by_perfume: Dict[int, Dict[str, List[str]]],
    member_status_by_perfume: Dict[int, str],
) -> Dict[int, Dict]:
    # 회원별 등록 상태(register_status) 향수 프로필에 포함

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
            "register_status": member_status_by_perfume.get(perfume_id),
        }
    return perfume_map


# 배치 작업으로 미리 계산되어 저장된 향수 간 유사도 테이블을 조회하여
# 실시간 계산 없이 edge 데이터 구성
def _fetch_similarity_edges_from_db(
    perfume_ids: Optional[List[int]],
    min_similarity: float,
    use_full_dataset: bool,
    perfume_count: Optional[int],
) -> List[Dict]:
    if perfume_ids is not None and not perfume_ids:
        return []

    total_perfumes = perfume_count if perfume_count is not None else (len(perfume_ids) if perfume_ids is not None else 0)
    logger.info(
        f"   → {total_perfumes:,}개 향수 간 유사도 엣지 조회 중 "
        f"(min_similarity={min_similarity}, full_dataset={use_full_dataset}, top_k={SIMILARITY_TOP_K if use_full_dataset else 'all'})..."
    )
    query_start = time.time()
    
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 선택된 향수 ID 목록 내에서만
            # 유사도(score)가 임계값 이상인 쌍을 조회
            if use_full_dataset:
                # 전체 데이터 조회 시 상위 K개 유사도만 반환 (전송량/응답시간 최적화)
                # 유사도 테이블은 A<B 방향으로만 저장되므로 양방향을 펼쳐서 Top-K 추출
                sql = """
                    WITH all_edges AS (
                        SELECT perfume_id_a AS src, perfume_id_b AS dst, score
                        FROM TB_PERFUME_SIMILARITY
                        WHERE score >= %s
                        UNION ALL
                        SELECT perfume_id_b AS src, perfume_id_a AS dst, score
                        FROM TB_PERFUME_SIMILARITY
                        WHERE score >= %s
                    ),
                    ranked AS (
                        SELECT src, dst, score,
                               ROW_NUMBER() OVER (PARTITION BY src ORDER BY score DESC) AS rn
                        FROM all_edges
                    )
                    SELECT src AS perfume_id_a, dst AS perfume_id_b, score
                    FROM ranked
                    WHERE rn <= %s
                """
                cur.execute(sql, (min_similarity, min_similarity, SIMILARITY_TOP_K))
            else:
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

    query_time = time.time() - query_start
    logger.info(f"   → {len(rows):,}개 유사도 엣지 조회 완료 ({query_time:.1f}초)")
    
    # [{perfume_id_a, perfume_id_b, score}, ...] 형태 반환
    return rows


# 네트워크 그래프 시각화용 데이터 구성
def _build_network(
    perfume_map: Dict[int, Dict],
    min_similarity: float,
    top_accords: int,
    use_full_dataset: bool,
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
                "register_status": perfume.get("register_status"),
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
    similarity_rows = _fetch_similarity_edges_from_db(
        None if use_full_dataset else perfume_ids_list,
        min_similarity,
        use_full_dataset=use_full_dataset,
        perfume_count=len(perfume_ids_list),
    )

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


def _build_network_data(
    min_similarity: float,
    top_accords: int,
    max_perfumes: Optional[int],
    member_id: Optional[int],
    debug: bool = False,
) -> Dict:
    """네트워크 데이터를 DB에서 구축"""
    started_at = time.time()
    
    logger.info("=" * 60)
    logger.info("🔄 네트워크 데이터 구축 시작")
    logger.info("=" * 60)

    # 1. 향수 기본 정보 조회
    logger.info("📊 [1/5] 향수 기본 정보 조회 중...")
    step_start = time.time()
    perfume_rows = _fetch_perfume_basic(max_perfumes)
    perfume_ids = [int(row["perfume_id"]) for row in perfume_rows]
    logger.info(f"   ✓ {len(perfume_ids):,}개 향수 조회 완료 ({time.time() - step_start:.1f}초)")
    
    is_full_dataset = max_perfumes is None

    # 2. 어코드 데이터 조회
    logger.info("📊 [2/5] 어코드 데이터 조회 중...")
    step_start = time.time()
    accord_rows = _fetch_perfume_accords(None if is_full_dataset else perfume_ids)
    logger.info(f"   ✓ {len(accord_rows):,}개 어코드 데이터 조회 완료 ({time.time() - step_start:.1f}초)")

    # 3. 태그 데이터 조회
    logger.info("📊 [3/5] 태그 데이터 조회 중...")
    step_start = time.time()
    tags_by_perfume = _fetch_perfume_tags(None if is_full_dataset else perfume_ids)
    member_status_by_perfume = _fetch_member_statuses(member_id, perfume_ids)
    logger.info(f"   ✓ 태그 데이터 조회 완료 ({time.time() - step_start:.1f}초)")
    
    # 4. 향수 프로필 구축
    logger.info("📊 [4/5] 향수 프로필 구축 중...")
    step_start = time.time()
    perfume_map = _build_profiles(
        perfume_rows,
        accord_rows,
        tags_by_perfume,
        member_status_by_perfume,
    )
    logger.info(f"   ✓ {len(perfume_map):,}개 프로필 구축 완료 ({time.time() - step_start:.1f}초)")

    # 5. 네트워크 그래프 구성
    logger.info("📊 [5/5] 네트워크 그래프 구성 중...")
    step_start = time.time()
    network = _build_network(perfume_map, min_similarity, top_accords, is_full_dataset, debug)
    logger.info(f"   ✓ 노드 {network['meta']['perfume_count']:,}개, 엣지 {network['meta']['edge_count']:,}개 생성 완료 ({time.time() - step_start:.1f}초)")

    # 빌드 메타 정보 추가
    total_time = time.time() - started_at
    network["meta"]["built_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    network["meta"]["build_seconds"] = round(total_time, 3)
    network["meta"]["max_perfumes"] = max_perfumes
    
    logger.info("=" * 60)
    logger.info(
        f"✅ 네트워크 데이터 구축 완료 - "
        f"향수: {network['meta']['perfume_count']:,}개, "
        f"어코드: {network['meta']['accord_count']:,}개, "
        f"엣지: {network['meta']['edge_count']:,}개 "
        f"(총 {total_time:.1f}초)"
    )
    logger.info("=" * 60)

    return network


def get_perfume_network(
    min_similarity: float = 0.45,
    top_accords: int = 2,
    max_perfumes: Optional[int] = None,
    member_id: Optional[int] = None,
    debug: bool = False,
) -> Dict:
    """향수 네트워크 데이터 조회 (DB 직접 조회, 캐시 미사용)"""
    return _build_network_data(min_similarity, top_accords, max_perfumes, member_id, debug)
