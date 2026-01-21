from typing import Dict, List, Optional

from pydantic import BaseModel, Field
from pydantic import ConfigDict


class NetworkNode(BaseModel):
    id: str
    type: str
    label: str
    brand: Optional[str] = None
    image: Optional[str] = None
    primary_accord: Optional[str] = None
    accord_profile: Optional[Dict[str, float]] = None


class NetworkEdge(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    from_: str = Field(alias="from")
    to: str
    type: str
    weight: Optional[float] = None


class NetworkMeta(BaseModel):
    perfume_count: int
    accord_count: int
    edge_count: int
    accord_edges: int
    similarity_edges: int
    similarity_edges_high: int
    min_similarity: float
    top_accords: int
    candidate_pairs: int
    built_at: str
    build_seconds: float
    max_perfumes: Optional[int] = None
    debug_samples: Optional[Dict[str, List[Dict]]] = None


class NetworkResponse(BaseModel):
    nodes: List[NetworkNode]
    edges: List[NetworkEdge]
    meta: NetworkMeta
