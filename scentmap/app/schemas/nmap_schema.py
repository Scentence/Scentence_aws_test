from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict

# 1. 기본 요소 스키마
class NMapNode(BaseModel):
    """향수 맵의 노드 (향수 또는 어코드)"""
    id: str
    type: str  # "perfume" | "accord"
    label: str
    brand: Optional[str] = None
    image: Optional[str] = None
    primary_accord: Optional[str] = None
    accords: Optional[List[str]] = None
    seasons: Optional[List[str]] = None
    occasions: Optional[List[str]] = None
    genders: Optional[List[str]] = None
    register_status: Optional[str] = None  # 회원의 경우 'want', 'have' 등

class NMapEdge(BaseModel):
    """노드 간의 연결 (유사도 또는 포함 관계)"""
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    from_node: str = Field(alias="from")
    to_node: str = Field(alias="to")
    type: str  # "HAS_ACCORD" | "SIMILAR_TO"
    weight: float  # 유사도 점수 또는 어코드 비중

# 2. 분석 결과 요약 (향기 카드로 보낼 핵심 데이터)
class NMapAnalysisSummary(BaseModel):
    """향기 카드로 전달될 분석 요약 정보"""
    top_notes: List[str]
    middle_notes: List[str]
    base_notes: List[str]
    mood_keywords: List[str]
    representative_color: Optional[str] = None
    analysis_text: Optional[str] = None

# 3. 전체 응답 스키마
class NMapResponse(BaseModel):
    """향수 맵 최종 응답 구조"""
    nodes: List[NMapNode]
    edges: List[NMapEdge]
    summary: NMapAnalysisSummary  # 향기 카드 생성을 위한 요약 데이터 추가
    meta: Dict[str, Optional[float | int | str]]