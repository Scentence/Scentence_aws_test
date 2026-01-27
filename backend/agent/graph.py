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
    WRITER_RECOMMENDATION_PROMPT_EXPERT,
    NOTE_SELECTION_PROMPT,
)
from .database import save_recommendation_log

# [정보 검색 전용 서브 그래프 임포트]
from .graph_info import info_graph

load_dotenv()

# ==========================================
# 1. 모델 설정
# ==========================================
FAST_LLM = ChatOpenAI(model="gpt-4.1-mini", temperature=0, streaming=True)
SMART_LLM = ChatOpenAI(model="gpt-4.1", temperature=0, streaming=True)
SUPER_SMART_LLM = ChatOpenAI(model="gpt-5.2", temperature=0, streaming=True)
# Non-streaming version for parallel_reco to prevent token interleaving
SUPER_SMART_LLM_NO_STREAM = ChatOpenAI(model="gpt-5.2", temperature=0, streaming=False)


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
        "messages": state.get("messages", []),
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

    # 현재 정보를 문자열로 변환
    current_context_str = json.dumps(current_prefs, ensure_ascii=False)

    # [★수정] 여기서 CURRENT_CONTEXT만 채워주면 됩니다! (SUFFICIENCY_CRITERIA는 이미 들어있음)
    try:
        formatted_prompt = INTERVIEWER_PROMPT.format(
            CURRENT_CONTEXT=current_context_str
        )
    except Exception as e:
        # 혹시라도 포맷팅 에러가 나면 원본 프롬프트를 사용하여 멈추지 않게 함
        print(f"⚠️ Prompt Formatting Error: {e}")
        formatted_prompt = INTERVIEWER_PROMPT.replace(
            "{{CURRENT_CONTEXT}}", "정보 없음"
        )

    messages = [SystemMessage(content=formatted_prompt)] + state["messages"]

    try:
        result = SMART_LLM.with_structured_output(InterviewResult).invoke(messages)
        new_prefs = result.user_preferences.dict(exclude_unset=True)
        updated_prefs = {
            **current_prefs,
            **{k: v for k, v in new_prefs.items() if v is not None},
        }

        if result.is_sufficient:
            print(
                f"      ✅ [Handover] 정보 확보 완료! Researcher로 전달: {json.dumps(updated_prefs, ensure_ascii=False)}",
                flush=True,
            )
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


# ==========================================
# [REMOVED] Old researcher_node and writer_node
# These have been replaced by parallel_reco_node which consolidates
# both functionalities with FCFS streaming.
# ==========================================


