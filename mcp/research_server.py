# ### 1. 환경 설정
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from fastmcp import FastMCP
from dotenv import load_dotenv
from langchain_tavily import TavilySearch

# Tavily API Key 가져오기(.env 파일에서)
# .env 파일에 TAVILY_API_KEY=your_api_key 형식으로 저장해두세요.
file_path = '.env'
load_dotenv(file_path)

# 서버 및 도구 설정

# 서버 설정 (의료 정보 전문가로 변경)
mcp_server = FastMCP(name="MedicalInfoExpert")

# Tavily 검색 도구 설정 (최대 3개 결과)
tavily_tool = TavilySearch(max_results=3)


# 전문가 도구 함수 정의

# 입력 스키마 정의 (의료 주제로 변경)
class MedicalInput(BaseModel):
    topic: str = Field(description="검색할 질병, 증상, 또는 의료 주제")

# 전문가 도구 함수 정의 (의료 정보 검색 및 요약으로 변경)
@mcp_server.tool(
    name="search_and_summarize_medical_info",
    description="주어진 의료 주제에 대해 신뢰할 수 있는 웹 소스를 검색하고, 핵심 정보를 요약하여 반환합니다."
)
def search_and_summarize_medical_info(input_data: MedicalInput) -> Dict[str, Any]:
    """
    Tavily 검색을 사용하여 의료 정보를 수집하고, 이해하기 쉽게 요약하여 반환하는 전문가 도구.
    """
    print(f"--- [MedicalInfoExpert] 주제 '{input_data.topic}'에 대한 정보 검색을 시작합니다. ---")
    try:
        # 웹 검색 실행 (검색어에 '질병관리청', '정의' 등을 추가해 신뢰도 높은 결과 유도)
        search_query = f"{input_data.topic} 질병관리청 정의 원인 증상 치료"
        tool_output = tavily_tool.invoke(search_query)        

        # ======================= 수집된 데이터 전처리 및 요약 =======================
        # 딕셔너리(tool_output)에서 필요한 정보(제목, 내용, URL)만 추출하여 가공
        processed_content = []
        for res in tool_output.get("results", []):
            # 각 검색 결과를 명확히 구분하기 위해 제목과 내용을 함께 포함
            processed_content.append(
                f"제목: {res.get('title', '제목 없음')}\n"
                f"내용: {res.get('content', '내용 없음')}\n"
                f"출처: {res.get('url', 'URL 없음')}"
            )
        
        # 가공된 텍스트를 하나의 문자열로 병합
        raw_summary_text = "\n\n---\n\n".join(processed_content)
        # ============================================================================

        # (선택 사항) 여기서 LLM을 사용하여 raw_summary_text를 구조화된 요약본으로 만들 수 있음
        # 현재는 검색 결과들을 깔끔하게 정리해서 반환
        final_summary = (
            f"의료 정보 요약 ('{input_data.topic}')\n\n"
            f"**중요 안내:** 이 정보는 일반적인 참고용이며, 의사의 진료를 대체할 수 없습니다. "
            f"정확한 진단과 치료는 반드시 전문의와 상담하세요.\n\n"
            f"--- 아래는 검색된 주요 정보 요약입니다 ---\n\n"
            f"{raw_summary_text}"
        )
        # ============================================================================

        # 정해진 프로토콜에 따라 결과 반환
        return {
            "result": {
                "medical_summary": final_summary
            }
        }
    except Exception as e:
        error_message = f"의료 정보 검색 및 요약 중 오류 발생: {e}"
        print(f"[ERROR] {error_message}")
        return {"error": error_message}


# 서버 실행 
if __name__ == "__main__":
    print("MCP [MedicalInfoExpert] 서버가 시작되었습니다.")
    mcp_server.run()
