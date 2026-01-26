# backend/agent/graph_info.py
import json
import asyncio
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END

# [1] 스키마 임포트
from .schemas_info import InfoState, InfoRoutingDecision
from .tools_schemas_info import IngredientAnalysisResult

# [2] 도구 임포트
from .tools_info import (
    lookup_perfume_info_tool,
    lookup_note_info_tool,
    lookup_accord_info_tool,
)
from .tools_similarity import lookup_similar_perfumes_tool

# [3] 프롬프트 임포트
from .prompts_info import (
    INFO_SUPERVISOR_PROMPT,
    PERFUME_DESCRIBER_PROMPT_BEGINNER,
    PERFUME_DESCRIBER_PROMPT_EXPERT,
    SIMILARITY_CURATOR_PROMPT_BEGINNER,
    SIMILARITY_CURATOR_PROMPT_EXPERT,
    INGREDIENT_SPECIALIST_PROMPT,
)

load_dotenv()

# [LLM 이원화]
INFO_LLM = ChatOpenAI(model="gpt-4o", temperature=0, streaming=True)
ROUTER_LLM = ChatOpenAI(model="gpt-4o", temperature=0, streaming=False)


# ==========================================
# 4. Node Functions
# ==========================================


def info_supervisor_node(state: InfoState):
    """[Router] 분류 노드"""
    print(f"\n   ▶️ [Info Subgraph] Supervisor 노드 시작", flush=True)
    user_query = state.get("user_query", "")

    chat_history = state.get("messages", [])
    context_str = ""
    if chat_history:
        recent_msgs = chat_history[-3:] if len(chat_history) > 3 else chat_history
        for msg in recent_msgs:
            role = "User" if isinstance(msg, HumanMessage) else "AI"
            if msg.content:
                context_str += f"- {role}: {msg.content}\n"

    final_system_prompt = INFO_SUPERVISOR_PROMPT
    if context_str:
        final_system_prompt += f"\n\n[Recent Chat Context]\n{context_str}"

    final_system_prompt += "\n\n[Instruction]\nResolve the target name from context and classify based on the PRIORITY rules."

    messages = [
        SystemMessage(content=final_system_prompt),
        HumanMessage(content=user_query),
    ]

    try:
        decision = ROUTER_LLM.with_structured_output(InfoRoutingDecision).invoke(
            messages
        )
        final_target = decision.target_name

        if not final_target or final_target in [
            "이거",
            "그거",
            "이 향수",
            "추천해줘",
            "비슷한거",
        ]:
            print(f"      ⚠️ 타겟 해상 실패: '{final_target}' -> Fallback", flush=True)
            return {"info_type": "unknown", "target_name": "unknown"}

        print(
            f"      👉 [Decided] Type: '{decision.info_type}' | Target: '{final_target}'",
            flush=True,
        )

        return {"info_type": decision.info_type, "target_name": final_target}

    except Exception as e:
        print(f"      ❌ Supervisor 에러 발생: {e}", flush=True)
        return {"info_type": "unknown", "target_name": "unknown"}


async def perfume_describer_node(state: InfoState):
    """[Perfume Expert] 상세 정보"""
    target = state["target_name"]

    # [★설정] 사용자 모드 (DB 연동 전 하드코딩: "BEGINNER" or "EXPERT")
    USER_MODE = "BEGINNER"
    try:
        print(f"\n   ▶️ [Info Subgraph] Perfume Describer: '{target}'", flush=True)

        # 1. 도구 호출
        search_result_json = await lookup_perfume_info_tool.ainvoke(target)

        # [★추가] DB에서 실제로 어떤 값이 왔는지 로그를 찍어야 원인 분석이 가능합니다.
        print(f"      🔍 [DB Result]: {str(search_result_json)[:200]}...", flush=True)

        # [★수정] 가드레일 강화: "검색 실패" 뿐만 아니라 "DB 에러"나 "Error"가 포함된 경우도 차단
        is_error = any(
            keyword in search_result_json
            for keyword in ["검색 실패", "찾을 수 없습니다", "DB 에러", "Error"]
        )
        is_empty = (
            not search_result_json
            or search_result_json == "{}"
            or search_result_json == "[]"
        )

        if is_error or is_empty:
            # 에러 메시지를 LLM에게 넘기지 않고 여기서 바로 사과 답변을 반환합니다.
            fail_msg = f"죄송합니다. '{target}'에 대한 상세 정보를 데이터베이스에서 찾을 수 없습니다. 😢"
            return {"messages": [AIMessage(content=fail_msg)], "final_answer": fail_msg}

        if USER_MODE == "EXPERT":
            print("      😎 [Mode] 전문가용 분석 프롬프트 적용")
            selected_prompt = PERFUME_DESCRIBER_PROMPT_EXPERT
        else:
            print("      🐥 [Mode] 비기너용 도슨트 프롬프트 적용")
            selected_prompt = PERFUME_DESCRIBER_PROMPT_BEGINNER

        messages = [
            SystemMessage(content=selected_prompt),
            HumanMessage(
                content=f"대상 향수: {target}\n\n[검색된 상세 정보]:\n{search_result_json}"
            ),
        ]
        response = await INFO_LLM.ainvoke(messages)

        return {"messages": [response], "final_answer": response.content}

    except Exception as e:
        print(f"      ❌ Perfume Describer 에러: {e}", flush=True)
        msg = f"죄송합니다. '{target}' 정보를 불러오는 중 기술적인 오류가 발생했습니다."
        return {"messages": [AIMessage(content=msg)], "final_answer": msg}