async def parallel_reco_node(state: AgentState):
    member_id = state.get("member_id", 0)
    user_prefs = state.get("user_preferences", {})
    current_context = json.dumps(user_prefs, ensure_ascii=False)

    plan_llm = SMART_LLM.with_structured_output(SearchStrategyPlan)
    seen_ids = set()
    seen_ids_lock = asyncio.Lock()

    def _normalize_section_boundary(previous_text: str, next_text: str) -> str:
        if not previous_text or not next_text:
            return next_text
        if not next_text.lstrip().startswith("##"):
            return next_text
        prev_trimmed = previous_text.rstrip()
        if prev_trimmed.endswith("---") and not previous_text.endswith("\n"):
            if not next_text.startswith("\n"):
                return f"\n{next_text}"
        return next_text

    async def prepare_strategy(strategy_name: str, priority: int):
        """Phase 1: Strategy planning + search + perfume selection (parallel)"""
        print(f"   👉 [Strategy {priority}] {strategy_name} 시작", flush=True)
        
        plan_messages = [
            SystemMessage(content=RESEARCHER_SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    f"사용자 요청 데이터: {current_context}\n"
                    f"전략 이름: {strategy_name}\n"
                    f"우선순위: {priority}\n"
                    "위 데이터를 바탕으로 전략을 수립해 주세요."
                )
            ),
        ]

        try:
            plan = await plan_llm.ainvoke(
                plan_messages, config={"tags": ["internal_helper"]}
            )
        except Exception as e:
            print(f"      ❌ [Strategy {priority}] 전략 수립 실패: {e}", flush=True)
            return None

        try:
            h_filters = plan.hard_filters.model_dump(exclude_none=True)
            s_filters = plan.strategy_filters.model_dump(exclude_none=True)
        except Exception:
            h_filters = {}
            s_filters = {}

        try:
            candidates, _match_type = await smart_search_with_retry_async(
                h_filters, s_filters, query_text=plan.reason
            )
        except Exception as e:
            print(f"      ❌ [Strategy {priority}] 검색 실패: {e}", flush=True)
            return None

        selected_perfume = None
        async with seen_ids_lock:
            for candidate in candidates:
                if candidate["id"] not in seen_ids:
                    selected_perfume = candidate
                    seen_ids.add(candidate["id"])
                    break

        if not selected_perfume:
            print(f"      ❌ [Strategy {priority}] 중복 제거 후 선택 가능한 향수 없음", flush=True)
            return None
        
        print(f"      ✅ [Strategy {priority}] 선택: {selected_perfume.get('name')} (ID: {selected_perfume.get('id')})", flush=True)

        save_recommendation_log(
            member_id=member_id, perfumes=[selected_perfume], reason=plan.reason
        )

        strategy_result = StrategyResult(
            strategy_name=plan.strategy_name,
            strategy_keyword=plan.strategy_keyword,
            strategy_reason=plan.reason,
            perfumes=[
                PerfumeDetail(
                    id=selected_perfume.get("id"),
                    perfume_name=selected_perfume.get("name"),
                    perfume_brand=selected_perfume.get("brand"),
                    accord=f"{selected_perfume.get('accords')}\n[Best Review]: {selected_perfume.get('best_review')}",
                    notes=PerfumeNotes(
                        top=selected_perfume.get("top_notes") or "N/A",
                        middle=selected_perfume.get("middle_notes") or "N/A",
                        base=selected_perfume.get("base_notes") or "N/A",
                    ),
                    image_url=selected_perfume.get("image_url"),
                    gender=selected_perfume.get("gender", "Unisex"),
                    season="All",
                    occasion="Any",
                )
            ],
        )

        section_data = {
            "user_preferences": user_prefs,
            "strategy": {
                "name": plan.strategy_name,
                "reason": plan.reason,
                "keywords": plan.strategy_keyword,
                "priority": priority,
            },
            "perfume": strategy_result.perfumes[0].dict(),
        }
        
        return {
            "section_data": section_data,
            "priority": priority,
        }

    async def generate_output(prepared_data: dict):
        """Phase 2: LLM output generation with streaming (sequential)"""
        if not prepared_data:
            return None
            
        section_data = prepared_data["section_data"]
        priority = prepared_data["priority"]
        
        USER_MODE = "BEGINNER"  # 옵션: "BEGINNER" | "EXPERT"
        print(f"   🐥 [Strategy {priority}] 비기너용 프롬프트 적용", flush=True)
        
        data_ctx = json.dumps(section_data, ensure_ascii=False, indent=2)

        section_system = (
            "당신은 향수를 잘 모르는 초보자를 위한 세상에서 가장 친절하고 감각적인 '향수 도슨트(Docent)'입니다.\n"
            "아래 [참고 데이터]에 있는 향수 1개만 사용해서, '단 하나의 추천 섹션'만 작성하세요.\n\n"
            "**[★ ZERO HALLUCINATION POLICY ★]**\n"
            "1. **데이터 그라운딩(Grounding)**: 반드시 제공된 [참고 데이터] 내의 정보만 사용하세요. 데이터에 없는 향수나 성분을 절대 지어내지 마세요.\n"
            "2. **수량 엄수**: 데이터가 1개이므로, 다른 향수를 절대 창작하지 마세요. 제공된 향수만 추천하세요.\n\n"
            "[★작성 규칙 - 필독★]\n\n"
            "1. **[도입부]**:\n"
            "   - **절대 금지**: 전체 도입부, '요청하신 3가지 전략', '수립한 전략대로' 같은 표현 사용 금지.\n"
            f"   - 바로 '## {priority}.' 로 시작하세요.\n\n"
            "2. **[추천 이유 (Logical Connection) - ★이미지 전략 합성]**:\n"
            "   - **브릿지(Bridge) 설명**: **사용자의 정보(대상, 계절 등)**와 **리서처가 전달한 전략적 의도(strategy_reason)**를 하나의 유기적인 문장으로 합쳐서 설명하세요.\n"
            "   - **핵심**: 리서처의 분석 내용을 그대로 읽어주는 것이 아니라, 도슨트로서 사용자에게 말을 건네는 따뜻한 문투로 재구성하세요.\n"
            "   - **일상어 변환**: '우디', '스파이시', '머스크' 등 전문 용어를 직접 쓰지 말고 느낌으로 풀어서 전달하세요.\n\n"
            "3. **[향 묘사 및 용어]**:\n"
            "   - **일상어 변환**: '탑/미들/베이스' 용어 금지. '꽃집에 들어선 듯한 향', '포근한 살냄새'처럼 풀어서 설명하세요.\n"
            "   - **성별 표현**: '유니섹스' 대신 '남성에게, 여성에게, 남녀 모두에게 잘 어울려요' 형태로 표현하세요.\n\n"
            "4. **[형식 규칙]**:\n"
            f"   - 출력은 반드시 '## {priority}.' 로 시작하세요.\n"
            "   - 섹션 안에 '---' 구분선을 출력하지 마세요 (구분선은 바깥에서 붙입니다).\n"
            "   - 반드시 이미지 마크다운을 포함하세요: ![이름](이미지링크)\n"
            "   - 마지막 줄에 반드시 저장 태그를 포함하세요: [[SAVE:향수ID:향수명]]\n\n"
            f"[모드]\n"
            f"- USER_MODE={USER_MODE}\n"
            "- 자연스럽고 산뜻한 한국어로 작성하세요.\n\n"
            "[참고 데이터]:\n"
            f"{data_ctx}"
        )

        messages = [SystemMessage(content=section_system)] + state["messages"]

        try:
            response = await SUPER_SMART_LLM.ainvoke(messages)
            print(f"      ✅ [Strategy {priority}] 작성 완료 ({len(response.content)} chars)", flush=True)
            return response.content
        except Exception as e:
            print(f"      ❌ [Strategy {priority}] 작성 실패: {e}", flush=True)
            return None

    # Phase 1: Parallel preparation (strategy planning + search)
    # All 3 strategies run simultaneously - fast!
    prep_tasks = [
        asyncio.create_task(prepare_strategy("이미지 강조", 1)),
        asyncio.create_task(prepare_strategy("이미지 보완", 2)),
        asyncio.create_task(prepare_strategy("이미지 반전", 3)),
    ]
    
    # Phase 2: Sequential output generation with streaming
    # Wait for prep in order, then generate output with streaming
    results = []
    try:
        data1 = await prep_tasks[0]
        result1 = await generate_output(data1) if data1 else None
        results.append(result1)
        
        data2 = await prep_tasks[1]
        result2 = await generate_output(data2) if data2 else None
        results.append(result2)
        
        data3 = await prep_tasks[2]
        result3 = await generate_output(data3) if data3 else None
        results.append(result3)
    except (Exception, asyncio.CancelledError) as e:
        print(f"   ⚠️ [Parallel Reco] Task cancelled or failed: {e}", flush=True)
        return {
            "messages": [AIMessage(content="조건에 맞는 향수를 찾지 못했습니다. 😢")],
            "next_step": "end",
        }

    # Assemble sections in order (1 → 2 → 3)
    full_text = ""
    for idx, result_text in enumerate(results, start=1):
        # Handle exceptions returned by gather(return_exceptions=True)
        if isinstance(result_text, (Exception, asyncio.CancelledError)):
            print(f"   ⚠️ [Section {idx}] Failed: {result_text}", flush=True)
            continue

        if not result_text:
            continue

        if full_text:
            # Add separator with clean boundaries
            full_text = f"{full_text}\n\n---\n\n{result_text}"
        else:
            full_text = result_text

    if not full_text:
        full_text = "조건에 맞는 향수를 찾지 못했습니다. 😢 대안을 안내해 드릴게요..."

    return {"messages": [AIMessage(content=full_text)], "next_step": "end"}


