# APE Core 코드 정리 지침

## 개요

이 문서는 APE Core(백엔드 서버) 코드베이스의 정리 및 개선 지침을 제공합니다. 모든 개발자는 이 지침을 따라 코드 일관성과 유지보수성을 향상시켜야 합니다.

## 불필요한 코드 제거

### 1. 중복 코드 제거

- `src/agents/rag_agent.py`의 `_simulate_document_search` 메서드(줄 597-646) 제거
- 임베딩 테스트용 하드코딩된 벡터 코드(줄 109-111, 156-158) 정리
- 중복된 로깅 코드 통합 (try-except 블록 내 중복 로깅 등)

### 2. 레거시 코드 정리

- `config.py`의 SWDP, Jira, Bitbucket, Pocket 관련 설정 블록 제거
- 불필요한 임시 API 키와 URL 하드코딩 값 제거

### 3. 디버깅용 코드 정리

- 과도한 로깅 간소화 (줄 159-164, 176-180, 332-333 등)
- 테스트용 코드와 주석 처리된 미사용 코드 제거

## 코드 구조 개선

### 1. 모듈화 강화

- **agent 모듈**: 독립적인 AI agent 구현
- **workflow 모듈**: langgraph 기반 워크플로우 관리
- **api 모듈**: FastAPI 엔드포인트 구현
- **models 모듈**: 데이터 모델 및 임베딩 모델 관리
- **utils 모듈**: 공통 유틸리티 기능

### 2. 의존성 관리

- 계층화된 아키텍처 적용 (API → 워크플로우 → Agent → 모델)
- 의존성 주입 패턴 사용으로 결합도 낮추기
- 인터페이스 정의를 통한 모듈 간 경계 명확화

### 3. 설계 패턴 적용

- **팩토리 패턴**: 다양한 Agent 생성
- **전략 패턴**: 다양한 LLM 구현체 교체 가능
- **옵저버 패턴**: 워크플로우 상태 변화 모니터링
- **의존성 주입**: 결합도 감소 및 테스트 용이성 확보

## 코드 스타일 통일

### 1. 네이밍 규칙

```python
# 변수 및 함수: snake_case
user_message = "Hello"
def process_request(request_data):
    pass

# 클래스: PascalCase
class UserManager:
    pass

# 상수: UPPER_CASE
MAX_TOKENS = 4096
```

### 2. 주석 및 문서화

- 클래스와 함수에 독스트링(docstring) 추가
- 복잡한 로직에 인라인 주석 추가
- 코드 블록 시작에 목적 설명 주석 추가

### 3. 들여쓰기 및 형식

- 4칸 공백 들여쓰기 사용
- 최대 줄 길이 100자 제한
- 함수 간 2줄 공백, 클래스 간 3줄 공백

## 에러 처리 표준화

### 1. 일관된 예외 처리

```python
try:
    # 작업 수행
except SpecificException as e:
    logger.error(f"작업 실패: {e}", exc_info=True)
    raise CustomException(f"작업을 완료할 수 없습니다: {e}") from e
```

### 2. 사용자 정의 예외

```python
class APIError(Exception):
    """API 관련 오류"""
    pass

class ValidationError(Exception):
    """입력 데이터 검증 오류"""
    pass
```

## 테스트 가이드라인

### 1. 단위 테스트

- 각 모듈의 핵심 기능에 대한 단위 테스트 작성
- pytest 프레임워크 사용
- 모의 객체(mock)를 활용한 의존성 격리

### 2. 통합 테스트

- API 엔드포인트에 대한 통합 테스트 작성
- 테스트 데이터베이스 및 환경 설정

## 성능 최적화

### 1. 리소스 사용 개선

- 불필요한 메모리 사용 최소화
- 대규모 데이터 처리 시 스트리밍 방식 활용
- 임시 파일 및 리소스 적절히 정리

### 2. 비동기 처리

- I/O 작업에 비동기 패턴 적용
- 백그라운드 작업 큐 활용

## 보안 강화

### 1. 민감 정보 관리

- API 키 등 민감 정보는 환경 변수로 관리
- 하드코딩된 보안 정보 제거

### 2. 입력 검증

- 모든 사용자 입력 데이터 검증
- Pydantic 모델 활용한 데이터 검증

## 개선 작업 우선순위

1. 누락된 의존성 패키지 추가 (requirements.txt 업데이트)
2. 민감 정보 및 하드코딩된 API 키 제거
3. 레거시 코드 및 미사용 코드 정리
4. 모듈 구조 개선 및 일관성 확보
5. 에러 처리 및 로깅 표준화
6. 테스트 코드 추가
