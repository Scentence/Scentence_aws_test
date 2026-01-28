from fastapi import APIRouter
from typing import List
from scentmap.app.schemas.ncard_schemas import ScentCard
from scentmap.app.services.ncard_service import ncard_service

router = APIRouter(prefix="/ncard", tags=["ncard"])

@router.get("/", response_model=List[ScentCard])
async def get_scent_cards():
    """향기 분석 카드 리스트 조회"""
    return ncard_service.get_dummy_cards()