async def ingredient_specialist_node(state: InfoState):
    """[Ingredient Expert] 성분 분석"""
    try:
        user_query = state.get("user_query", "")
        target_name = state.get("target_name", "")
        print(
            f"\n   ▶️ [Info Subgraph] Ingredient Specialist: '{user_query}'", flush=True
        )

        # 1. 쿼리 분석 로직 (원래 로직 유지)
        analysis_prompt = f"""
        You are a query analyzer. Separate 'Notes' and 'Accords'.
        Query: "{user_query}"
        Context Target: "{target_name}"
        Output JSON: {{ "notes": [], "accords": [], "is_ambiguous": false }}
        """

        try:
            analysis = await ROUTER_LLM.with_structured_output(
                IngredientAnalysisResult
            ).ainvoke(analysis_prompt, config={"tags": ["internal_helper"]})
            print(
                f"      - 분석 결과: Notes={analysis.notes}, Accords={analysis.accords}",
                flush=True,
            )
        except Exception as e:
            print(f"      ⚠️ 분석 실패: {e}", flush=True)
            analysis = IngredientAnalysisResult(notes=[target_name], accords=[])

        # 2. 병렬 도구 호출 (원래 로직 유지)
        tasks = []
        tasks.append(
            lookup_note_info_tool.ainvoke({"keywords": analysis.notes})
            if analysis.notes
            else asyncio.sleep(0, result="")
        )
        tasks.append(
            lookup_accord_info_tool.ainvoke({"keywords": analysis.accords})
            if analysis.accords
            else asyncio.sleep(0, result="")
        )

        results = await asyncio.gather(*tasks)
        note_result, accord_result = results[0], results[1]

        # 3. 상세 로깅 함수 및 실행 (원래 로직 유지)
        def print_result_log(category: str, result_str: str):
            if not result_str:
                return
            try:
                data = json.loads(result_str)
                if not data:
                    print(f"      🔍 [{category}]: 결과 없음 (Empty)", flush=True)
                    return
                for key, val in data.items():
                    if isinstance(val, dict):
                        perfumes = val.get("representative_perfumes", [])
                        perfume_log = ", ".join(perfumes) if perfumes else "없음"
                        print(
                            f"      🔍 [{category}] '{key}': (대표향수: {perfume_log})",
                            flush=True,
                        )
            except:
                pass

        print_result_log("Note DB", note_result)
        print_result_log("Accord DB", accord_result)

        # =============================================================
        # [★ 할루시네이션 방지: 조기 차단(Early Exit) 가드레일]
        # =============================================================
        # 분석된 노트와 어코드에 대해 DB 검색 결과가 모두 유효하지 않은지 확인합니다.
        # 결과가 없거나("{}"), 검색 실패 메시지가 포함된 경우 LLM 호출을 생략합니다.
        is_note_empty = (
            not note_result or "검색 실패" in note_result or note_result == "{}"
        )
        is_accord_empty = (
            not accord_result or "검색 실패" in accord_result or accord_result == "{}"
        )

        if is_note_empty and is_accord_empty:
            print(
                f"      ⚠️ [Hallucination Guard] 데이터 부재로 LLM 호출을 생략합니다.",
                flush=True,
            )
            fail_msg = f"죄송합니다. 말씀하신 '{user_query}' 성분에 대한 상세 정보가 현재 데이터베이스에 등록되어 있지 않습니다. 😢"
            return {"messages": [AIMessage(content=fail_msg)], "final_answer": fail_msg}
        # =============================================================

        # 4. LLM 기반 답변 생성 (데이터가 있을 때만 실행)
        combined_context = f"""
        [User Interest]: Notes: {analysis.notes}, Accords: {analysis.accords}
        [Search Results]:
        --- Note Data ---
        {note_result}
        --- Accord Data ---
        {accord_result}
        """

        messages = [
            SystemMessage(content=INGREDIENT_SPECIALIST_PROMPT),
            HumanMessage(content=combined_context),
        ]
        response = await INFO_LLM.ainvoke(messages)

        return {"messages": [response], "final_answer": response.content}

    except Exception as e:
        print(f"      ❌ Ingredient Specialist 에러: {e}", flush=True)
        msg = "성분 정보를 분석하는 도중 기술적인 문제가 발생했습니다."
        return {"messages": [AIMessage(content=msg)], "final_answer": msg}


