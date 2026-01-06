# ### 1. 환경 설정

# 필요한 라이브러리 / 모듈 / 함수 임포트 
import os
import sys
import json
import asyncio
from typing import Annotated, List, Dict, Any
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from functools import partial
import uuid

# 실행 파일 폴더 경로 가져오기
folder_path = os.path.dirname(os.path.abspath(__file__))

# OpenAI API Key 가져오기
env_file_path=os.path.join(folder_path, '.env')
load_dotenv(env_file_path)

# 파이썬 실행 환경 가져오기
python_command = sys.executable


# LangGraph 상태 정의 
class OrchestratorState(BaseModel):
    messages: Annotated[List[BaseMessage], add_messages]
    medical_summary: str | None = Field(default=None, description="의료 정보 검색 결과를 저장하는 필드")
    user_query: str | None = Field(default=None, description="사용자의 원본 질문을 저장하는 필드")
    next_node: str = Field(default="", description="다음에 실행할 노드를 지정")


# 에이전트(노드 함수) 역할 정의
async def supervisor_node(state: OrchestratorState) -> Dict[str, Any]:
    """전체 작업 흐름을 시작하고, 다음 단계를 결정하는 감독관 노드"""
    print("\n[Node: Supervisor] 감독관이 작업을 검토합니다.")
    # 새 작업 시작 시, 상태 초기화 및 원본 질문 저장
    if isinstance(state.messages[-1], HumanMessage):
        print("새로운 요청을 감지했습니다. 의료 정보 전문가를 호출합니다.")
        return {
            "medical_summary": None, 
            "user_query": state.messages[-1].content,
            "next_node": "call_medical_info"
        }
    else:
        # 보고서 작성 완료 후, 최종 종료 결정
        print("모든 작업이 완료되었습니다. 프로세스를 종료합니다.")
        return {"next_node": "end"}


async def medical_info_node(state: OrchestratorState, tool_map: Dict) -> Dict[str, Any]:
    """의료 정보 검색 전문가(서버)를 호출하는 노드"""
    print("[Node: Medical Info] 의료 정보 전문가에게 업무를 요청합니다...")
    # MedicalInfoExpert의 툴 이름으로 변경
    info_tool = tool_map["search_and_summarize_medical_info"]
    tool_input = {"input_data": {"topic": state.user_query}}
    
    # 도구 실행
    response_str = await info_tool.ainvoke(tool_input)

    # 도구 실행의 결과 값(JSON 문자열) -> 파이썬 딕셔너리로 변환
    try:
        response_data = json.loads(response_str)
    except json.JSONDecodeError:
        error_msg = "서버로부터 유효하지 않은 응답을 받았습니다."
        print(f"  - [CRITICAL] {error_msg}, 응답 내용: {response_str[:200]}...") 
        return {"messages": [AIMessage(content=f"시스템 오류: {error_msg}")], "next_node": "end"}
    
    # 도구 실행의 결과 값 -> 요약 정보 추출
    # MCP의 반환 필드명에 맞게 'medical_summary'로 변경
    if "result" in response_data:
        summary = response_data["result"]["medical_summary"]
        print("의료 정보 검색을 완료하고 요약 정보를 수신했습니다.")
        return {"medical_summary": summary, "next_node": "call_medical_report"}
    else:
        error_msg = response_data.get("error", "알 수 없는 오류")
        print(f"   - 의료 정보 검색 중 오류 발생: {error_msg}")
        return {"messages": [AIMessage(content=f"의료 정보 검색 실패: {error_msg}")], "next_node": "end"}


async def medical_report_node(state: OrchestratorState, tool_map: Dict) -> Dict[str, Any]:
    """의료 보고서 작성 전문가(서버)를 호출하는 노드"""
    print("[Node: Medical Report] 의료 보고서 작성 전문가에게 업무를 요청합니다...")
    # MedicalReportWriter의 툴 이름으로 변경
    report_tool = tool_map["write_final_medical_report"]
    tool_input = {
        "input_data": {
            "user_query": state.user_query,
            # 상태 필드명에 맞게 'medical_summary'를 전달
            "research_summary": state.medical_summary 
        }
    }

    # 도구 실행
    response_str = await report_tool.ainvoke(tool_input)

    # 도구 실행의 결과 값(JSON 문자열) -> 파이썬 딕셔너리로 변환
    try:
        response_data = json.loads(response_str)
    except json.JSONDecodeError:
        error_msg = "서버로부터 유효하지 않은 응답을 받았습니다."
        print(f"  - [CRITICAL] {error_msg}, 응답 내용: {response_str[:200]}...") 
        return {"messages": [AIMessage(content=f"시스템 오류: {error_msg}")], "next_node": "end"}
     
    # 도구 실행의 결과 값 -> 최종 보고서 추출
    # MCP의 반환 필드명에 맞게 'report_text'로 변경
    if "result" in response_data:
        report = response_data["result"]["report_text"]
        print("최종 의료 정보 보고서 작성을 완료했습니다.")
        return {"messages": [AIMessage(content=report)], "next_node": "supervisor"}
    else:
        error_msg = response_data.get("error", "알 수 없는 오류")
        print(f"의료 보고서 작성 중 오류 발생: {error_msg}")
        return {"messages": [AIMessage(content=f"의료 보고서 작성 실패: {error_msg}")], "next_node": "end"}


