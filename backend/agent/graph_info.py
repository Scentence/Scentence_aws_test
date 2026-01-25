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

from .tools_info import (
    lookup_perfume_info_tool, 
    lookup_note_info_tool, 
    lookup_accord_info_tool
)
from .prompts_info import (
    INFO_SUPERVISOR_PROMPT,
    PERFUME_DESCRIBER_PROMPT,
    INGREDIENT_SPECIALIST_PROMPT
)

load_dotenv()
INFO_LLM = ChatOpenAI(model="gpt-4o", temperature=0, streaming=True)

# ==========================================
# 4. Node Functions
# ==========================================

def info_supervisor_node(state: InfoState):
    """[Router] 분류 노드"""
    print(f"\n   ▶️ [Info Subgraph] Supervisor 노드 시작", flush=True)
    user_query = state.get('user_query', '')
    
    messages = [
        SystemMessage(content=INFO_SUPERVISOR_PROMPT),
        HumanMessage(content=user_query)
    ]
    
    decision = INFO_LLM.with_structured_output(InfoRoutingDecision).invoke(messages)
    print(f"      - 분류 결과: {decision.info_type} / {decision.target_name}", flush=True)
    
    return {
        "info_type": decision.info_type,
        "target_name": decision.target_name
    }


async def perfume_describer_node(state: InfoState):
    """[Perfume Expert] 특정 향수 상세 정보 설명"""
    target = state["target_name"]
    print(f"\n   ▶️ [Info Subgraph] Perfume Describer: '{target}'", flush=True)
    
    # 1. 도구 실행
    search_result_json = await lookup_perfume_info_tool.ainvoke(target)
    
    # [Log] 검색 결과 출력 (너무 길면 자르되, 핵심 정보 확인용)
    print(f"      🔍 [DB Result]: {str(search_result_json)[:200]}...", flush=True)
    
    # 2. 답변 생성
    messages = [
        SystemMessage(content=PERFUME_DESCRIBER_PROMPT),
        HumanMessage(content=f"대상 향수: {target}\n\n[검색된 상세 정보]:\n{search_result_json}")
    ]
    response = await INFO_LLM.ainvoke(messages)
    return {"messages": [response]}


async def ingredient_specialist_node(state: InfoState):
    """
    [Ingredient Expert] 
    사용자 질문을 분석하여 '노트(원료)'와 '어코드(분위기)'를 분리하고,
    각각 적합한 도구를 병렬로 호출하여 종합적인 답변을 제공합니다.
    """
    user_query = state.get("user_query", "")
    target_name = state.get("target_name", "") 
    
    print(f"\n   ▶️ [Info Subgraph] Ingredient Specialist: '{user_query}'", flush=True)

    # [Step 1] 질문 분석 (화면 출력 방지 태그 적용)
    analysis_prompt = f"""
    You are a query analyzer for a perfume database.
    User Query: "{user_query}"
    Context Target: "{target_name}"
    
    Task:
    Analyze the query and separate the terms into:
    1. 'Notes': Concrete ingredients (e.g., Rose, Musk, Vetiver, Vanilla).
    2. 'Accords': Scent categories/vibes (e.g., Woody, Citrus, Floral, Spicy).
    
    Output JSON (IngredientAnalysisResult):
    {{ "notes": ["..."], "accords": ["..."], "is_ambiguous": false }}
    """
    
    try:
        # 화면에 출력되지 않도록 내부 태그 사용
        analysis = await INFO_LLM.with_structured_output(IngredientAnalysisResult).ainvoke(
            analysis_prompt,
            config={"tags": ["internal_helper"]} 
        )
        print(f"      - 분석 결과: Notes={analysis.notes}, Accords={analysis.accords}", flush=True)
    except Exception as e:
        print(f"      ⚠️ 분석 실패: {e}", flush=True)
        analysis = IngredientAnalysisResult(notes=[target_name], accords=[])

    # [Step 2] 도구 선별 호출 (병렬 처리)
    tasks = []
    
    if analysis.notes:
        tasks.append(lookup_note_info_tool.ainvoke({"keywords": analysis.notes}))
    else:
        async def dummy_note(): return ""
        tasks.append(dummy_note())

    if analysis.accords:
        tasks.append(lookup_accord_info_tool.ainvoke({"keywords": analysis.accords}))
    else:
        async def dummy_accord(): return ""
        tasks.append(dummy_accord())
        
    results = await asyncio.gather(*tasks)
    
    note_result = results[0]
    accord_result = results[1]

    # [★수정] 로그 출력 함수 (대표 향수 리스트를 명확히 출력)
    def print_result_log(category: str, result_str: str):
        if not result_str: return
        try:
            data = json.loads(result_str)
            if not data:
                print(f"      🔍 [{category}]: 결과 없음 (Empty)", flush=True)
                return
            
            for key, val in data.items():
                if isinstance(val, dict):
                    # 대표 향수 리스트 추출
                    perfumes = val.get("representative_perfumes", [])
                    perfume_log = ", ".join(perfumes) if perfumes else "없음"
                    
                    # 설명 일부 추출
                    desc = val.get("description", "")
                    short_desc = desc[:30] + "..." if len(desc) > 30 else desc

                    print(f"      🔍 [{category}] '{key}':", flush=True)
                    print(f"          - 🧴 대표 향수: {perfume_log}", flush=True) # <-- 여기!
                    print(f"          - 📝 설명 요약: {short_desc}", flush=True)
        except:
            # JSON 파싱 실패 시(에러 메시지 등) 원본 출력
            print(f"      🔍 [{category} Raw]: {result_str}", flush=True)

    # 로그 실행
    print_result_log("Note DB", note_result)
    print_result_log("Accord DB", accord_result)
    
    # [Step 3] 답변 생성
    combined_context = f"""
    [User Interest]:
    - Notes: {analysis.notes}
    - Accords: {analysis.accords}
    
    [Search Results]:
    --- Note Data ---
    {note_result}
    
    --- Accord Data ---
    {accord_result}
    
    [Instruction]:
    Explain the characteristics based on the data. 
    If 'Accord Data' is present, define the vibe. 
    If 'Note Data' has descriptions like 'Woody(비 온 뒤 숲속...)', emphasize those rich details.
    """
    
    messages = [
        SystemMessage(content=INGREDIENT_SPECIALIST_PROMPT),
        HumanMessage(content=combined_context)
    ]
    response = await INFO_LLM.ainvoke(messages)
    
    return {"messages": [response]}


# ==========================================
# 5. Graph Build (Info Subgraph)
# ==========================================
info_workflow = StateGraph(InfoState)

# 노드 등록
info_workflow.add_node("info_supervisor", info_supervisor_node)
info_workflow.add_node("perfume_describer", perfume_describer_node)
info_workflow.add_node("ingredient_specialist", ingredient_specialist_node) 

# 엣지 연결
info_workflow.add_edge(START, "info_supervisor")

# 라우팅 조건
info_workflow.add_conditional_edges(
    "info_supervisor",
    lambda x: x["info_type"],
    {
        "perfume": "perfume_describer",
        "brand": "perfume_describer",      
        "note": "ingredient_specialist",   
        "accord": "ingredient_specialist", 
        "ingredient": "ingredient_specialist",
        "unknown": END 
    }
)

# 종료 엣지
info_workflow.add_edge("perfume_describer", END)
info_workflow.add_edge("ingredient_specialist", END)

# 컴파일
info_graph = info_workflow.compile()