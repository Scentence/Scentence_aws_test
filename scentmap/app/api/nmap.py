from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from scentmap.app.schemas.nmap_schema import NMapResponse, FilterOptionsResponse
from scentmap.app.services.nmap_service import get_nmap_data, get_filter_options

"""
NMapRouter: 향수 맵(NMap) 시각화 및 필터 옵션 관련 API 엔드포인트
"""

router = APIRouter(prefix="/nmap", tags=["nmap"])

@router.get("/filter-options", response_model=FilterOptionsResponse)
def get_nmap_filters():
    """향수 맵 필터링을 위한 브랜드, 계절, 상황 등 옵션 목록 조회"""
    try:
        return get_filter_options()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.get("/perfumes", response_model=NMapResponse)
async def get_nmap_perfumes(
    min_similarity: float = Query(0.0, ge=0.0, le=1.0),
    top_accords: int = Query(5, ge=1, le=5),
    max_perfumes: Optional[int] = Query(None, ge=1),
    member_id: Optional[int] = Query(None, ge=1),
    debug: bool = False,
):
    """향수 네트워크 데이터 조회 (통합된 엔드포인트)"""
    try:
        return get_nmap_data(
            member_id=member_id,
            max_perfumes=max_perfumes,
            min_similarity=min_similarity,
            top_accords=top_accords,
            debug=debug
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.get("/result", response_model=NMapResponse)
async def get_nmap_result(
    member_id: Optional[int] = Query(None, description="회원 ID"),
    max_perfumes: Optional[int] = Query(100, description="최대 향수 개수"),
    min_similarity: float = Query(0.45, description="유사도 필터 기준"),
    top_accords: int = Query(2, description="표시할 상위 어코드 개수")
):
    """향수 맵 분석 결과 및 시각화 데이터 조회 (기존 호환용)"""
    try:
        return get_nmap_data(
            member_id=member_id,
            max_perfumes=max_perfumes,
            min_similarity=min_similarity,
            top_accords=top_accords
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
