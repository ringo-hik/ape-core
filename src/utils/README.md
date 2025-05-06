# 유틸리티 모듈

이 모듈은 Axiom Agent 시스템에서 사용되는 공통 유틸리티 함수를 제공합니다.

## 주요 기능

- SQL 관련 유틸리티 (`sql_utils.py`)
- 응답 포맷팅 유틸리티 (`response_utils.py`)

## SQL 유틸리티

SQL 쿼리 추출, 결과 포맷팅 등의 기능을 제공합니다.

```python
from src.utils import extract_sql_query, format_query_result

# 텍스트에서 SQL 쿼리 추출
query = extract_sql_query(text, check_sql_keywords=True)

# 쿼리 결과 포맷팅
formatted_result = format_query_result(result, sql_query, llm_response, agent_type)
```

## 응답 포맷팅 유틸리티

에이전트 응답, 에러 응답, 스트리밍 응답 등의 포맷팅 기능을 제공합니다.

```python
from src.utils import format_agent_response

# 에이전트 응답 포맷팅
response = format_agent_response(content, agent_id, model_id)
```

## 사용 방법

각 에이전트 클래스에서 중복 코드 대신 이 유틸리티 모듈의 함수를 사용하여 코드 중복을 줄이고 일관성을 유지합니다.

예시:

```python
from src.utils import extract_sql_query, format_agent_response

class CustomAgent:
    def process_query(self, text):
        # SQL 쿼리 추출
        query = extract_sql_query(text)
        
        # 응답 포맷팅
        return format_agent_response(result, self.agent_id, self.model_id)
```