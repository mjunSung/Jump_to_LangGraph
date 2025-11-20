# LangGraph 학습 프로젝트

LangGraph를 활용한 챗봇 및 라우팅 시스템 구현 실습

## 구현 내용

### 1. 기본 챗봇
- StateGraph로 간단한 대화형 봇 구현
- GPT-4o-mini 모델 사용

### 2. 메모리 챗봇
- MemorySaver로 대화 기록 유지
- Thread ID로 세션 관리
- 이전 대화 내용 기억 가능

### 3. 의료 상담 시스템
- 전문 용어로 답변 생성 → 일반인용 쉬운 설명으로 변환
- 2단계 파이프라인 (generate_answer → explain_answer)

### 4. 뉴스 라우터
- 사용자 질문 분석 → 도메인(의료/경제) 자동 선택
- 도메인별 뉴스 검색 후 전문가 답변 생성
- 데이터: 의협신문, 네이버 경제뉴스

## 기술 스택
- LangChain, LangGraph
- OpenAI GPT-4o-mini
- WebBaseLoader, InMemoryVectorStore

## 주요 개념
- **StateGraph**: 상태 기반 워크플로우
- **Checkpoint**: 대화 기록 저장
- **Conditional Edges**: 조건부 라우팅
- **RAG**: 벡터 검색 + 생성
