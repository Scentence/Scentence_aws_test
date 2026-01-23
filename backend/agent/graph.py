import os
import json
import traceback
import asyncio
import itertools
from typing import Literal, List, Dict, Any, Optional

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

# [Import] 로컬 모듈 - schemas.py의 모든 클래스를 가져옵니다.
from .schemas import (
    AgentState,
    UserPreferences,
    InterviewResult,
    RoutingDecision,
    ResearchActionPlan,
    SearchStrategyPlan,
    HardFilters,
    StrategyFilters,
    ResearcherOutput,
    StrategyResult,
    PerfumeDetail,
    PerfumeNotes,
)

from .tools import (
    advanced_perfume_search_tool,
    lookup_note_by_string_tool,
    lookup_note_by_vector_tool,
)

from .prompts import (
    SUPERVISOR_PROMPT,
    INTERVIEWER_PROMPT,
    RESEARCHER_SYSTEM_PROMPT,
    WRITER_FAILURE_PROMPT,
    WRITER_CHAT_PROMPT,
    WRITER_RECOMMENDATION_PROMPT,
    NOTE_SELECTION_PROMPT,
)
from .database import save_recommendation_log

load_dotenv()

# ==========================================
# 1. 모델 설정 (성능 이원화)
# ==========================================
FAST_LLM = ChatOpenAI(model="gpt-4o-mini", temperature=0, streaming=True)
SMART_LLM = ChatOpenAI(model="gpt-4.1", temperature=0, streaming=True)
SUPER_SMART_LLM = ChatOpenAI(model="gpt-5.2", temperature=0, streaming=True)

# ==========================================
# 2. 유틸리티 및 보조 기능 함수
# ==========================================


def log_filters(h_filters: dict, s_filters: dict):
    """현재 적용 중인 필터 조건을 가독성 좋게 출력합니다."""
    h_items = [f"{k.capitalize()}: {v}" for k, v in h_filters.items() if v]
    h_str = " | ".join(h_items) if h_items else "None"

    s_items = []
    for k, v in s_filters.items():
        if v:
            val_str = str(v) if not isinstance(v, list) else f"{v}"
            s_items.append(f"{k.capitalize()}: {val_str}")
    s_str = " | ".join(s_items) if s_items else "None"

    print(f"       🔒 [Hard] {h_str}", flush=True)
    print(f"       ✨ [Soft] {s_str}", flush=True)


async def smart_search_with_retry_async(
    h_filters: dict, s_filters: dict, exclude_ids: list = None, query_text: str = ""
):
    """필터를 단계별로 완화하며 비동기적으로 향수를 검색합니다."""
    priority_order = ["note", "accord", "occasion"]
    active_keys = [k for k in priority_order if k in s_filters and s_filters[k]]

    # 1차 시도 (전체 조건)
    results = await advanced_perfume_search_tool.ainvoke(
        {
            "hard_filters": h_filters,
            "strategy_filters": s_filters,
            "exclude_ids": exclude_ids,
            "query_text": query_text,
        }
    )
    if results:
        return results, "Perfect Match"

    # 2차 시도 (필터 조합 완화 루프)
    for r in range(len(active_keys) - 1, 0, -1):
        for combo_keys in itertools.combinations(active_keys, r):
            temp_filters = {k: s_filters[k] for k in combo_keys}
            results = await advanced_perfume_search_tool.ainvoke(
                {
                    "hard_filters": h_filters,
                    "strategy_filters": temp_filters,
                    "exclude_ids": exclude_ids,
                    "query_text": query_text,
                }
            )
            if results:
                return results, f"Relaxed (Level {len(active_keys)-r})"
    return [], "No Results"


# ==========================================
# 3. Node Functions
# ==========================================


