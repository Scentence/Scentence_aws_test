import os
import json
import traceback
from typing import Literal, List, Dict, Any, Optional

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
import itertools
import copy

# [Import] 로컬 모듈 - schemas.py에서 정의한 모든 클래스를 가져옵니다.
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

load_dotenv()

# ==========================================
# 1. 모델 설정
# ==========================================
FAST_LLM = ChatOpenAI(model="gpt-4o-mini", temperature=0, streaming=True)
SMART_LLM = ChatOpenAI(model="gpt-4o", temperature=0, streaming=True)
SUPER_SMART_LLM = ChatOpenAI(model="gpt-5.2", temperature=0, streaming=True)


# ==========================================
# 3. Node Functions
# ==========================================
def supervisor_node(state: AgentState):
    print("\n" + "=" * 60, flush=True)
    print("👀 [Supervisor] 대화 분석 및 정보 추출 중...", flush=True)

    # 1. 기존에 수집된 정보 가져오기 (휘발 방지)
    current_prefs = state.get("user_preferences", {})

    # 2. 이미 인터뷰 모드라면 바로 인터뷰어로 토스
    if state.get("active_mode") == "interviewer":
        print("   -> ⏩ Active Mode: Interviewer 유지", flush=True)
        return {"next_step": "interviewer"}

    # 3. 인터뷰어와 동일한 프롬프트 및 스키마를 사용하여 정보 추출
    # Supervisor 단계에서 정보를 추출해야 Researcher가 빈 값을 받지 않습니다.
    messages = [SystemMessage(content=INTERVIEWER_PROMPT)] + state["messages"]

    try:
        # 정밀한 정보 추출을 위해 SMART_LLM(gpt-4o)을 사용합니다.
        result = SMART_LLM.with_structured_output(InterviewResult).invoke(messages)

        # 4. 정보 업데이트 및 병합
        new_prefs = result.user_preferences.dict(exclude_unset=True)
        updated_prefs = {
            **current_prefs,
            **{k: v for k, v in new_prefs.items() if v is not None},
        }

        # 5. 라우팅 판단
        # [Case A] 향수와 관련 없는 잡담인 경우
        if result.is_off_topic:
            print(f"   -> 🎯 결정된 경로: WRITER (Off-topic)", flush=True)
            return {"next_step": "writer", "active_mode": None}

        # [Case B] 필수 정보(Target + Concept)가 충족된 경우 -> 바로 검색
        if result.is_sufficient:
            print(f"   -> 🎯 결정된 경로: RESEARCHER (정보 충족)", flush=True)
            print(
                f"      수집 정보: {json.dumps(updated_prefs, ensure_ascii=False)}",
                flush=True,
            )
            return {
                "next_step": "researcher",
                "user_preferences": updated_prefs,
                "active_mode": None,
            }

        # [Case C] 정보가 더 필요한 경우 -> Interviewer에게 전달
        else:
            print(f"   -> 🎯 결정된 경로: INTERVIEWER (추가 질문 필요)", flush=True)
            return {
                "next_step": "interviewer",
                "user_preferences": updated_prefs,
                "active_mode": "interviewer",
            }

    except Exception as e:
        print(f"   -> ⚠️ Supervisor Error: {e}")
        # 에러 발생 시 안전하게 인터뷰어 단계로 보냅니다.
        return {"next_step": "interviewer"}


# ==========================================
# 4. Interviewer 노드 정의
# ==========================================


def interviewer_node(state: AgentState):
    print(f"\n🎤 [Interviewer] 정보 분석 중...", flush=True)
    current_prefs = state.get("user_preferences", {})
    current_prefs_str = (
        json.dumps(current_prefs, ensure_ascii=False, indent=2)
        if current_prefs
        else "없음"
    )

    augmented_prompt = f"""
    {INTERVIEWER_PROMPT}
    [★Context★] 이전 수집 정보: {current_prefs_str}
    """
    messages = [SystemMessage(content=augmented_prompt)] + state["messages"]

    try:
        result = SMART_LLM.with_structured_output(InterviewResult).invoke(messages)
        print(
            f"   -> 📊 판단: 충족({result.is_sufficient}), 잡담({result.is_off_topic})",
            flush=True,
        )

        if result.is_off_topic:
            return {"active_mode": None, "next_step": "writer"}

        if result.is_sufficient:
            print("   -> 🚀 정보 충족! Researcher 호출", flush=True)
            return {
                "messages": [],
                "user_preferences": result.user_preferences.dict(),
                "active_mode": None,
                "next_step": "researcher",
            }
        else:
            print("   -> ❓ 정보 부족", flush=True)
            print("현재 수집된 사용자 정보 :", result.user_preferences.dict())
            return {
                "messages": [AIMessage(content=result.response_message)],
                "user_preferences": result.user_preferences.dict(),
                "active_mode": "interviewer",
                "next_step": "end",
            }
    except Exception as e:
        print(f"   -> ⚠️ Error: {e}")
        return {"active_mode": None, "next_step": "writer"}


