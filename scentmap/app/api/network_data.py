from fastapi import APIRouter, HTTPException, Query

from scentmap.app.schemas.network_data_schema import NetworkResponse
from scentmap.app.services.network_data_service import get_perfume_network


router = APIRouter(prefix="/network", tags=["network"])


@router.get("/perfumes", response_model=NetworkResponse)
def perfume_network(
    min_similarity: float = Query(0.45, ge=0.0, le=1.0),
    top_accords: int = Query(2, ge=1, le=5),
    max_perfumes: int | None = Query(None, ge=1),
    debug: bool = False,
):
    try:
        return get_perfume_network(
            min_similarity=min_similarity,
            top_accords=top_accords,
            max_perfumes=max_perfumes,
            debug=debug,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
