from fastapi import APIRouter, Body
from typing import List, Optional
from scentmap.app.schemas.ncard_schemas import ScentCard, ScentCardCreate
from scentmap.app.services.ncard_service import ncard_service

router = APIRouter(prefix="/ncard", tags=["ncard"])

@router.get("/", response_model=List[ScentCard])
async def get_scent_cards():
    """향기 분석 카드 리스트 조회"""
    return ncard_service.get_dummy_cards()

@router.post("/generate", response_model=ScentCard)
async def generate_scent_card(
    mbti: str = Body(..., embed=True),
    selected_accords: List[str] = Body(..., embed=True)
):
    """사용자 선택 기반 향기 분석 카드 생성"""
    return await ncard_service.generate_card(mbti, selected_accords)
