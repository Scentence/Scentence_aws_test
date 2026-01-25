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
    lookup_accord_info_tool
)
from .tools_similarity import lookup_similar_perfumes_tool  

# [3] 프롬프트 임포트
from .prompts_info import (
    INFO_SUPERVISOR_PROMPT,
    PERFUME_DESCRIBER_PROMPT,
    INGREDIENT_SPECIALIST_PROMPT,
    SIMILARITY_CURATOR_PROMPT
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
    user_query = state.get('user_query', '')
    
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
        HumanMessage(content=user_query)
    ]
    
    try:
        decision = ROUTER_LLM.with_structured_output(InfoRoutingDecision).invoke(messages)
        final_target = decision.target_name
        
        if not final_target or final_target in ["이거", "그거", "이 향수", "추천해줘", "비슷한거"]:
             print(f"      ⚠️ 타겟 해상 실패: '{final_target}' -> Fallback", flush=True)
             return {"info_type": "unknown", "target_name": "unknown"}

        print(f"      👉 [Decided] Type: '{decision.info_type}' | Target: '{final_target}'", flush=True)
        
        return {
            "info_type": decision.info_type,
            "target_name": final_target
        }
        
    except Exception as e:
        print(f"      ❌ Supervisor 에러 발생: {e}", flush=True)
        return {"info_type": "unknown", "target_name": "unknown"}


async def perfume_describer_node(state: InfoState):
    """[Perfume Expert] 상세 정보"""
    try:
        target = state["target_name"]
        print(f"\n   ▶️ [Info Subgraph] Perfume Describer: '{target}'", flush=True)
        
        search_result_json = await lookup_perfume_info_tool.ainvoke(target)
        print(f"      🔍 [DB Result]: {str(search_result_json)[:200]}...", flush=True)
        
        messages = [
            SystemMessage(content=PERFUME_DESCRIBER_PROMPT),
            HumanMessage(content=f"대상 향수: {target}\n\n[검색된 상세 정보]:\n{search_result_json}")
        ]
        response = await INFO_LLM.ainvoke(messages)
        
        # [★수정] final_answer에 response.content를 담아서 반환해야 화면에 나옵니다!
        return {
            "messages": [response], 
            "final_answer": response.content
        }
        
    except Exception as e:
        print(f"      ❌ Perfume Describer 에러: {e}", flush=True)
        msg = f"죄송합니다. '{target}' 정보를 불러오는 중 오류가 발생했습니다."
        return {"messages": [AIMessage(content=msg)], "final_answer": msg}


async def ingredient_specialist_node(state: InfoState):
    """[Ingredient Expert] 성분 분석"""
    try:
        user_query = state.get("user_query", "")
        target_name = state.get("target_name", "") 
        print(f"\n   ▶️ [Info Subgraph] Ingredient Specialist: '{user_query}'", flush=True)

        analysis_prompt = f"""
        You are a query analyzer. Separate 'Notes' and 'Accords'.
        Query: "{user_query}"
        Context Target: "{target_name}"
        Output JSON: {{ "notes": [], "accords": [], "is_ambiguous": false }}
        """
        
        try:
            analysis = await ROUTER_LLM.with_structured_output(IngredientAnalysisResult).ainvoke(
                analysis_prompt,
                config={"tags": ["internal_helper"]} 
            )
            print(f"      - 분석 결과: Notes={analysis.notes}, Accords={analysis.accords}", flush=True)
        except Exception as e:
            print(f"      ⚠️ 분석 실패: {e}", flush=True)
            analysis = IngredientAnalysisResult(notes=[target_name], accords=[])

        tasks = []
        tasks.append(lookup_note_info_tool.ainvoke({"keywords": analysis.notes}) if analysis.notes else asyncio.sleep(0, result=""))
        tasks.append(lookup_accord_info_tool.ainvoke({"keywords": analysis.accords}) if analysis.accords else asyncio.sleep(0, result=""))
        
        results = await asyncio.gather(*tasks)
        note_result, accord_result = results[0], results[1]

        def print_result_log(category: str, result_str: str):
            if not result_str: return
            try:
                data = json.loads(result_str)
                if not data:
                    print(f"      🔍 [{category}]: 결과 없음 (Empty)", flush=True)
                    return
                for key, val in data.items():
                    if isinstance(val, dict):
                        perfumes = val.get("representative_perfumes", [])
                        perfume_log = ", ".join(perfumes) if perfumes else "없음"
                        print(f"      🔍 [{category}] '{key}': (대표향수: {perfume_log})", flush=True)
            except: pass

        print_result_log("Note DB", note_result)
        print_result_log("Accord DB", accord_result)
        
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
            HumanMessage(content=combined_context)
        ]
        response = await INFO_LLM.ainvoke(messages)
        
        # [★수정] final_answer 추가
        return {
            "messages": [response], 
            "final_answer": response.content
        }
        
    except Exception as e:
        print(f"      ❌ Ingredient Specialist 에러: {e}", flush=True)
        msg = "성분 정보를 분석하는 도중 문제가 발생했습니다."
        return {"messages": [AIMessage(content=msg)], "final_answer": msg}


async def similarity_curator_node(state: InfoState):
    """[Similarity Curator] 유사 향수 추천"""
    try:
        target = state["target_name"]
        print(f"\n   ▶️ [Info Subgraph] Similarity Curator: '{target}'", flush=True)
        
        # 1. 도구 실행
        similarity_result_json = await lookup_similar_perfumes_tool.ainvoke(target)
        print(f"      🔍 [Similarity Result]: {str(similarity_result_json)[:200]}...", flush=True)
        
        # 2. 답변 생성
        messages = [
            SystemMessage(content=SIMILARITY_CURATOR_PROMPT),
            HumanMessage(content=f"기준 향수: {target}\n\n[유사도 분석 결과]:\n{similarity_result_json}")
        ]
        response = await INFO_LLM.ainvoke(messages)
        
        # [★수정] final_answer 추가
        return {
            "messages": [response], 
            "final_answer": response.content
        }
        
    except Exception as e:
        print(f"      ❌ Similarity Curator 에러: {e}", flush=True)
        msg = f"죄송합니다. '{target}'와 유사한 향수를 찾는 과정에서 답변이 너무 길어져 중단되었습니다."
        return {"messages": [AIMessage(content=msg)], "final_answer": msg}


async def fallback_handler_node(state: InfoState):
    """[Fallback] 안내"""
    print(f"\n   ⚠️ [Info Subgraph] Fallback Handler 실행", flush=True)
    fallback_msg = "죄송합니다. 말씀하신 향수가 무엇인지 정확히 파악하지 못했어요. 😅\n'샤넬 넘버5랑 비슷한 거 추천해줘' 처럼 향수 이름을 콕 집어서 다시 말씀해 주시겠어요?"
    
    # [★수정] final_answer 추가
    return {
        "messages": [AIMessage(content=fallback_msg)], 
        "final_answer": fallback_msg
    }


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
        "unknown": "fallback_handler"
    }
)

info_workflow.add_edge("perfume_describer", END)
info_workflow.add_edge("ingredient_specialist", END)
info_workflow.add_edge("similarity_curator", END)
info_workflow.add_edge("fallback_handler", END)

info_graph = info_workflow.compile()