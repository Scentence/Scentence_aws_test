# backend/agent/tools_schemas_info.py
from pydantic import BaseModel, Field
from typing import List, Optional

# ==========================================
# [도구 입력 스키마]
# ==========================================
class NoteSearchInput(BaseModel):
    """노트(원료) 검색 도구 입력 스키마"""
    keywords: List[str] = Field(
        description="검색할 노트(원료) 이름 리스트 (예: ['Rose', 'Vetiver', 'Tonka Bean'])"
    )

class AccordSearchInput(BaseModel):
    """어코드(향조/분위기) 검색 도구 입력 스키마"""
    keywords: List[str] = Field(
        description="검색할 어코드(향조) 이름 리스트 (예: ['Woody', 'Citrus', 'Powdery'])"
    )

# ==========================================
# [에이전트 분석 결과 스키마]
# ==========================================
class IngredientAnalysisResult(BaseModel):
    """사용자 질문을 분석하여 노트와 어코드를 분류한 결과"""
    notes: List[str] = Field(
        default=[], 
        description="질문에서 식별된 노트(구체적 원료) 리스트 (예: Rose, Musk)"
    )
    accords: List[str] = Field(
        default=[], 
        description="질문에서 식별된 어코드(향의 분위기/계열) 리스트 (예: Woody, Floral)"
    )
    is_ambiguous: bool = Field(
        default=False, 
        description="사용자 질문이 향수와 관련 없거나 모호한 경우 True"
    )