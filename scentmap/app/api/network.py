from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import ORJSONResponse
from typing import List, Optional

from scentmap.app.services.network_service import get_filter_options, get_perfume_network


router = APIRouter(prefix="/network", tags=["network"])


@router.get("/filter-options", response_class=ORJSONResponse)
def filter_options():
    """
    필터 옵션 조회 (DB 기준 향수 카운트순 정렬)
    """
    try:
        data = get_filter_options()
        return ORJSONResponse(content=data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/perfumes", response_class=ORJSONResponse)
def perfume_network(
    min_similarity: float = Query(0.0, ge=0.0, le=1.0),  # 기본값 0.0 (전체)
    top_accords: int = Query(5, ge=1, le=5),  # 기본값 5 (최대)
    max_perfumes: int | None = Query(None, ge=1),  # None = 전체
    member_id: int | None = Query(None, ge=1),
    debug: bool = False,
):
    """
    향수 네트워크 데이터 조회
    
    클라이언트 사이드 필터링을 위해 전체 데이터를 반환하도록 최적화.
    - min_similarity: 0.0 (전체 유사도 엣지 포함)
    - top_accords: 5 (향수당 최대 5개 어코드)
    - max_perfumes: None (전체 향수)
    """
    try:
        data = get_perfume_network(
            min_similarity=min_similarity,
            top_accords=top_accords,
            max_perfumes=max_perfumes,
            member_id=member_id,
            debug=debug,
        )
        return ORJSONResponse(content=data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