# ==========================================
# 4. Graph Build
# ==========================================
workflow = StateGraph(AgentState)

workflow.add_node("supervisor", supervisor_node)
workflow.add_node("interviewer", interviewer_node)
# workflow.add_node("researcher", researcher_node)  # Replaced by parallel_reco
# workflow.add_node("writer", writer_node)  # Replaced by parallel_reco
workflow.add_node("parallel_reco", parallel_reco_node)
workflow.add_node("info_retrieval_subgraph", call_info_graph_wrapper)

workflow.add_edge(START, "supervisor")

workflow.add_conditional_edges(
    "supervisor",
    lambda x: x["next_step"],
    {
        "interviewer": "interviewer",
        "info_retrieval": "info_retrieval_subgraph",
        "writer": "parallel_reco",  # Replaced writer with parallel_reco
    },
)

workflow.add_conditional_edges(
    "interviewer",
    lambda x: x["next_step"],
    {"end": END, "researcher": "parallel_reco", "writer": "parallel_reco"},
)

# workflow.add_edge("researcher", "writer")  # Old flow - replaced
# workflow.add_edge("writer", END)  # Old flow - replaced
workflow.add_edge("parallel_reco", END)
workflow.add_edge("info_retrieval_subgraph", END)

checkpointer = MemorySaver()
app_graph = workflow.compile(checkpointer=checkpointer)
