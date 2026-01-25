# backend/agent/schemas_info.py
from typing import List, Optional, Dict, Literal, Any
from pydantic import BaseModel, Field

# ==========================================
# 1. 정보 검색 전용 상태 (Info State)
# ==========================================
# 메인 그래프의 State와는 별개로, 정보 팀 내부에서만 쓰는 상태입니다.
class InfoState(Dict):
    user_query: str                  # 사용자의 원래 질문
    info_type: Literal["perfume", "note", "accord", "brand", "unknown"] # 질문 유형
    target_name: str                 # 검색할 대상 이름 (예: "샤넬 넘버5", "머스크", "시트러스")
    
    # 검색 결과 데이터
    search_result: Optional[Dict]    # DB에서 찾은 Raw Data
    final_answer: Optional[str]      # 사용자에게 나갈 최종 답변 텍스트
    
    # 메시지 기록 (필요하다면 메인 그래프와 공유하거나 따로 관리)
    messages: List[Any] 


# ==========================================
# 2. 정보 분류 라우팅 (Router Output)
# ==========================================
class InfoRoutingDecision(BaseModel):
    """사용자 질문이 무엇에 관한 것인지 분류"""
    info_type: Literal["perfume", "note", "accord", "brand"] = Field(
        description="질문의 대상 카테고리 (향수, 노트, 어코드, 브랜드)"
    )
    target_name: str = Field(
        description="질문의 핵심 대상 이름 (예: '조말론 블랙베리', '우디', '샤넬')"
    )
    intent: str = Field(
        description="사용자가 궁금해하는 구체적인 내용 (예: '지속력이 궁금해', '어떤 향인지 설명해줘')"
    )