# ==========================================
# 5. Researcher에 사용될 기능함수 정의
# ==========================================
def log_filters(h_filters: dict, s_filters: dict):
    """현재 적용 중인 필터 조건을 가독성 좋게 출력합니다."""
    # Hard Filter 포맷팅
    h_items = [f"{k.capitalize()}: {v}" for k, v in h_filters.items() if v]
    h_str = " | ".join(h_items) if h_items else "None"
    
    # Soft Filter 포맷팅
    s_items = []
    for k, v in s_filters.items():
        if v:
            # 리스트면 간결하게 표시
            val_str = str(v) if not isinstance(v, list) else f"{v}"
            s_items.append(f"{k.capitalize()}: {val_str}")
    s_str = " | ".join(s_items) if s_items else "None"

    print(f"       🔒 [Hard] {h_str}", flush=True)
    print(f"       ✨ [Soft] {s_str}", flush=True)

# ==========================================
# [Helper] 스마트 검색 및 재시도 로직 (조합형 시도)
# ==========================================
# backend/graph.py

def smart_search_with_retry(
    h_filters: dict, 
    s_filters: dict, 
    exclude_ids: list = None,
    query_text: str = "" 
):

    # 중요도 순서: Note > Accord > Occasion
    priority_order = ["note", "accord", "occasion"]
    active_keys = [k for k in priority_order if k in s_filters and s_filters[k]]

    # ---------------------------------------------------------
    # 1. [Attempt 1] Full Conditions (로그 유지)
    # ---------------------------------------------------------
    print(f"\n      📍 [Attempt 1] Full Conditions ({len(active_keys)} filters)", flush=True)
    log_filters(h_filters, s_filters)

    results = advanced_perfume_search_tool.invoke(
        {
            "hard_filters": h_filters,
            "strategy_filters": s_filters,
            "exclude_ids": exclude_ids,
            "query_text": query_text,
        }
    )

    if results:
        print(f"      ✅ Found {len(results)} perfumes (Perfect Match)", flush=True)
        return results, "Perfect Match"

    # ---------------------------------------------------------
    # 2. [Loop] Combinations (로그 제거 -> 성공 시에만 출력)
    # ---------------------------------------------------------
    for r in range(len(active_keys) - 1, 0, -1):
        # 중요도 순서대로 조합 생성
        combinations = list(itertools.combinations(active_keys, r))
        
        # [수정] "Trying..." 로그 제거 (조용히 시도)
        
        for combo_keys in combinations:
            temp_filters = {k: s_filters[k] for k in combo_keys}
            combo_str = "+".join([k.upper() for k in combo_keys])
            
            # [수정] "Testing..." 로그 제거 (조용히 시도)

            results = advanced_perfume_search_tool.invoke(
                {
                    "hard_filters": h_filters,
                    "strategy_filters": temp_filters,
                    "exclude_ids": exclude_ids,
                    "query_text": query_text,
                }
            )

            if results:
                # [수정] 성공 시 Level과 조합명(Combo)을 명시
                level = len(active_keys) - r
                match_type = f"Relaxed (Level {level} - [{combo_str}])"
                print(f"      ✅ Found {len(results)} perfumes ({match_type})", flush=True)
                return results, match_type

    return [], "No Results"

# ==========================================
# 6. Researcher노드 정의
# ==========================================
# backend/graph.py

