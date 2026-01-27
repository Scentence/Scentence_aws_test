"""
향기카드 데이터 스키마 정의
"""
from pydantic import BaseModel, Field
from typing import List, Optional


class AccordInfo(BaseModel):
    """어코드 정보"""
    name: str = Field(..., description="어코드 이름")
    description: str = Field(..., description="어코드 설명")


class ScentCard(BaseModel):
    """향기카드 기본 스키마"""
    title: str = Field(
        ..., 
        min_length=3, 
        max_length=30,
        description="카드 제목 (5-7자 권장)"
    )
    story: str = Field(
        ..., 
        min_length=20, 
        max_length=300,
        description="짧은 스토리 (2-3문장)"
    )
    accords: List[AccordInfo] = Field(
        ..., 
        min_items=1, 
        max_items=5,
        description="선택된 어코드 정보"
    )


class ScentCardResponse(BaseModel):
    """향기카드 API 응답"""
    card: ScentCard
    session_id: str
    generation_method: str = Field(
        ..., 
        description="생성 방법: 'llm_full', 'llm_light', 'template'"
    )
    generation_time_ms: Optional[int] = None
