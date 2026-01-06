# Medical Information AI System

MCP(Model Context Protocol)와 LangGraph를 활용한 멀티 에이전트 기반 의료 정보 안내 시스템입니다. 사용자의 질병 및 증상 관련 질문에 대해 신뢰할 수 있는 정보를 검색하고, 이해하기 쉬운 형태의 의료 정보 보고서를 자동으로 생성합니다.

## Project Overview

이 프로젝트는 3개의 독립적인 컴포넌트로 구성된 멀티 에이전트 아키텍처를 사용합니다:

- **Orchestrator**: LangGraph 기반 워크플로우 관리 및 에이전트 조율
- **Research Server**: Tavily API를 활용한 의료 정보 검색 및 요약
- **Report Server**: OpenAI GPT를 활용한 구조화된 의료 보고서 생성

## Architecture

```
User Input
    |
    v
medical_orchestrator.py (LangGraph Workflow)
    |
    +---> research_server.py (MCP Server: MedicalInfoExpert)
    |         |
    |         +---> Tavily Search API
    |         |
    |         +---> Medical Information Summary
    |
    +---> report_server.py (MCP Server: MedicalReportWriter)
              |
              +---> OpenAI GPT-4o-mini
              |
              +---> Structured Medical Report
    |
    v
Final Medical Report (Markdown Format)
```

## Files Description

### 1. medical_orchestrator.py
메인 애플리케이션으로, 전체 시스템의 워크플로우를 관리합니다.

**주요 기능:**
- LangGraph를 사용한 상태 기반 워크플로우 구현
- 3개의 노드로 구성된 실행 그래프 (supervisor, call_medical_info, call_medical_report)
- MultiServerMCPClient를 통한 2개의 MCP 서버 연결 및 관리
- AsyncSqliteSaver를 사용한 대화 히스토리 저장
- CLI 기반 대화형 인터페이스 제공

**핵심 컴포넌트:**
- `OrchestratorState`: 시스템 상태 관리 (메시지, 의료 요약, 사용자 질문, 다음 노드)
- `supervisor_node`: 작업 흐름 제어 및 다음 단계 결정
- `medical_info_node`: 의료 정보 검색 전문가 호출
- `medical_report_node`: 의료 보고서 작성 전문가 호출
- `router`: 상태 기반 라우팅 함수

### 2. research_server.py
의료 정보 검색 및 요약을 담당하는 MCP 서버입니다.

**주요 기능:**
- MCP 서버명: `MedicalInfoExpert`
- Tavily Search API를 활용한 웹 검색
- 질병관리청 등 신뢰도 높은 소스 우선 검색
- 검색 결과 전처리 및 구조화된 요약 생성

**제공 도구:**
- `search_and_summarize_medical_info`: 의료 주제에 대한 검색 및 요약 수행

**입력/출력:**
- Input: `topic` (검색할 질병, 증상, 의료 주제)
- Output: `medical_summary` (구조화된 의료 정보 요약)

### 3. report_server.py
최종 의료 정보 보고서 생성을 담당하는 MCP 서버입니다.

**주요 기능:**
- MCP 서버명: `MedicalReportWriter`
- OpenAI GPT-4o-mini를 활용한 보고서 생성
- 마크다운 형식의 7개 섹션 구조화된 보고서 작성
  1. 개요
  2. 주요 원인
  3. 대표적인 증상
  4. 진단 및 검사
  5. 치료 및 관리 방법
  6. 예방 및 생활 수칙
  7. 위험 신호 및 병원 방문 권고

**제공 도구:**
- `write_final_medical_report`: 의료 정보를 바탕으로 최종 보고서 작성

**입력/출력:**
- Input: `user_query` (사용자 원본 질문), `research_summary` (의료 정보 요약)
- Output: `report_text` (마크다운 형식 최종 보고서)

## Installation

### 1. 패키지 설치

```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정

프로젝트 루트 디렉토리에 `.env` 파일을 생성하고 다음 API 키를 설정하세요:

```env
OPENAI_API_KEY=your_openai_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
```

**API 키 발급:**
- OpenAI API Key: https://platform.openai.com/api-keys
- Tavily API Key: https://tavily.com/

## Usage

### 기본 실행

```bash
python medical_orchestrator.py
```

### 사용 예시

```
--- AI 의료 정보 안내 시스템 ---
대화 ID: 12345678
안녕하세요! 저는 당신의 건강 정보 AI 파트너입니다.
궁금한 질병이나 증상에 대해 말씀해주세요. (종료: exit, quit, 그만)

사용자: 고혈압이란 무엇인가요?

[Node: Supervisor] 감독관이 작업을 검토합니다.
새로운 요청을 감지했습니다. 의료 정보 전문가를 호출합니다.
[Routing] 다음 목적지: call_medical_info

[Node: Medical Info] 의료 정보 전문가에게 업무를 요청합니다...
--- [MedicalInfoExpert] 주제 '고혈압이란 무엇인가요?'에 대한 정보 검색을 시작합니다. ---
의료 정보 검색을 완료하고 요약 정보를 수신했습니다.
[Routing] 다음 목적지: call_medical_report

[Node: Medical Report] 의료 보고서 작성 전문가에게 업무를 요청합니다...
--- [MedicalReportWriter] 최종 의료 정보 보고서 작성을 시작합니다. ---
최종 의료 정보 보고서 작성을 완료했습니다.
[Routing] 다음 목적지: supervisor

[Node: Supervisor] 감독관이 작업을 검토합니다.
모든 작업이 완료되었습니다. 프로세스를 종료합니다.
[Routing] 다음 목적지: end

AI: [구조화된 마크다운 형식의 의료 정보 보고서 출력]
```

### 종료

다음 명령어 중 하나를 입력하여 프로그램을 종료할 수 있습니다:
- `exit`
- `quit`
- `그만`

## Features

- **멀티 에이전트 아키텍처**: MCP를 활용한 독립적이고 전문화된 에이전트 구성
- **상태 관리**: LangGraph를 통한 명확한 워크플로우 및 상태 관리
- **대화 히스토리**: SQLite 기반 대화 기록 저장 및 관리
- **신뢰성 있는 정보**: 질병관리청 등 공신력 있는 소스 우선 검색
- **구조화된 보고서**: 7개 섹션으로 구성된 체계적인 의료 정보 제공
- **안전성**: 모든 보고서에 의료 면책 조항 포함

## Important Notice

이 시스템이 제공하는 정보는 일반적인 참고용이며, 의사의 진료를 대체할 수 없습니다. 정확한 진단과 치료는 반드시 전문의와 상담하세요.

## Dependencies

주요 라이브러리:
- `langgraph`: 상태 그래프 기반 워크플로우 관리
- `langchain-mcp-adapters`: MCP 서버 연결 및 통신
- `fastmcp`: MCP 서버 프레임워크
- `langchain-tavily`: Tavily 검색 API 통합
- `langchain-openai`: OpenAI LLM 통합
- `pydantic`: 데이터 검증 및 스키마 관리

전체 의존성 목록은 `requirements.txt`를 참조하세요.

## Technical Stack

- **Language**: Python 3.10+
- **Framework**: LangGraph, FastMCP
- **LLM**: OpenAI GPT-4o-mini
- **Search API**: Tavily Search
- **Database**: SQLite (aiosqlite)
- **Protocol**: Model Context Protocol (MCP)

## License

This project is for educational and reference purposes only.