def supervisor_node(state: AgentState):
    print("\n" + "=" * 60, flush=True)
    print("👀 [Supervisor] 대화 분석 및 정보 추출 중...", flush=True)
    current_prefs = state.get("user_preferences", {})

    if state.get("active_mode") == "interviewer":
        return {"next_step": "interviewer"}

    messages = [SystemMessage(content=INTERVIEWER_PROMPT)] + state["messages"]
    try:
        result = SMART_LLM.with_structured_output(InterviewResult).invoke(messages)
        new_prefs = result.user_preferences.dict(exclude_unset=True)
        updated_prefs = {
            **current_prefs,
            **{k: v for k, v in new_prefs.items() if v is not None},
        }

        if result.is_off_topic:
            return {"next_step": "writer", "active_mode": None}
        if result.is_sufficient:
            return {
                "next_step": "researcher",
                "user_preferences": updated_prefs,
                "status": "추천 전략을 세우는 중입니다...",
                "active_mode": None,
            }
        return {
            "next_step": "interviewer",
            "user_preferences": updated_prefs,
            "active_mode": "interviewer",
        }
    except Exception:
        return {"next_step": "interviewer"}


def interviewer_node(state: AgentState):
    print(f"\n🎤 [Interviewer] 정보 분석 및 추가 질문 생성...", flush=True)
    messages = [SystemMessage(content=INTERVIEWER_PROMPT)] + state["messages"]
    try:
        result = SMART_LLM.with_structured_output(InterviewResult).invoke(messages)
        if result.is_sufficient:
            return {
                "next_step": "researcher",
                "status": "추천 전략을 세우는 중입니다...",
                "active_mode": None,
            }
        return {
            "messages": [AIMessage(content=result.response_message)],
            "user_preferences": result.user_preferences.dict(),
            "active_mode": "interviewer",
            "next_step": "end",
        }
    except Exception:
        return {"next_step": "writer"}


async def researcher_node(state: AgentState):
    print(f"\n🧠 [Researcher] 전략 수립 및 병렬 DB 검색 시작...", flush=True)
    current_member_id = state.get("member_id", 0)
    user_prefs = state.get("user_preferences", {})
    current_context = json.dumps(user_prefs, ensure_ascii=False)

    # 1. 하드 필터용 노트 전처리 (사용자 입력 노드를 DB 규격으로 변환)
    user_note = user_prefs.get("note")
    refined_hard_note = None
    if user_note:
        matched = await lookup_note_by_string_tool.ainvoke({"keyword": user_note})
        if matched:
            refined_hard_note = matched[0]

    # 2. 전략 수립 (gpt-4o-mini 사용으로 지연 시간 단축)
    messages = [
        SystemMessage(content=RESEARCHER_SYSTEM_PROMPT),
        HumanMessage(
            content=f"사용자 요청 데이터: {current_context}\n위 데이터를 바탕으로 '이미지 강조, 보완, 반전'의 3가지 검색 전략을 세워주세요."
        ),
    ]
    plan_result = await SMART_LLM.with_structured_output(ResearchActionPlan).ainvoke(
        messages
    )

    # 3. 개별 전략 처리 비동기 내부 함수 (중복 방지를 위해 후보군 전체 반환)
    async def process_strategy_candidates(plan: SearchStrategyPlan):
        # [로그] 각 전략의 시작 알림
        print(f"   👉 [Parallel Task Start] {plan.strategy_name}", flush=True)

        h_filters = plan.hard_filters.model_dump(exclude_none=True)
        if refined_hard_note:
            h_filters["note"] = refined_hard_note

        s_filters = plan.strategy_filters.model_dump(exclude_none=True)

        # 소프트 필터용 노트 벡터 검색 및 LLM 최종 선택
        strategy_note_input = s_filters.get("note")
        if strategy_note_input:
            raw_keyword = (
                strategy_note_input[0]
                if isinstance(strategy_note_input, list)
                else strategy_note_input
            )
            candidates = await lookup_note_by_vector_tool.ainvoke(
                {"keyword": raw_keyword}
            )

            if candidates:
                selection_messages = [
                    SystemMessage(
                        content=NOTE_SELECTION_PROMPT.format(candidates=candidates)
                    ),
                    HumanMessage(
                        content=f"전략: {plan.strategy_name}\n의도: {plan.reason}"
                    ),
                ]
                selected_res = await SMART_LLM.ainvoke(selection_messages)
                llm_selected = [
                    c for c in candidates if c.lower() in selected_res.content.lower()
                ]
                s_filters["note"] = (
                    llm_sel if (llm_sel := llm_selected) else candidates[:1]
                )

        # [로그] 현재 적용된 상세 필터 출력
        log_filters(h_filters, s_filters)

        # 검색 결과 리스트 전체(candidates)를 비동기로 가져옵니다.
        db_perfumes, match_type = await smart_search_with_retry_async(
            h_filters, s_filters, query_text=plan.reason
        )

        # [로그] 검색 결과 요약 출력
        print(
            f"      ✅ {plan.strategy_name}: {len(db_perfumes)}건 발견 ({match_type})",
            flush=True,
        )

        return {"plan": plan, "candidates": db_perfumes}

    # 4. asyncio.gather를 통해 3가지 전략을 병렬로 동시 수행
    tasks = [process_strategy_candidates(p) for p in plan_result.plans]
    all_candidates_results = await asyncio.gather(*tasks)

    # 5. 중복 제거 및 전략별 고유 향수 최종 선택
    final_results = []
    seen_perfume_ids = set()

    for item in all_candidates_results:
        plan = item["plan"]
        candidates = item["candidates"]

        # 이미 다른 전략에서 선택된 향수는 제외하고 가장 순위가 높은 것을 선택합니다.
        selected_p = None
        for p in candidates:
            if p["id"] not in seen_perfume_ids:
                selected_p = p
                seen_perfume_ids.add(p["id"])
                break

        # 만약 모든 후보가 중복이거나 결과가 없다면 해당 전략은 건너뜁니다.
        if not selected_p:
            continue

        # DB 로그 저장 및 결과 객체 생성
        save_recommendation_log(
            member_id=current_member_id, perfumes=[selected_p], reason=plan.reason
        )

        final_results.append(
            StrategyResult(
                strategy_name=plan.strategy_name,
                strategy_keyword=plan.strategy_keyword,
                strategy_reason=plan.reason,
                perfumes=[
                    PerfumeDetail(
                        id=selected_p.get("id"),
                        perfume_name=selected_p.get("name"),
                        perfume_brand=selected_p.get("brand"),
                        accord=f"{selected_p.get('accords')}\n[Best Review]: {selected_p.get('best_review')}",
                        notes=PerfumeNotes(
                            top=selected_p.get("top_notes") or "N/A",
                            middle=selected_p.get("middle_notes") or "N/A",
                            base=selected_p.get("base_notes") or "N/A",
                        ),
                        image_url=selected_p.get("image_url"),
                        gender=selected_p.get("gender", "Unisex"),
                        season="All",
                        occasion="Any",
                    )
                ],
            )
        )

    # 6. 최종 결과를 상태에 반영하고 작가 노드로 이동
    return {
        "research_results": {"results": [r.dict() for r in final_results]},
        "messages": [AIMessage(content="[RESEARCH_DONE]")],
        "next_step": "writer",
    }