def researcher_node(state: AgentState):
    print(f"\n🧠 [Researcher] 전략 수립 및 DB 검색...", flush=True)

    user_prefs = state.get("user_preferences", {})
    current_context = json.dumps(user_prefs, ensure_ascii=False)
    print(f"   👤 User Context: {current_context}", flush=True)

    # [1] Hard Filter용 노트 전처리
    user_note = user_prefs.get("note")
    refined_hard_note = None
    if user_note:
        matched_notes = lookup_note_by_string_tool.invoke({"keyword": user_note})
        if matched_notes:
            refined_hard_note = matched_notes[0]
            print(
                f"   🎯 User Note Refined: '{user_note}' -> '{refined_hard_note}'",
                flush=True,
            )

    # [2] 전략 수립 메시지 생성
    messages = [
        SystemMessage(content=RESEARCHER_SYSTEM_PROMPT),
        HumanMessage(
            content=f"사용자 요청 데이터: {current_context}\n위 데이터를 바탕으로 '이미지 강조, 보완, 반전'의 3가지 검색 전략을 세워주세요."
        ),
    ]

    try:
        plan_result = SMART_LLM.with_structured_output(ResearchActionPlan).invoke(
            messages
        )
        final_results = []
        collected_ids = []

        for plan in plan_result.plans:
            print(f"\n   " + "-" * 50, flush=True)
            print(f"   👉 [Strategy {plan.priority}] {plan.strategy_name}", flush=True)

            current_reason = plan.reason
            
            # 리랭킹용 쿼리 텍스트 구성 (기본값)
            search_query_text = (
                f"{current_reason}. Keywords: {', '.join(plan.strategy_keyword)}"
            )

            h_filters = (
                plan.hard_filters.model_dump(exclude_none=True)
                if hasattr(plan.hard_filters, "model_dump")
                else plan.hard_filters.dict(exclude_none=True)
            )

            # [안전장치] 기본 매핑
            if h_filters.get("season") == "봄": h_filters["season"] = "Spring"
            if h_filters.get("gender") == "남성": h_filters["gender"] = "Men"
            if refined_hard_note: h_filters["note"] = refined_hard_note

            # =================================================================
            # [★수정 포인트] Occasion 이원화 전략 (Dual-Track Strategy)
            # =================================================================
            target_occasion = h_filters.get("occasion")
            if target_occasion:
                # DB 메타데이터 로드 (유효성 검사를 위해 필요)
                from .database import fetch_meta_data
                meta = fetch_meta_data()
                
                # DB에 있는 유효한 상황 목록 (소문자 변환하여 비교)
                valid_occasions = [o.strip().lower() for o in meta.get("occasions", "").split(",")]
                
                if target_occasion.lower() in valid_occasions:
                    # Case A: DB에 있는 값 (예: Office, Date) -> Hard Filter 유지
                    print(f"      🔒 Occasion '{target_occasion}' is valid. Keeping Hard Filter.", flush=True)
                else:
                    # Case B: DB에 없는 값 (예: Wedding, Gym) -> Hard Filter 제거 & 쿼리에 추가
                    print(f"      ⚠️ Occasion '{target_occasion}' not in DB. Moving to Query Text.", flush=True)
                    
                    # 1. SQL 조건에서 삭제 (0건 방지)
                    del h_filters["occasion"]
                    
                    # 2. 리뷰 검색어(Query)에 추가하여 리랭킹으로 찾음
                    search_query_text += f". It is perfect for {target_occasion}."
            # =================================================================

            s_filters = (
                plan.strategy_filters.model_dump(exclude_none=True)
                if hasattr(plan.strategy_filters, "model_dump")
                else plan.strategy_filters.dict(exclude_none=True)
            )

            # [3] Strategy Filter용 노트 후보군 추출
            strategy_note_input = s_filters.get("note")
            if strategy_note_input:
                raw_keyword = (
                    strategy_note_input[0]
                    if isinstance(strategy_note_input, list) and strategy_note_input
                    else strategy_note_input
                )

                if raw_keyword:
                    print(
                        f"      🔍 '{raw_keyword}' 기반 노트 후보군 추출 중...",
                        flush=True,
                    )
                    candidates = lookup_note_by_vector_tool.invoke(
                        {"keyword": raw_keyword}
                    )

                    if candidates:
                        print(f"      ➡️ 추출된 후보군: {candidates}", flush=True)
                        selection_messages = [
                            SystemMessage(
                                content=NOTE_SELECTION_PROMPT.format(
                                    candidates=candidates
                                )
                            ),
                            HumanMessage(
                                content=f"현재 전략: {plan.strategy_name}\n의도: {current_reason}"
                            ),
                        ]
                        selected_response = SMART_LLM.invoke(selection_messages).content
                        
                        llm_selected = [
                            c for c in candidates
                            if c.lower() in selected_response.lower()
                        ]

                        s_filters["note"] = (
                            llm_selected if llm_selected else candidates[:1]
                        )
                        print(
                            f"      🎯 LLM 최종 선택 노트: {s_filters['note']}",
                            flush=True,
                        )

            # [4] 검색 수행 (리랭킹 적용)
            db_perfumes, match_type = smart_search_with_retry(
                h_filters,
                s_filters,
                exclude_ids=collected_ids,
                query_text=search_query_text,
            )

            # [5] 검색 실패 시 Re-Act
            if not db_perfumes:
                print(
                    f"      ⚠️ '{plan.strategy_name}' 결과 없음. 재수립 시도...",
                    flush=True,
                )
                retry_messages = [
                    SystemMessage(content=RESEARCHER_SYSTEM_PROMPT),
                    HumanMessage(
                        content=f"사용자 정보: {current_context}\n실패한 필터: {json.dumps(s_filters)}\n전략에 부합하는 새로운 키워드와 사유(Reason)를 제안해줘."
                    ),
                ]
                new_plan = SMART_LLM.with_structured_output(SearchStrategyPlan).invoke(
                    retry_messages
                )

                s_filters = (
                    new_plan.strategy_filters.model_dump(exclude_none=True)
                    if hasattr(new_plan.strategy_filters, "model_dump")
                    else new_plan.strategy_filters.dict(exclude_none=True)
                )
                current_reason = new_plan.reason
                
                # 재시도 시에도 쿼리 업데이트
                search_query_text = f"{current_reason}. Keywords: {', '.join(new_plan.strategy_keyword)}"
                
                # 재시도 시에도 Occasion이 쿼리에 반영되어야 한다면 추가 (선택사항)
                if target_occasion and target_occasion.lower() not in valid_occasions:
                     search_query_text += f". It is perfect for {target_occasion}."

                # 노트 재검색 로직
                if s_filters.get("note"):
                    retry_keyword = (
                        s_filters["note"][0]
                        if isinstance(s_filters["note"], list)
                        else s_filters["note"]
                    )
                    retry_candidates = lookup_note_by_vector_tool.invoke(
                        {"keyword": retry_keyword}
                    )
                    if retry_candidates:
                        s_filters["note"] = retry_candidates[:2]

                db_perfumes, match_type = smart_search_with_retry(
                    h_filters,
                    s_filters,
                    exclude_ids=collected_ids,
                    query_text=search_query_text,
                )

            # [6] 결과 정리
            perfume_details = []
            if db_perfumes:
                p = db_perfumes[0]
                collected_ids.append(p["id"])
                print(
                    f"      ✅ 최종 선정: {p.get('brand')} - {p.get('name')} ({match_type})",
                    flush=True,
                )

                best_review_text = p.get("best_review", "리뷰 정보 없음")
                accord_with_review = f"{p.get('accords') or '정보 없음'}\n[✨ Best Review]: {best_review_text}"

                p_notes = PerfumeNotes(
                    top=p.get("top_notes") or "정보 없음",
                    middle=p.get("middle_notes") or "정보 없음",
                    base=p.get("base_notes") or "정보 없음",
                )
                detail = PerfumeDetail(
                    perfume_name=p.get("name", "Unknown"),
                    perfume_brand=p.get("brand", "Unknown"),
                    accord=accord_with_review,
                    season="All Seasons",
                    occasion="Any",
                    gender=p.get("gender", "Unisex"),
                    notes=p_notes,
                    image_url=p.get("image_url"),
                )
                perfume_details.append(detail)

            final_results.append(
                StrategyResult(
                    strategy_name=plan.strategy_name,
                    strategy_keyword=plan.strategy_keyword,
                    strategy_reason=current_reason,
                    perfumes=perfume_details,
                )
            )

        return {
            "research_results": (
                ResearcherOutput(results=final_results).model_dump()
                if hasattr(ResearcherOutput, "model_dump")
                else ResearcherOutput(results=final_results).dict()
            ),
            "messages": [AIMessage(content="[RESEARCH_DONE]")],
            "next_step": "writer",
        }

    except Exception as e:
        print(f"   -> 🚨 Researcher Node Error: {e}")
        import traceback

        traceback.print_exc()
        return {"research_results": {"results": []}, "next_step": "writer"}


