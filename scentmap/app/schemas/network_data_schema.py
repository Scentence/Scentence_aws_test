from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class NetworkNode(BaseModel):
    id: str
    type: str  # 필수
    label: str  # 필수
    brand: Optional[str] = None
    group: Optional[str] = None  # [추가] 브랜드별 색상 구분에 사용
    image: Optional[str] = None
    primary_accord: Optional[str] = None
    top_accords: Optional[List[str]] = None  # [추가] 상위 어코드 리스트
    accord_profile: Optional[Dict[str, float]] = None


class NetworkEdge(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    from_: str = Field(alias="from")
    to: str
    type: str
    weight: Optional[float] = None  # 기존 필드 (호환성 유지)
    value: Optional[float] = None  # [추가] 선 굵기 (Vis.js용)
    title: Optional[str] = None  # [추가] 마우스 오버 툴팁


class NetworkMeta(BaseModel):
    # [수정] 예전에는 필수였지만, 이제는 계산하지 않는 값들을 Optional로 변경
    perfume_count: Optional[int] = None
    accord_count: Optional[int] = None
    edge_count: Optional[int] = None
    accord_edges: Optional[int] = None
    similarity_edges: Optional[int] = None
    similarity_edges_high: Optional[int] = None
    min_similarity: Optional[float] = None
    top_accords: Optional[int] = None
    candidate_pairs: Optional[int] = None
    built_at: Optional[str] = None
    build_seconds: Optional[float] = None
    max_perfumes: Optional[int] = None
    debug_samples: Optional[Dict[str, List[Dict]]] = None

    # [추가] 새로운 로직에서 사용하는 필드
    count: Optional[int] = None
    process_time: Optional[float] = None
    msg: Optional[str] = None


class NetworkResponse(BaseModel):
    nodes: List[NetworkNode]
    edges: List[NetworkEdge]
    meta: NetworkMeta
