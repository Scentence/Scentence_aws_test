# backend/tools.py
from langchain_core.tools import tool
from typing import List, Dict, Any

# database.py에서 분리된 핵심 함수들을 임포트합니다.
# [수정] rerank_perfumes 추가
from database import (
    lookup_note_by_string,
    lookup_note_by_vector,
    search_perfumes,
    rerank_perfumes,
)

# 정의한 스키마를 임포트합니다.
# [수정] AdvancedSearchInput 사용
from tools_schemas import LookupNoteInput, AdvancedSearchInput


@tool(args_schema=LookupNoteInput)
def lookup_note_by_string_tool(keyword: str) -> List[str]:
    """
    사용자가 직접 입력한 구체적인 향료 이름의 오탈자를 교정합니다.
    - 사용자가 직접 언급한 '명시적 노트'를 Hard Filter용 표준 명칭으로 바꿀 때 사용하세요.
    """
    return lookup_note_by_string(keyword)


@tool(args_schema=LookupNoteInput)
def lookup_note_by_vector_tool(keyword: str) -> List[str]:
    """
    추상적인 향기 느낌이나 키워드와 관련된 실제 향료 후보군 10개를 검색합니다.
    - AI가 제안한 '이미지 키워드'를 실제 DB 노드로 변환하여 선택지를 확보할 때 사용하세요.
    """
    return lookup_note_by_vector(keyword)


@tool(args_schema=AdvancedSearchInput)
def advanced_perfume_search_tool(
    hard_filters: Dict[str, Any],
    strategy_filters: Dict[str, List[str]],
    exclude_ids: List[int],
    query_text: str,
) -> List[Dict[str, Any]]:
    """
    [고도화된 검색 도구]
    1. DB에서 조건에 맞는 향수 20개를 1차로 검색합니다. (Broad Retrieval)
    2. 입력된 'query_text'(전략 의도)와 리뷰 데이터를 비교해 가장 적합한 순서로 재정렬합니다. (Semantic Reranking)
    3. 최종 상위 5개를 반환합니다.
    """

    # 1. Broad Retrieval (20개 확보)
    candidates = search_perfumes(
        hard_filters=hard_filters,
        strategy_filters=strategy_filters,
        exclude_ids=exclude_ids,
        limit=20,  # 후보군을 넓게 잡음
    )

    if not candidates:
        return []

    # 2. Semantic Reranking (Top 5 선정)
    # query_text(전략 이유)를 이용해 순위를 뒤집습니다.
    final_results = rerank_perfumes(candidates, query_text, top_k=5)

    return final_results


# Export tools list
TOOLS = [
    lookup_note_by_string_tool,
    lookup_note_by_vector_tool,
    advanced_perfume_search_tool,
]