async def similarity_curator_node(state: InfoState):
    """[Similarity Expert] 유사 추천"""

    # [★설정] 사용자 모드
    USER_MODE = "BEGINNER"
    try:
        target = state["target_name"]
        print(f"\n   ▶️ [Info Subgraph] Similarity Curator: '{target}'", flush=True)

        # 1. 도구 호출 (기존 로직 유지)
        search_result_json = await lookup_similar_perfumes_tool.ainvoke(target)
        print(f"      🔍 [DB Result]: {str(search_result_json)[:200]}...", flush=True)

        # =============================================================
        # [★ 할루시네이션 방지: 조기 차단(Early Exit) 가드레일]
        # =============================================================
        # 유사 향수 검색 결과가 없거나 실패 메시지인 경우, LLM 호출을 건너뜁니다.
        # 결과가 "[]"이거나 특정 실패 키워드가 포함되어 있는지 확인합니다.
        is_empty = (
            not search_result_json
            or search_result_json == "[]"
            or "{}" in search_result_json
        )
        is_failed = (
            "검색 실패" in search_result_json or "결과가 없습니다" in search_result_json
        )

        if is_empty or is_failed:
            print(
                f"      ⚠️ [Hallucination Guard] 유사 향수 데이터 부재로 LLM 호출을 생략합니다.",
                flush=True,
            )
            fail_msg = f"현재 저희 데이터베이스에는 '{target}'과 결이 비슷한 향수 정보가 충분하지 않네요. 😅 다른 향수로 다시 찾아봐 드릴까요?"
            return {"messages": [AIMessage(content=fail_msg)], "final_answer": fail_msg}
        # =============================================================
        if USER_MODE == "EXPERT":
            print("      😎 [Mode] 전문가용 큐레이터 프롬프트 적용")
            selected_prompt = SIMILARITY_CURATOR_PROMPT_EXPERT
        else:
            print("      🐥 [Mode] 비기너용 도슨트 프롬프트 적용")
            selected_prompt = SIMILARITY_CURATOR_PROMPT_BEGINNER

        messages = [
            SystemMessage(content=selected_prompt),
            HumanMessage(
                content=f"원본 향수: {target}\n\n[추천 후보군 데이터]:\n{search_result_json}"
            ),
        ]
        response = await INFO_LLM.ainvoke(messages)

        # [★수정] 결과가 화면에 나오도록 final_answer를 포함하여 반환
        return {"messages": [response], "final_answer": response.content}

    except Exception as e:
        # 시스템 에러 처리 (기존 로직 유지)
        print(f"      ❌ Similarity Curator 에러: {e}", flush=True)
        msg = f"죄송합니다. '{target}'과 유사한 향수를 찾는 과정에서 기술적인 문제가 발생했습니다."
        return {"messages": [AIMessage(content=msg)], "final_answer": msg}


async def fallback_handler_node(state: InfoState):
    """[Fallback] 안내"""
    print(f"\n   ⚠️ [Info Subgraph] Fallback Handler 실행", flush=True)
    fallback_msg = "죄송합니다. 말씀하신 향수가 무엇인지 정확히 파악하지 못했어요. 😅\n'샤넬 넘버5랑 비슷한 거 추천해줘' 처럼 향수 이름을 콕 집어서 다시 말씀해 주시겠어요?"

    # [★수정] final_answer 추가
    return {"messages": [AIMessage(content=fallback_msg)], "final_answer": fallback_msg}


# ==========================================
# 5. Graph Build (Info Subgraph)
# ==========================================
info_workflow = StateGraph(InfoState)

info_workflow.add_node("info_supervisor", info_supervisor_node)
info_workflow.add_node("perfume_describer", perfume_describer_node)
info_workflow.add_node("ingredient_specialist", ingredient_specialist_node)
info_workflow.add_node("similarity_curator", similarity_curator_node)
info_workflow.add_node("fallback_handler", fallback_handler_node)

info_workflow.add_edge(START, "info_supervisor")

info_workflow.add_conditional_edges(
    "info_supervisor",
    lambda x: x["info_type"],
    {
        "perfume": "perfume_describer",
        "brand": "perfume_describer",
        "note": "ingredient_specialist",
        "accord": "ingredient_specialist",
        "ingredient": "ingredient_specialist",
        "similarity": "similarity_curator",
        "unknown": "fallback_handler",
    },
)

info_workflow.add_edge("perfume_describer", END)
info_workflow.add_edge("ingredient_specialist", END)
info_workflow.add_edge("similarity_curator", END)
info_workflow.add_edge("fallback_handler", END)

info_graph = info_workflow.compile()