# ==========================================
# 7. Writer노드 정의 (비동기 처리 적용)
# ==========================================


async def writer_node(state: AgentState):
    print(f"\n✍️ [Writer] 최종 답변 작성 중...", flush=True)
    last_message = state["messages"][-1]
    research_data = state.get("research_results", {})
    results_list = research_data.get("results", [])

    if isinstance(last_message, HumanMessage):
        selected_prompt = WRITER_CHAT_PROMPT
        data_context = ""
    elif not results_list or all(len(r["perfumes"]) == 0 for r in results_list):
        selected_prompt = WRITER_FAILURE_PROMPT
        data_context = ""
    else:
        selected_prompt = WRITER_RECOMMENDATION_PROMPT
        data_context = json.dumps(research_data, ensure_ascii=False, indent=2)

    full_content = f"{selected_prompt}\n\n[참고 데이터]:\n{data_context}"
    messages = [SystemMessage(content=full_content)] + state["messages"]

    try:
        # ainvoke를 사용하여 비동기로 호출합니다.
        # astream_events가 이 내부의 스트림을 자동으로 감지합니다.
        response = await SUPER_SMART_LLM.ainvoke(messages)
        return {"messages": [response], "next_step": "end"}
    except Exception:
        return {"next_step": "end"}


# 4. Graph Build
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
