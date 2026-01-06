# ### 1. 환경 설정
from typing import Dict, Any
from pydantic import BaseModel, Field
from fastmcp import FastMCP
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# API Key 가져오기(.env 파일에서)
# .env 파일에 OPENAI_API_KEY=your_api_key 형식으로 저장해두세요.
file_path = '.env'
load_dotenv(file_path)


# 서버 및 LLM 설정 

# 서버 설정 (의료 보고서 작성 전문가로 변경)
mcp_server = FastMCP(name="MedicalReportWriter")

# LLM 설정 (정확성을 위해 temperature를 낮게 설정)
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)


# 전문가 도구 함수 정의

# 입력 스키마 정의
class MedicalReportInput(BaseModel):
    user_query: str = Field(description="정보 요청을 위한 사용자의 원본 검색어 (예: '고혈압이란 무엇인가요?')")
    research_summary: str = Field(description="MedicalInfoExpert로부터 전달받은 원본 의료 정보 요약")

# 전문가 도구 함수 정의
@mcp_server.tool(
    name="write_final_medical_report",
    description="사용자의 원본 질문과 검색된 의료 정보 요약을 바탕으로, 체계적이고 이해하기 쉬운 최종 의료 정보 보고서를 마크다운 형식으로 생성합니다."
)
def write_final_medical_report(input_data: MedicalReportInput) -> Dict[str, Any]:
    """
    LLM을 사용하여 의료 정보와 사용자 의도를 종합한 최종 보고서를 작성하는 전문가 도구.
    """
    print("--- [MedicalReportWriter] 최종 의료 정보 보고서 작성을 시작합니다. ---")
    
    # 프롬프트: 의료 정보 전문가 역할과 명확한 구조 지시
    prompt = f"""
    당신은 일반인을 위해 의료 정보를 알기 쉽게 설명하는 의료 정보 전문가입니다.
    아래는 사용자의 원본 질문과 그에 따라 수집된 의료 정보 요약입니다.

    이 정보를 바탕으로, 사용자가 자신의 상태를 이해하고 다음에 취해야 할 행동을 파악하는 데 도움이 되도록,
    아래 '보고서 형식'에 맞춰 명확하고 체계적인 최종 의료 정보 보고서를 작성해주세요.

    # 원본 사용자 질문:
    {input_data.user_query}

    # 수집된 의료 정보 요약:
    {input_data.research_summary}

    # 지침:
    1. 전문 용어는 최대한 쉽게 풀어서 설명하세요.
    2. 각 항목은 명확하게 구분하고, 중요한 내용은 강조(예: **굵은 글씨**)해주세요.
    3. 반드시 가장 처음에 "이 정보는 의사의 진료를 대체할 수 없으며, 참고용으로만 활용해야 합니다"라는 면책 조항을 포함하세요.

    # 최종 보고서 형식 (마크다운):

    ### '{input_data.user_query}' 관련 정보 요약

    **매우 중요한 안내:** 이 정보는 일반적인 참고용이며, 의사의 진료를 대체할 수 없습니다. 정확한 진단과 치료는 반드시 전문의와 상담하세요.

    ---
    #### 1. 개요 (이것이 무엇인가요?)
    - [이 질병이나 증상에 대한 쉬운 설명]

    #### 2. 주요 원인
    - [어떤 이유로 발생하는가?]

    #### 3. 대표적인 증상
    - [나타날 수 있는 증상들]

    #### 4. 진단 및 검사
    - [병원에서 어떻게 확인하는가?]

    #### 5. 치료 및 관리 방법
    - [주요 치료법과 일상생활에서의 관리법]

    #### 6. 예방 및 생활 수칙
    - [예방을 위해 실천하면 좋은 것들]

    #### 7. 이럴 땐 꼭 병원에 가세요!
    - [즉시 의사의 진료가 필요한 위험 신호]

    ####  참고 자료
    - [주요 정보 출처]

    ---
    """
    try:
        response = llm.invoke(prompt)
        report_text = response.content
        return {"result": {"report_text": report_text}}
    except Exception as e:
        error_message = f"의료 보고서 생성 중 LLM 호출 오류 발생: {e}"
        print(f"[ERROR] {error_message}")
        return {"error": error_message}


# 서버 실행
if __name__ == "__main__":
    print("MCP [MedicalReportWriter] 서버가 시작되었습니다.")
    mcp_server.run()

