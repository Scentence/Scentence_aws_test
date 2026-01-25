# backend/agent/graph.py
import os
import json
import asyncio
import itertools
from typing import Literal, List, Dict, Any, Optional

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

# [Import] 로컬 모듈
from .schemas import (
    AgentState,
    UserPreferences,
    InterviewResult,
    RoutingDecision, 
    ResearchActionPlan,
    SearchStrategyPlan,
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

# [정보 검색 전용 서브 그래프 임포트]
from .graph_info import info_graph

load_dotenv()

# ==========================================
# 1. 모델 설정
# ==========================================
FAST_LLM = ChatOpenAI(model="gpt-4o-mini", temperature=0, streaming=True)
SMART_LLM = ChatOpenAI(model="gpt-4.1", temperature=0, streaming=True)
SUPER_SMART_LLM = ChatOpenAI(model="gpt-5.2", temperature=0, streaming=True)

# ==========================================
# 2. 유틸리티
# ==========================================
def log_filters(h_filters: dict, s_filters: dict):
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
    priority_order = ["note", "accord", "occasion"]
    active_keys = [k for k in priority_order if k in s_filters and s_filters[k]]

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

async def call_info_graph_wrapper(state: AgentState):
    """Sub-Graph Wrapper"""
    print(f"\n🚀 [Main Graph] 'info_graph' 서브 그래프 호출...", flush=True)
    current_query = state.get("user_query", "")
    
    if not current_query and state.get("messages"):
        last_msg = state["messages"][-1]
        if isinstance(last_msg, HumanMessage):
            current_query = last_msg.content
            
    print(f"   👉 전달할 Query: {current_query}", flush=True)

    subgraph_input = {
        "user_query": current_query,
        "messages": state.get("messages", [])
    }
    
    try:
        result = await info_graph.ainvoke(subgraph_input)
        print(f"✅ [Main Graph] 서브 그래프 완료. 결과 복귀.", flush=True)
        return {"messages": result.get("messages", [])}
        
    except Exception as e:
        print(f"🚨 [Main Graph] 서브 그래프 에러: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return {"messages": [AIMessage(content="정보 검색 중 오류가 발생했습니다.")]}

# ==========================================
# 3. Node Functions
# ==========================================

def supervisor_node(state: AgentState):
    """[Main Router]"""
    print("\n" + "=" * 60, flush=True)
    print("👀 [Supervisor] 사용자 의도 분류 중...", flush=True)
    
    if state.get("active_mode") == "interviewer":
        print("   👉 인터뷰 진행 중 -> Interviewer로 이동", flush=True)
        return {"next_step": "interviewer"}

    messages = [SystemMessage(content=SUPERVISOR_PROMPT)] + state["messages"]
    
    try:
        decision = SMART_LLM.with_structured_output(RoutingDecision).invoke(messages)
        next_step = decision.next_step 
        print(f"   👉 분류 결과: {next_step}", flush=True)
        return {"next_step": next_step}
        
    except Exception as e:
        print(f"   ⚠️ 분류 실패(Error): {e} -> 기본값 Writer로 이동", flush=True)
        return {"next_step": "writer"}


def interviewer_node(state: AgentState):
    """[Interviewer]"""
    print(f"\n🎤 [Interviewer] 추천 정보 분석 및 검증...", flush=True)
    current_prefs = state.get("user_preferences", {})
    messages = [SystemMessage(content=INTERVIEWER_PROMPT)] + state["messages"]
    
    try:
        result = SMART_LLM.with_structured_output(InterviewResult).invoke(messages)
        new_prefs = result.user_preferences.dict(exclude_unset=True)
        updated_prefs = {
            **current_prefs,
            **{k: v for k, v in new_prefs.items() if v is not None},
        }

        if result.is_sufficient:
            print(f"      ✅ [Handover] 정보 확보 완료! Researcher로 전달: {json.dumps(updated_prefs, ensure_ascii=False)}", flush=True)
            return {
                "next_step": "researcher",
                "user_preferences": updated_prefs,
                "status": "모든 정보가 확인되었습니다. 추천 전략을 수립합니다...",
                "active_mode": None, 
            }
            
        return {
            "messages": [AIMessage(content=result.response_message)],
            "user_preferences": updated_prefs,
            "active_mode": "interviewer", 
            "next_step": "end", 
        }
    except Exception as e:
        print(f"Interviewer Error: {e}")
        return {"next_step": "writer"} 


async def researcher_node(state: AgentState):
    print(f"\n🧠 [Researcher] 전략 수립 및 병렬 DB 검색 시작...", flush=True)
    current_member_id = state.get("member_id", 0)
    user_prefs = state.get("user_preferences", {})
    current_context = json.dumps(user_prefs, ensure_ascii=False)

    user_note = user_prefs.get("note")
    refined_hard_note = None
    if user_note:
        matched = await lookup_note_by_string_tool.ainvoke({"keyword": user_note})
        if matched:
            refined_hard_note = matched[0]

    messages = [
        SystemMessage(content=RESEARCHER_SYSTEM_PROMPT),
        HumanMessage(
            content=f"사용자 요청 데이터: {current_context}\n위 데이터를 바탕으로 '이미지 강조, 보완, 반전'의 3가지 검색 전략을 세워주세요."
        ),
    ]
    plan_result = await SMART_LLM.with_structured_output(ResearchActionPlan).ainvoke(messages)

    async def process_strategy_candidates(plan: SearchStrategyPlan):
        print(f"   👉 [Parallel Task] {plan.strategy_name}", flush=True)
        h_filters = plan.hard_filters.model_dump(exclude_none=True)
        if refined_hard_note:
            h_filters["note"] = refined_hard_note
        s_filters = plan.strategy_filters.model_dump(exclude_none=True)

        strategy_note_input = s_filters.get("note")
        if strategy_note_input:
            raw_keyword = (
                strategy_note_input[0]
                if isinstance(strategy_note_input, list)
                else strategy_note_input
            )
            candidates = await lookup_note_by_vector_tool.ainvoke({"keyword": raw_keyword})
            if candidates:
                selection_messages = [
                    SystemMessage(content=NOTE_SELECTION_PROMPT.format(candidates=candidates)),
                    HumanMessage(content=f"전략: {plan.strategy_name}\n의도: {plan.reason}"),
                ]
                selected_res = await SMART_LLM.ainvoke(selection_messages)
                llm_selected = [c for c in candidates if c.lower() in selected_res.content.lower()]
                s_filters["note"] = llm_selected if llm_selected else candidates[:1]

        log_filters(h_filters, s_filters)
        db_perfumes, match_type = await smart_search_with_retry_async(
            h_filters, s_filters, query_text=plan.reason
        )
        return {"plan": plan, "candidates": db_perfumes}

    tasks = [process_strategy_candidates(p) for p in plan_result.plans]
    all_candidates_results = await asyncio.gather(*tasks)

    final_results = []
    seen_perfume_ids = set()

    for item in all_candidates_results:
        plan = item["plan"]
        candidates = item["candidates"]
        
        selected_p = None
        for p in candidates:
            if p["id"] not in seen_perfume_ids:
                selected_p = p
                seen_perfume_ids.add(p["id"])
                break
        
        if not selected_p:
            # [★수정: 로그 추가] 검색 실패 시
            print(f"      ❌ [Result] {plan.strategy_name}: 검색된 향수가 없거나 중복되어 선택 실패", flush=True)
            continue

        # [★수정: 로그 추가] 검색 성공 시 향수 이름 출력
        print(f"      ✅ [Result] {plan.strategy_name}: {selected_p.get('brand')} - {selected_p.get('name')} (ID: {selected_p.get('id')})", flush=True)

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

    if not final_results:
        print(f"      ❌ [Result] 모든 전략에서 추천 가능한 향수를 찾지 못했습니다.", flush=True)
        return {
            "research_results": {"results": []},
            # [중요] 실패했음을 명시하는 메시지로 변경
            "messages": [AIMessage(content="[RESEARCH_FAILED]")], 
            "next_step": "writer",
            # [중요] 상태 메시지 수정 -> 이렇게 해야 Writer가 사과 멘트를 준비합니다.
            "status": "조건에 맞는 향수를 찾지 못했습니다. 😢 대안을 안내해 드릴게요...",
        }

    # 성공했을 때 (기존 로직)
    return {
        "research_results": {"results": [r.dict() for r in final_results]},
        "messages": [AIMessage(content="[RESEARCH_DONE]")],
        "next_step": "writer",
        "status": "전략에 맞는 향수들을 모두 찾았습니다! 답변을 작성합니다...",
    }


async def writer_node(state: AgentState):
    print(f"\n✍️ [Writer] 답변 작성 중...", flush=True)
    research_data = state.get("research_results", {})
    results_list = research_data.get("results", [])

    prompt = WRITER_RECOMMENDATION_PROMPT if results_list else WRITER_FAILURE_PROMPT
    if not results_list and state.get("next_step") == "writer":
        prompt = WRITER_CHAT_PROMPT

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
workflow.add_node("info_retrieval_subgraph", call_info_graph_wrapper)

workflow.add_edge(START, "supervisor")

workflow.add_conditional_edges(
    "supervisor",
    lambda x: x["next_step"],
    {
        "interviewer": "interviewer",
        "info_retrieval": "info_retrieval_subgraph",
        "writer": "writer"
    },
)

workflow.add_conditional_edges(
    "interviewer",
    lambda x: x["next_step"],
    {
        "end": END,                
        "researcher": "researcher", 
        "writer": "writer"          
    },
)

workflow.add_edge("researcher", "writer")
workflow.add_edge("writer", END)
workflow.add_edge("info_retrieval_subgraph", END)

checkpointer = MemorySaver()
app_graph = workflow.compile(checkpointer=checkpointer)