async def writer_node(state: AgentState):
    print(f"\n✍️ [Writer] 답변 작성 중...", flush=True)
    research_data = state.get("research_results", {})
    results_list = research_data.get("results", [])

    prompt = WRITER_RECOMMENDATION_PROMPT if results_list else WRITER_FAILURE_PROMPT
    data_ctx = (
        json.dumps(research_data, ensure_ascii=False, indent=2) if results_list else ""
    )

    messages = [
        SystemMessage(content=f"{prompt}\n\n[참고 데이터]:\n{data_ctx}")
    ] + state["messages"]

    response = await SUPER_SMART_LLM.ainvoke(messages)
    return {"messages": [response], "next_step": "end"}


# ==========================================
# 4. Graph Build
# ==========================================
workflow = StateGraph(AgentState)
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("interviewer", interviewer_node)
workflow.add_node("researcher", researcher_node)
workflow.add_node("writer", writer_node)

workflow.add_edge(START, "supervisor")
workflow.add_conditional_edges(
    "supervisor",
    lambda x: x["next_step"],
    {"interviewer": "interviewer", "researcher": "researcher", "writer": "writer"},
)
workflow.add_conditional_edges(
    "interviewer",
    lambda x: x["next_step"],
    {"end": END, "researcher": "researcher", "writer": "writer"},
)
workflow.add_edge("researcher", "writer")
workflow.add_edge("writer", END)

checkpointer = MemorySaver()
app_graph = workflow.compile(checkpointer=checkpointer)
