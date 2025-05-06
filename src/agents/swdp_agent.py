"""
SWDP 에이전트 - SW 개발 포털 인터페이스 에이전트

이 모듈은 SW 개발 포털(SWDP)에 접근하여 TR 정보, 티켓 정보 등을 검색하고 조작합니다.
"""

import uuid
import logging
import json
import re
import requests
from typing import Dict, Any, List, Optional, Union

from src.core.llm_service import llm_service
import config
from src.core.requests_config import get_secure_http_session
from src.utils.sql_utils import extract_sql_query
from src.utils.response_utils import format_agent_response as format_response
from src.agents.base_interface import BaseAgent

# 로깅 설정
logger = logging.getLogger("swdp_agent")

class SWDPAgent(BaseAgent):
    """SW 개발 포털 에이전트"""
    
    def __init__(self, **kwargs):
        """SWDP 에이전트 초기화"""
        self.agent_id = f"swdp-{uuid.uuid4()}"
        self.agent_type = "swdp"
        
        # 설정 로드
        swdp_config = config.get_swdp_tool_config() if hasattr(config, 'get_swdp_tool_config') else {}
        self.enabled = swdp_config.get('enabled', True)
        self.api_url = swdp_config.get('api_url', "https://swdp.example.com/api")
        self.username = swdp_config.get('username')
        self.password = swdp_config.get('password')
        self.db_schema_path = "./src/schema/swpdb.json"
        
        # Open API 설정
        self.internal_swdp_api = swdp_config.get('internal_swdp_api', "https://internal-swdp.example.com/api/v1")
        self.verify_ssl = swdp_config.get('verify_ssl', False)
        self.timeout = swdp_config.get('timeout', 30)
        
        # API 세션 초기화
        self.session = get_secure_http_session(
            timeout=self.timeout,
            verify_ssl=self.verify_ssl
        )
        
        # API 인증 헤더 설정
        if self.username and self.password:
            import base64
            auth_str = f"{self.username}:{self.password}"
            encoded_auth = base64.b64encode(auth_str.encode()).decode()
            self.session.headers.update({
                "Authorization": f"Basic {encoded_auth}",
                "Content-Type": "application/json"
            })
        
        # 스키마 정보 로드
        self.schema_info = self._load_schema_info()
        
        logger.info(f"SWDP 에이전트 초기화: {self.agent_id}")
    
    def _load_schema_info(self) -> Dict[str, Any]:
        """DB 스키마 정보 로드"""
        try:
            with open(self.db_schema_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"스키마 파일 로드 오류: {e}")
            return {}
    
    def _call_api(self, endpoint: str, method: str = "GET", 
                data: Dict[str, Any] = None, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        SWDP 내부 API 호출
        
        Args:
            endpoint: API 엔드포인트 경로
            method: HTTP 메서드
            data: 요청 데이터
            params: URL 파라미터
            
        Returns:
            API 응답 데이터
        """
        url = f"{self.internal_swdp_api.rstrip('/')}/{endpoint.lstrip('/')}"
        logger.info(f"SWDP API 호출: {method} {url}")
        
        try:
            from src.core.requests_config import make_api_request
            
            # API 요청 수행
            response = make_api_request(
                url=url,
                method=method,
                data=data,
                params=params,
                headers={
                    "Authorization": f"Basic {base64.b64encode(f'{self.username}:{self.password}'.encode()).decode()}"
                },
                verify_ssl=self.verify_ssl,
                timeout=self.timeout
            )
            
            if "error" in response:
                logger.error(f"API 오류: {response['error']}")
                return {"error": response["error"]}
                
            return response
            
        except Exception as e:
            logger.error(f"API 호출 오류: {e}")
            return {"error": str(e)}
            
    def _is_api_query(self, query: str) -> bool:
        """API 쿼리 여부 판단"""
        api_keywords = [
            "API", "웹훅", "webhook", "상태 변경", "업데이트", "update", 
            "생성", "create", "알림", "notification", "실시간", "realtime",
            "외부", "external", "연동", "integration", "호출", "call"
        ]
        
        query_lower = query.lower()
        return any(keyword.lower() in query_lower for keyword in api_keywords)

    def run(self, query: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        SWDP 쿼리 실행
        
        Args:
            query: 자연어 쿼리
            metadata: 추가 메타데이터 (검색 설정, TR ID 등)
            
        Returns:
            에이전트 응답
        """
        logger.info(f"SWDP 쿼리 실행: {query}")
        metadata = metadata or {}
        
        if not self.enabled:
            return format_response(self.agent_id, "오류: SWDP 에이전트가 비활성화되어 있습니다.", llm_service.model_id)
            
        # TR ID 확인
        tr_id = metadata.get("tr_id", "")
        
        # 데이터 접근 방식 결정 (DB vs API)
        if self._is_db_query(query):
            # DB 쿼리 처리
            return self._handle_db_query(query)
        elif self._is_api_query(query):
            # API 쿼리 처리
            return self._handle_api_query(query, tr_id)
        
        # 컨텍스트 정보
        context_from_other_agent = metadata.get("context", {})
        
        # 자연어 쿼리 분석 및 실행 계획 수립
        action_plan = self._analyze_query(query, tr_id)
        
        # 실행 계획에 따라 작업 수행
        result = self._execute_action_plan(action_plan, tr_id, context_from_other_agent)
        
        # 응답 반환
        return format_response(self.agent_id, result, llm_service.model_id)
    
    def _is_db_query(self, query: str) -> bool:
        """DB 쿼리 여부 판단"""
        db_keywords = [
            "검색", "조회", "쿼리", "query", "select", "찾아줘", 
            "데이터베이스", "database", "DB", "테이블", "table",
            "SQL", "통계", "조인", "join", "집계", "그룹", "group"
        ]
        
        query_lower = query.lower()
        return any(keyword.lower() in query_lower for keyword in db_keywords)
    
    def _handle_db_query(self, query: str) -> Dict[str, Any]:
        """DB 쿼리 처리"""
        # 스키마 정보 추출
        table_info = ""
        if 'database_schema' in self.schema_info:
            # 테이블 이름 추출
            tables_mentioned = self._extract_table_names(query)
            
            # 테이블 정보 추출
            for table_name in tables_mentioned:
                if table_name in self.schema_info['database_schema']:
                    table_data = self.schema_info['database_schema'][table_name]
                    table_info += f"테이블: {table_name}\n"
                    table_info += f"설명: {table_data.get('description', '설명 없음')}\n"
                    
                    # 컬럼 정보
                    table_info += "컬럼:\n"
                    for col_name, col_data in table_data.get('columns', {}).items():
                        col_type = col_data.get('type', '')
                        col_desc = col_data.get('description', '')
                        table_info += f"  - {col_name} ({col_type}): {col_desc}\n"
                    
                    table_info += "\n"
        
        # 예시 쿼리 추출
        example_queries = ""
        if 'example_queries' in self.schema_info:
            example_queries = "예시 쿼리:\n"
            for ex in self.schema_info.get('example_queries', [])[:3]:  # 최대 3개
                example_queries += f"- {ex.get('description', '')}\n"
                example_queries += f"  {ex.get('query', '')}\n\n"
        
        # 프롬프트 구성
        prompt = f"""SWDP 데이터베이스 전문가로서 다음 쿼리에 대한 SQL 쿼리를 작성해주세요.

질문: {query}

{table_info if table_info else ''}

{example_queries if example_queries else ''}

다음의 형식으로 응답해주세요:
1. 쿼리 분석: 사용자가 요청한 내용을 분석
2. SQL 쿼리 (```sql 형식으로): 실행할 SQL 쿼리
3. 결과 해석: 쿼리 결과를 어떻게 해석하면 되는지 설명

참고: 실제 환경에서 이 SQL 쿼리는 SWDP DB Agent에 전달되어 실행됩니다.
"""
        
        # LLM 호출
        messages = [llm_service.format_user_message(prompt)]
        response = llm_service.generate(messages)
        
        # SQL 쿼리 추출
        sql_query = extract_sql_query(response, check_sql_keywords=True)
        
        # 메타데이터 포함
        if sql_query:
            result = response + "\n\n---\n\n**참고**: 이 SQL 쿼리를 실행하려면 SWDP DB Agent를 이용해주세요."
        else:
            result = response
        
        return format_response(self.agent_id, result, llm_service.model_id)
    
    def _extract_table_names(self, query: str) -> List[str]:
        """쿼리에서 언급된 테이블 이름 추출"""
        if not self.schema_info or 'database_schema' not in self.schema_info:
            return []
        
        table_names = []
        query_lower = query.lower()
        
        for table_name in self.schema_info['database_schema'].keys():
            # 테이블 이름이나 설명이 언급되었는지 확인
            if table_name.lower() in query_lower:
                table_names.append(table_name)
            else:
                # 설명에서 테이블을 언급했는지 확인
                description = self.schema_info['database_schema'][table_name].get('description', '').lower()
                keywords = description.split()
                for keyword in keywords:
                    if len(keyword) > 3 and keyword in query_lower:  # 짧은 단어 제외
                        table_names.append(table_name)
                        break
        
        # TR 관련 키워드가 있으면 tr_items 테이블 추가
        tr_keywords = ["tr", "technical request", "기술 요청", "tr번호"]
        if any(keyword in query_lower for keyword in tr_keywords) and "tr_items" in self.schema_info['database_schema']:
            if "tr_items" not in table_names:
                table_names.append("tr_items")
        
        # 우선순위 또는 상태 관련 키워드가 있으면 tasks 테이블 추가
        task_keywords = ["task", "작업", "지연", "완료", "담당자", "우선순위", "priority", "status", "상태"]
        if any(keyword in query_lower for keyword in task_keywords) and "tasks" in self.schema_info['database_schema']:
            if "tasks" not in table_names:
                table_names.append("tasks")
        
        # 사용자 관련 키워드가 있으면 users 테이블 추가
        user_keywords = ["user", "사용자", "담당자", "이름", "사람", "직원"]
        if any(keyword in query_lower for keyword in user_keywords) and "users" in self.schema_info['database_schema']:
            if "users" not in table_names:
                table_names.append("users")
                
        return table_names
    
    
    def _analyze_query(self, query: str, tr_id: str) -> str:
        """쿼리 분석 및 실행 계획 생성"""
        # 프롬프트 구성
        prompt = f"""SWDP 에이전트로서 다음 쿼리를 분석하고 수행할 작업을 결정하세요:

쿼리: {query}
{'TR ID: ' + tr_id if tr_id else 'TR ID 없음'}

가능한 작업:
1. TR 정보 검색
2. TR 작업 목록 조회
3. TR 이력 조회
4. 티켓 정보 검색
5. 신규 티켓 생성

쿼리를 분석하여 어떤 작업을 수행해야 하는지 결정하세요.
결정한 작업을 작업 번호와 함께 명확하게 설명하세요.
"""
        
        # 메시지 구성
        messages = [llm_service.format_user_message(prompt)]
        
        # LLM 호출
        action_plan = llm_service.generate(messages)
        
        # 오류 처리
        if isinstance(action_plan, dict) and "error" in action_plan:
            return f"쿼리 분석 오류: {action_plan['error']}"
        
        return action_plan
    
    def _handle_api_query(self, query: str, tr_id: str = "") -> Dict[str, Any]:
        """
        API 쿼리 처리
        
        Args:
            query: 자연어 쿼리
            tr_id: TR ID (선택적)
            
        Returns:
            API 응답 포맷팅 결과
        """
        logger.info(f"API 쿼리 처리: {query}")
        
        # 프롬프트 구성
        prompt = f"""SWDP API 전문가로서 다음 쿼리를 분석하고 적절한 API 호출을 결정해주세요.

질문: {query}
{'TR ID: ' + tr_id if tr_id else ''}

SWDP Open API는 다음과 같은 기능을 제공합니다:
1. TR 정보 조회 (/tr/{id})
2. TR 작업 목록 조회 (/tr/{id}/tasks)
3. TR 이력 조회 (/tr/{id}/history)
4. 티켓 정보 조회 (/ticket/{id})
5. 티켓 생성 (POST /ticket)
6. 상태 업데이트 (PUT /tr/{id}/status)
7. 알림 설정 (POST /notifications)

적절한 API 엔드포인트와 HTTP 메서드를 결정하고, 필요한 파라미터와 요청 본문을 제안해주세요.
응답은 아래 형식으로 작성해주세요:

1. 엔드포인트: /api/path
2. 메서드: GET/POST/PUT/DELETE
3. 파라미터: key1=value1, key2=value2 (URL 쿼리 파라미터)
4. 요청 본문: {"key": "value"} (POST/PUT 요청에 사용)
5. 목적: 이 API 호출의 목적 간략 설명
"""
        
        # 메시지 구성
        messages = [llm_service.format_user_message(prompt)]
        
        # LLM 호출
        response = llm_service.generate(messages)
        
        # 오류 처리
        if isinstance(response, dict) and "error" in response:
            return format_response(self.agent_id, f"API 분석 오류: {response['error']}", llm_service.model_id)
        
        # API 호출 정보 추출
        api_info = self._extract_api_info(response)
        
        if not api_info or "endpoint" not in api_info:
            return format_response(self.agent_id, f"API 정보 추출 실패. 응답:\n\n{response}", llm_service.model_id)
        
        # API 호출 수행
        api_result = self._call_api(
            endpoint=api_info["endpoint"],
            method=api_info.get("method", "GET"),
            params=api_info.get("params", {}),
            data=api_info.get("data", {})
        )
        
        # 에러 처리
        if "error" in api_result:
            # 에러 응답 포맷팅
            from src.utils.response_utils import format_error_response
            
            error_msg = f"## API 호출 오류\n\n```\n{api_result['error']}\n```\n\n### API 정보\n\n"
            error_msg += f"- 엔드포인트: {api_info['endpoint']}\n"
            error_msg += f"- 메서드: {api_info.get('method', 'GET')}\n"
            
            # 에이전트 응답 형식으로 변환하여 반환
            return format_response(self.agent_id, error_msg, llm_service.model_id)
        
        # API 호출 결과 포맷팅
        result = f"## API 호출 성공: {api_info.get('method', 'GET')} {api_info['endpoint']}\n\n"
        
        # API 호출 목적 추가
        if "purpose" in api_info:
            result += f"### 목적\n\n{api_info['purpose']}\n\n"
        
        # 응답 데이터 추가
        result += "### 응답 데이터\n\n"
        result += f"```json\n{json.dumps(api_result, indent=2, ensure_ascii=False)}\n```\n\n"
        
        return format_response(self.agent_id, result, llm_service.model_id)
    
    def _extract_api_info(self, text: str) -> Dict[str, Any]:
        """
        LLM 응답에서 API 호출 정보 추출
        
        Args:
            text: LLM 응답 텍스트
            
        Returns:
            API 호출 정보 사전
        """
        api_info = {
            "endpoint": "",
            "method": "GET",
            "params": {},
            "data": {},
            "purpose": ""
        }
        
        # 엔드포인트 추출
        endpoint_match = re.search(r"엔드포인트:\s*(\/[^\s,\n]+)", text)
        if endpoint_match:
            api_info["endpoint"] = endpoint_match.group(1)
        
        # 메서드 추출
        method_match = re.search(r"메서드:\s*(GET|POST|PUT|DELETE)", text)
        if method_match:
            api_info["method"] = method_match.group(1)
        
        # 파라미터 추출
        params_match = re.search(r"파라미터:(.*?)(?:\n|\r\n|\r|$)", text, re.DOTALL)
        if params_match:
            params_text = params_match.group(1).strip()
            if params_text and params_text.lower() not in ["없음", "none", "n/a"]:
                for param in params_text.split(','):
                    if '=' in param:
                        key, value = param.split('=', 1)
                        api_info["params"][key.strip()] = value.strip()
        
        # 요청 본문 추출
        data_match = re.search(r"요청 본문:(.+?)(?:\n\d\.|\n$)", text, re.DOTALL)
        if data_match:
            data_text = data_match.group(1).strip()
            if data_text and data_text.lower() not in ["없음", "none", "n/a"]:
                try:
                    # JSON 객체 찾기
                    json_match = re.search(r"\{.*\}", data_text, re.DOTALL)
                    if json_match:
                        api_info["data"] = json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    logger.warning(f"요청 본문 JSON 파싱 실패: {data_text}")
        
        # 목적 추출
        purpose_match = re.search(r"목적:(.+?)(?:\n\d\.|\n$|$)", text, re.DOTALL)
        if purpose_match:
            api_info["purpose"] = purpose_match.group(1).strip()
        
        return api_info
    
    def _execute_action_plan(self, action_plan: str, tr_id: str, context: Dict[str, Any]) -> str:
        """실행 계획에 따라 작업 수행"""
        # 작업 유형 결정
        action_type = self._determine_action_type(action_plan)
        
        # 작업 유형에 따라 처리
        if "TR 정보 검색" in action_type:
            return self._get_tr_info(tr_id or self._extract_tr_id(action_plan))
        elif "TR 작업 목록" in action_type:
            return self._get_tr_tasks(tr_id or self._extract_tr_id(action_plan))
        elif "TR 이력" in action_type:
            return self._get_tr_history(tr_id or self._extract_tr_id(action_plan))
        elif "티켓 정보" in action_type:
            ticket_id = self._extract_ticket_id(action_plan)
            return self._get_ticket_info(ticket_id)
        elif "신규 티켓" in action_type:
            # Jira 컨텍스트 확인
            jira_context = context.get("jira", "")
            return self._create_ticket(action_plan, tr_id, jira_context)
        else:
            return f"지원되지 않는 작업 유형입니다: {action_type}\n\n실행 계획:\n{action_plan}"
    
    def _determine_action_type(self, action_plan: str) -> str:
        """실행 계획에서 작업 유형 결정"""
        action_types = ["TR 정보 검색", "TR 작업 목록", "TR 이력", "티켓 정보", "신규 티켓"]
        for action in action_types:
            if action in action_plan:
                return action
        return "알 수 없는 작업"
    
    def _extract_tr_id(self, text: str) -> str:
        """텍스트에서 TR ID 추출"""
        # 간단한 가상 구현 (실제로는 정규식 또는 NER 사용)
        if "TR-" in text:
            # TR ID 형식: TR-숫자
            parts = text.split("TR-")
            if len(parts) > 1:
                tr_id = "TR-" + parts[1].split()[0].strip()
                return tr_id
        return "TR-12345"  # 기본값
    
    def _extract_ticket_id(self, text: str) -> str:
        """텍스트에서 티켓 ID 추출"""
        # 간단한 가상 구현 (실제로는 정규식 또는 NER 사용)
        if "TICKET-" in text:
            parts = text.split("TICKET-")
            if len(parts) > 1:
                ticket_id = "TICKET-" + parts[1].split()[0].strip()
                return ticket_id
        return "TICKET-67890"  # 기본값
    
    def _get_tr_info(self, tr_id: str) -> str:
        """TR 정보 조회 (가상 구현)"""
        # 실제 구현에서는 SWDP API 호출
        tr_info = {
            "id": tr_id,
            "title": f"{tr_id} - 신규 기능 개발 요청",
            "status": "진행 중",
            "priority": "중간",
            "assigned_to": "홍길동",
            "requested_by": "김철수",
            "created_date": "2023-08-15",
            "deadline": "2023-09-30",
            "description": "사용자 인증 시스템 개선 및 새로운 대시보드 기능 추가 개발 요청"
        }
        
        # 결과 형식화
        result = f"## TR 정보: {tr_id}\n\n"
        result += f"제목: {tr_info['title']}\n"
        result += f"상태: {tr_info['status']}\n"
        result += f"우선순위: {tr_info['priority']}\n"
        result += f"담당자: {tr_info['assigned_to']}\n"
        result += f"요청자: {tr_info['requested_by']}\n"
        result += f"생성일: {tr_info['created_date']}\n"
        result += f"마감일: {tr_info['deadline']}\n\n"
        result += f"설명:\n{tr_info['description']}\n"
        
        # SQL 쿼리 예시 추가
        result += "\n\n## 관련 데이터 조회 예시\n\n"
        result += "이 TR 정보를 데이터베이스에서 조회하는 SQL 쿼리 예시입니다:\n\n"
        result += "```sql\n"
        result += f"SELECT * FROM tr_items WHERE tr_number = '{tr_id}';\n"
        result += "```\n\n"
        result += "이 쿼리를 실행하려면 'SWDP DB' 에이전트를 사용하세요."
        
        return result
    
    def _get_tr_tasks(self, tr_id: str) -> str:
        """TR 작업 목록 조회 (가상 구현)"""
        # 실제 구현에서는 SWDP API 호출
        tasks = [
            {"id": "TASK-1", "title": "요구사항 분석", "status": "완료", "assigned_to": "홍길동"},
            {"id": "TASK-2", "title": "설계 문서 작성", "status": "완료", "assigned_to": "홍길동"},
            {"id": "TASK-3", "title": "구현 - 인증 모듈", "status": "진행 중", "assigned_to": "김영희"},
            {"id": "TASK-4", "title": "구현 - 대시보드", "status": "대기 중", "assigned_to": "이철수"},
            {"id": "TASK-5", "title": "테스트", "status": "대기 중", "assigned_to": "박지민"}
        ]
        
        # 결과 형식화
        result = f"## TR 작업 목록: {tr_id}\n\n"
        for task in tasks:
            result += f"- {task['id']}: {task['title']} ({task['status']}, 담당: {task['assigned_to']})\n"
        
        # SQL 쿼리 예시 추가
        result += "\n\n## 관련 데이터 조회 예시\n\n"
        result += "이 TR의 작업 목록을 데이터베이스에서 조회하는 SQL 쿼리 예시입니다:\n\n"
        result += "```sql\n"
        result += f"SELECT t.id, t.title, t.status, u.first_name || ' ' || u.last_name as assigned_to\n"
        result += f"FROM tasks t\n"
        result += f"JOIN users u ON t.assignee_id = u.id\n"
        result += f"JOIN tr_items tr ON t.project_id = tr.project_id\n"
        result += f"WHERE tr.tr_number = '{tr_id}'\n"
        result += f"ORDER BY t.priority, t.created_at;\n"
        result += "```\n\n"
        result += "이 쿼리를 실행하려면 'SWDP DB' 에이전트를 사용하세요."
        
        return result
    
    def _get_tr_history(self, tr_id: str) -> str:
        """TR 이력 조회 (가상 구현)"""
        # 실제 구현에서는 SWDP API 호출
        history = [
            {"date": "2023-08-15", "action": "생성", "user": "김철수", "details": "TR 생성"},
            {"date": "2023-08-16", "action": "담당자 지정", "user": "관리자", "details": "담당자를 홍길동으로 지정"},
            {"date": "2023-08-18", "action": "상태 변경", "user": "홍길동", "details": "상태를 '분석 중'으로 변경"},
            {"date": "2023-08-22", "action": "상태 변경", "user": "홍길동", "details": "상태를 '설계 중'으로 변경"},
            {"date": "2023-08-30", "action": "상태 변경", "user": "홍길동", "details": "상태를 '구현 중'으로 변경"},
            {"date": "2023-09-10", "action": "코멘트", "user": "김영희", "details": "인증 모듈 구현 진행 상황 보고"}
        ]
        
        # 결과 형식화
        result = f"## TR 이력: {tr_id}\n\n"
        for entry in history:
            result += f"- {entry['date']}: {entry['action']} ({entry['user']})\n  {entry['details']}\n"
        
        # SQL 쿼리 예시 추가
        result += "\n\n## 관련 데이터 조회 예시\n\n"
        result += "이 TR의 이력을 데이터베이스에서 조회하는 SQL 쿼리 예시입니다:\n\n"
        result += "```sql\n"
        result += f"SELECT th.created_at as date, th.field_changed as action, \n"
        result += f"       u.first_name || ' ' || u.last_name as user_name, \n"
        result += f"       th.new_value as details\n"
        result += f"FROM task_history th\n"
        result += f"JOIN users u ON th.user_id = u.id\n"
        result += f"JOIN tr_items tr ON th.task_id = tr.id\n"
        result += f"WHERE tr.tr_number = '{tr_id}'\n"
        result += f"ORDER BY th.created_at DESC;\n"
        result += "```\n\n"
        result += "이 쿼리를 실행하려면 'SWDP DB' 에이전트를 사용하세요."
        
        return result
    
    def _get_ticket_info(self, ticket_id: str) -> str:
        """티켓 정보 조회 (가상 구현)"""
        # 실제 구현에서는 SWDP API 호출
        ticket_info = {
            "id": ticket_id,
            "title": f"{ticket_id} - UI 버그 수정",
            "status": "진행 중",
            "priority": "높음",
            "assigned_to": "김영희",
            "reported_by": "이철수",
            "created_date": "2023-09-05",
            "deadline": "2023-09-15",
            "description": "로그인 화면에서 특정 조건에서 버튼이 비활성화되는 버그 수정 필요",
            "related_tr": "TR-12345"
        }
        
        # 결과 형식화
        result = f"## 티켓 정보: {ticket_id}\n\n"
        result += f"제목: {ticket_info['title']}\n"
        result += f"상태: {ticket_info['status']}\n"
        result += f"우선순위: {ticket_info['priority']}\n"
        result += f"담당자: {ticket_info['assigned_to']}\n"
        result += f"보고자: {ticket_info['reported_by']}\n"
        result += f"생성일: {ticket_info['created_date']}\n"
        result += f"마감일: {ticket_info['deadline']}\n"
        result += f"관련 TR: {ticket_info['related_tr']}\n\n"
        result += f"설명:\n{ticket_info['description']}\n"
        
        # SQL 쿼리 예시 추가
        result += "\n\n## 관련 데이터 조회 예시\n\n"
        result += "데이터베이스에서 유사한 티켓을 조회하는 SQL 쿼리 예시입니다:\n\n"
        result += "```sql\n"
        result += f"SELECT t.id, t.title, t.status, t.priority, \n"
        result += f"       ua.first_name || ' ' || ua.last_name as assigned_to, \n"
        result += f"       ur.first_name || ' ' || ur.last_name as reported_by,\n"
        result += f"       t.created_at, t.due_date, tr.tr_number\n"
        result += f"FROM tasks t\n"
        result += f"JOIN users ua ON t.assignee_id = ua.id\n"
        result += f"JOIN users ur ON t.reporter_id = ur.id\n"
        result += f"LEFT JOIN tr_items tr ON t.project_id = tr.project_id\n"
        result += f"WHERE t.type = 'bug' AND t.status != 'done'\n"
        result += f"ORDER BY t.priority, t.created_at;\n"
        result += "```\n\n"
        result += "이 쿼리를 실행하려면 'SWDP DB' 에이전트를 사용하세요."
        
        return result
    
    def _create_ticket(self, action_plan: str, tr_id: str, jira_context: str) -> str:
        """새 티켓 생성 (가상 구현)"""
        # 실제 구현에서는 SWDP API 호출
        
        # 티켓 제목/설명 추출 (실제로는 LLM으로 파싱)
        title = "신규 기능 개발 티켓"
        description = "TR 요청에 따른 신규 기능 개발 티켓입니다."
        
        if jira_context:
            # Jira 컨텍스트가 있으면 연동 정보 추가
            title = f"[Jira 연동] {title}"
            description += f"\n\nJira 컨텍스트:\n{jira_context}"
        
        # 가상 티켓 생성 결과
        ticket_id = f"TICKET-{uuid.uuid4().hex[:6].upper()}"
        
        # 결과 형식화
        result = f"## 새 티켓 생성 완료\n\n"
        result += f"티켓 ID: {ticket_id}\n"
        result += f"제목: {title}\n"
        result += f"관련 TR: {tr_id}\n"
        result += f"설명: {description}\n\n"
        result += "상태: 생성됨\n"
        
        # SQL 쿼리 예시 추가
        result += "\n\n## 데이터베이스 입력 예시\n\n"
        result += "이 티켓을 데이터베이스에 입력하는 SQL 쿼리 예시입니다:\n\n"
        result += "```sql\n"
        result += f"INSERT INTO tasks (title, description, status, priority, assignee_id, reporter_id, type, project_id)\n"
        result += f"VALUES ('{title}', '{description}', 'to_do', 'medium', \n"
        result += f"        (SELECT id FROM users WHERE username = 'current_user'),\n"
        result += f"        (SELECT id FROM users WHERE username = 'current_user'),\n"
        result += f"        'task',\n"
        result += f"        (SELECT project_id FROM tr_items WHERE tr_number = '{tr_id}'));\n"
        result += "```\n\n"
        result += "이 쿼리를 실행하려면 'SWDP DB' 에이전트를 사용하세요."
        
        return result