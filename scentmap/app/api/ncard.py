from fastapi import APIRouter, Body
from typing import List
from scentmap.app.schemas.ncard_schemas import ScentCard
from scentmap.app.services.ncard_service import ncard_service

"""
NCardRouter: 향기 분석 카드 관련 독립 API 엔드포인트
"""

router = APIRouter(prefix="/ncard", tags=["ncard"])

@router.get("/", response_model=List[ScentCard])
async def get_scent_cards(member_id: int = 1): # 예시용 기본값
    """회원의 향기 분석 카드 목록 조회"""
    result = ncard_service.get_member_cards(member_id)
    # 스키마 변환 로직 필요 (ScentCard 모델에 맞게)
    return [] # 임시 반환

@router.post("/generate", response_model=ScentCard)
async def generate_scent_card(mbti: str = Body(..., embed=True), selected_accords: List[str] = Body(..., embed=True)):
    """사용자 입력 기반 즉석 향기 카드 생성 (세션 없이)"""
    # 세션 ID 없이 생성하는 경우를 위한 처리
    result = await ncard_service.generate_card(session_id="adhoc", mbti=mbti, selected_accords=selected_accords)
    # result['card'] 데이터를 ScentCard 모델로 변환하여 반환
    return ScentCard(**result['card'])