# 그래프 라우터 함수 정의 
def router(state: OrchestratorState) -> str:
    """state의 next_node 값을 읽어 다음 노드를 결정하는 라우터"""
    print(f"[Routing] 다음 목적지: {state.next_node}")
    if state.next_node == "end":
        return END
    return state.next_node


# 메인 함수 정의
async def main():
    # 1. 대화 기록을 저장할 DB 파일 설정
    db_file = os.path.join(folder_path, "medical_agent.sqlite")

    # 2. AsyncSqliteSaver를 async with 구문을 사용하여 DB 연결을 안전하게 관리
    async with AsyncSqliteSaver.from_conn_string(db_file) as memory:
        # 클라이언트 생성: MCP 서버 파일명과 키 변경
        client = MultiServerMCPClient({
            # MedicalInfoExpert 서버 연결
            "MedicalInfoExpert": {
                "command": python_command, 
                "args": [os.path.join(folder_path, "research_server.py")],  # <-- 파일명 변경
                "transport": "stdio"
                },
            # MedicalReportWriter 서버 연결
            "MedicalReportWriter": {
                "command": python_command, 
                "args": [os.path.join(folder_path, "report_server.py")],  # <-- 파일명 변경
                "transport": "stdio"
                }
        })
        
        # 도구 함수 목록 생성    
        tools = await client.get_tools()
        print(f"\n--- MCP 서버로부터 {len(tools)}개의 전문가 도구 로드 완료 ---")

        # 도구 함수 목록 -> 딕셔너리 생성
        tool_map = {tool.name: tool for tool in tools}    

        # 그래프 생성
        graph = StateGraph(OrchestratorState)

        # 그래프: 노드 추가 (함수명 변경)
        graph.add_node("supervisor", supervisor_node)
        graph.add_node("call_medical_info", partial(medical_info_node, tool_map=tool_map))  # <-- 노드명 및 함수명 변경
        graph.add_node("call_medical_report", partial(medical_report_node, tool_map=tool_map)) # <-- 노드명 및 함수명 변경
        
        # 그래프: 시작점 설정
        graph.set_entry_point("supervisor")

        # 그래프: 에지 설정
        graph.add_conditional_edges("supervisor", router)
        graph.add_conditional_edges("call_medical_info", router)
        graph.add_conditional_edges("call_medical_report", router)
        
        # 그래프 컴파일 + 체크포인터 설정(그래프와 연결)
        agent_executor = graph.compile(checkpointer=memory)
        
        print("\n--- AI 의료 정보 안내 시스템 ---")

        # 고유한 대화 ID를 사용하여 여러 사용자 또는 대화를 관리할 수 있음
        thread_id=str(uuid.uuid4())
        config = {"configurable": {"thread_id":thread_id}}
        print(f"대화 ID: {thread_id[:8]}")
        print("안녕하세요! 저는 당신의 건강 정보 AI 파트너입니다.")
        print("궁금한 질병이나 증상에 대해 말씀해주세요. (종료: exit, quit, 그만)")

        # 그래프 실행
        while True:            

            # 사용자 입력 설정
            user_input = input("사용자: ")
            if user_input.lower() in ["exit", "quit", "그만"]: 
                break            
            
            try:
                # 최초 상태 설정
                initial_state = {"messages": [HumanMessage(content=user_input)]}
                # 최종 결과 생성
                final_state = await agent_executor.ainvoke(initial_state, config=config)
                # 최종 결과 값(최종 보고서) 추출
                final_answer = final_state["messages"][-1].content
                
                # 최종 결과 값 출력
                if final_answer:
                    print(f"\nAI: {final_answer}")
                else:
                    print("\nAI: 죄송합니다. 작업을 완료하지 못했습니다.")                    

            except Exception as e:
                print(f"\n[CRITICAL] 시스템 실행 중 심각한 오류가 발생했습니다: {e}")

# 애플리케이션 실행
if __name__ == "__main__":
    asyncio.run(main())
