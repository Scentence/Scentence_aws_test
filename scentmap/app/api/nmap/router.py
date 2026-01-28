from fastapi import APIRouter, Depends, Query
from typing import Optional
from scentmap.app.schemas.nmap_schema import NMapResponse
from scentmap.app.services.nmap_service import get_nmap_data

router = APIRouter(prefix="/nmap", tags=["nmap"])

@router.get("/result", response_model=NMapResponse)
async def get_nmap_result(
    member_id: Optional[int] = Query(None, description="회원 ID (로그인한 경우)"),
    max_perfumes: Optional[int] = Query(100, description="조회할 최대 향수 개수"),
    min_similarity: float = Query(0.45, description="유사도 필터 기준"),
    top_accords: int = Query(2, description="향수당 표시할 상위 어코드 개수")
):
    """
    향수 맵 분석 결과 및 시각화 데이터를 조회합니다.
    조회된 데이터에는 향기 카드 생성을 위한 요약 정보(summary)가 포함됩니다.
    """
    return get_nmap_data(
        member_id=member_id,
        max_perfumes=max_perfumes,
        min_similarity=min_similarity,
        top_accords=top_accords
    )
