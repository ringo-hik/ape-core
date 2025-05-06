"""
Jira 에이전트 - Jira 인터페이스 에이전트

이 모듈은 내부 Jira 시스템과 상호작용하여 프로젝트, 이슈, 댓글 등을 조회하고 수정합니다.
Mock 모드를 지원하여 내부망 연결 없이도 테스트 가능합니다.
"""

import uuid
import logging
import json
import os
from typing import Dict, Any, List, Optional, Union
import re

from src.core.llm_service import llm_service
import config
from src.core.requests_config import get_secure_http_session
from src.utils.response_utils import format_agent_response as format_response
from src.agents.base_interface import BaseAgent

# 로깅 설정
logger = logging.getLogger("jira_agent")

class JiraAgent(BaseAgent):
    """Jira 인터페이스 에이전트"""
    
    def __init__(self, **kwargs):
        """Jira 에이전트 초기화"""
        self.agent_id = f"jira-{uuid.uuid4()}"
        self.agent_type = "jira"
        
        # 설정 로드
        self.jira_config = config.get_jira_tool_config() if hasattr(config, 'get_jira_tool_config') else {}
        self.enabled = self.jira_config.get('enabled', True)
        self.api_url = self.jira_config.get('api_url', "https://jira.internal.example.com/rest/api/2")
        self.username = self.jira_config.get('username', "jira_agent")
        self.password = self.jira_config.get('password', "")
        
        # Mock 모드 설정
        self.mock_mode = True  # 항상 Mock 모드로 실행
        
        # 스키마 정보 로드
        self.schema_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                        "src", "schema", "jira.json")
        self.schema_info = self._load_schema()
        
        # API 세션 초기화 (실제 연결 시 사용)
        if not self.mock_mode:
            self.session = get_secure_http_session(timeout=30, verify_ssl=False)
            
            # 기본 인증 설정
            if self.username and self.password:
                import base64
                auth_str = f"{self.username}:{self.password}"
                encoded_auth = base64.b64encode(auth_str.encode()).decode()
                self.session.headers.update({
                    "Authorization": f"Basic {encoded_auth}",
                    "Content-Type": "application/json"
                })
        
        logger.info(f"Jira 에이전트 초기화: {self.agent_id} (Mock 모드: {self.mock_mode})")
    
    def _load_schema(self) -> Dict[str, Any]:
        """스키마 정보 로드"""
        try:
            if os.path.exists(self.schema_path):
                with open(self.schema_path, 'r', encoding='utf-8') as f:
                    schema_data = json.load(f)
                logger.info(f"스키마 파일 로드 성공: {self.schema_path}")
                return schema_data
            else:
                logger.warning(f"스키마 파일이 존재하지 않음: {self.schema_path}")
                return {}
        except Exception as e:
            logger.error(f"스키마 파일 로드 오류: {e}")
            return {}
    
    def _find_endpoint_response(self, endpoint_path: str, method: str = "GET") -> Dict[str, Any]:
        """
        스키마에서 엔드포인트 응답 찾기
        
        Args:
            endpoint_path: API 엔드포인트 경로
            method: HTTP 메서드
            
        Returns:
            Mock 응답 데이터
        """
        if not self.schema_info or "api_endpoints" not in self.schema_info:
            return {"error": "스키마 정보가 없습니다."}
        
        # 경로 파라미터 처리 (예: /issue/{issueKey} -> /issue/*)
        endpoint_pattern = endpoint_path
        if "{" in endpoint_path:
            endpoint_pattern = re.sub(r'\{[^}]+\}', '*', endpoint_path)
        
        # 엔드포인트 찾기
        for endpoint in self.schema_info["api_endpoints"]:
            schema_endpoint = endpoint.get("endpoint", "")
            schema_method = endpoint.get("method", "GET")
            
            # 엔드포인트 패턴 매칭
            if (schema_endpoint == endpoint_path or 
                (schema_endpoint.replace("*", "") in endpoint_path and "*" in schema_endpoint)) and \
               schema_method == method:
                
                # 경로 파라미터 처리
                if "path_params" in endpoint and "{" in schema_endpoint:
                    for param_name, param_value in endpoint["path_params"].items():
                        if "{" + param_name + "}" in schema_endpoint:
                            # 실제 엔드포인트에서 파라미터 값 추출
                            param_pattern = schema_endpoint.replace("{" + param_name + "}", "([^/]+)")
                            param_match = re.match(param_pattern, endpoint_path)
                            if param_match and param_match.group(1) == param_value:
                                return endpoint.get("response", {})
                
                # 일반 엔드포인트 매칭
                return endpoint.get("response", {})
        
        return {"error": f"엔드포인트 찾을 수 없음: {endpoint_path} ({method})"}
    
    def _call_api(self, endpoint: str, method: str = "GET", 
                 data: Dict[str, Any] = None, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Jira API 호출
        
        Args:
            endpoint: API 엔드포인트 경로
            method: HTTP 메서드
            data: 요청 데이터
            params: URL 파라미터
            
        Returns:
            API 응답 데이터
        """
        # Mock 모드인 경우 스키마에서 응답 찾기
        if self.mock_mode:
            logger.info(f"Mock 모드 Jira API 호출: {method} {endpoint}")
            
            # 각 엔드포인트별 특수 처리
            if endpoint == "/myself" and method == "GET":
                return self._find_endpoint_response("/rest/api/2/myself", "GET")
            elif endpoint == "/project" and method == "GET":
                return self._find_endpoint_response("/rest/api/2/project", "GET")
            elif endpoint.startswith("/issue/") and method == "GET":
                issue_key = endpoint.split("/")[-1]
                # /rest/api/2/issue/{issueKey} 형식으로 변환
                mock_endpoint = "/rest/api/2/issue/{issueKey}"
                response = self._find_endpoint_response(mock_endpoint, "GET")
                # issueKey를 실제 값으로 대체
                if isinstance(response, dict) and "key" in response:
                    response["key"] = issue_key
                return response
            elif endpoint == "/issue" and method == "POST":
                # 이슈 생성
                mock_response = self._find_endpoint_response("/rest/api/2/issue", "POST")
                if data and "fields" in data and "summary" in data["fields"]:
                    # 이슈 제목을 응답에 반영
                    mock_response["key"] = f"AI-{uuid.uuid4().hex[:3].upper()}"
                return mock_response
            elif endpoint == "/search" and method == "POST":
                # 이슈 검색
                return self._find_endpoint_response("/rest/api/2/search", "POST")
            else:
                # 일반적인 엔드포인트 처리
                return self._find_endpoint_response(f"/rest/api/2{endpoint}", method)
        
        # 실제 API 호출 (Mock 모드가 아닌 경우)
        url = f"{self.api_url.rstrip('/')}/{endpoint.lstrip('/')}"
        logger.info(f"Jira API 호출: {method} {url}")
        
        try:
            response = None
            
            if method == "GET":
                response = self.session.get(url, params=params)
            elif method == "POST":
                response = self.session.post(url, json=data, params=params)
            elif method == "PUT":
                response = self.session.put(url, json=data, params=params)
            elif method == "DELETE":
                response = self.session.delete(url, params=params)
            
            if response and response.status_code < 400:
                return response.json()
            else:
                error_msg = f"API 오류: {response.status_code}" if response else "API 응답 없음"
                logger.error(error_msg)
                return {"error": error_msg}
                
        except Exception as e:
            logger.error(f"API 호출 오류: {e}")
            return {"error": str(e)}
    
    def run(self, query: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Jira 쿼리 실행
        
        Args:
            query: 자연어 쿼리
            metadata: 추가 메타데이터
            
        Returns:
            에이전트 응답
        """
        logger.info(f"Jira 쿼리 실행: {query}")
        metadata = metadata or {}
        
        if not self.enabled:
            return format_response(self.agent_id, "오류: Jira 에이전트가 비활성화되어 있습니다.", llm_service.model_id)
        
        # 작업 분석 (Jira 쿼리 의도 파악)
        action_plan = self._analyze_query(query)
        logger.info(f"Jira 작업 분석: {action_plan}")
        
        # 작업 수행
        action_type = self._determine_action_type(action_plan)
        
        # 작업 유형별 처리
        if "내 정보" in action_type or "사용자 정보" in action_type:
            result = self._get_myself()
        elif "프로젝트 목록" in action_type:
            result = self._get_projects()
        elif "이슈 생성" in action_type:
            result = self._create_issue(query, action_plan)
        elif "이슈 검색" in action_type:
            result = self._search_issues(query, action_plan)
        elif "이슈 상세" in action_type:
            issue_key = self._extract_issue_key(query, action_plan)
            result = self._get_issue_details(issue_key)
        else:
            result = f"지원되지 않는 작업 유형입니다: {action_type}\n\n실행 계획:\n{action_plan}"
        
        # 응답 반환
        return format_response(self.agent_id, result, llm_service.model_id)
    
    def _analyze_query(self, query: str) -> str:
        """
        쿼리 분석 및 실행 계획 생성
        
        Args:
            query: 자연어 쿼리
            
        Returns:
            실행 계획
        """
        # 프롬프트 구성
        prompt = f"""Jira 에이전트로서 다음 쿼리를 분석하고 수행할 작업을 결정하세요:

쿼리: {query}

가능한 작업:
1. 내 사용자 정보 조회
2. 프로젝트 목록 조회
3. 이슈 생성
4. 이슈 검색
5. 이슈 상세 조회

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
    
    def _determine_action_type(self, action_plan: str) -> str:
        """실행 계획에서 작업 유형 결정"""
        action_types = ["내 정보", "사용자 정보", "프로젝트 목록", "이슈 생성", "이슈 검색", "이슈 상세"]
        for action in action_types:
            if action in action_plan:
                return action
        return "알 수 없는 작업"
    
    def _extract_issue_key(self, query: str, action_plan: str) -> str:
        """텍스트에서 이슈 키 추출"""
        # Jira 이슈 키 패턴 (예: AI-101, SWDP-2023 등)
        issue_key_pattern = r'([A-Z]+-\d+)'
        
        # 쿼리에서 이슈 키 찾기
        match = re.search(issue_key_pattern, query)
        if match:
            return match.group(1)
            
        # 실행 계획에서 이슈 키 찾기
        match = re.search(issue_key_pattern, action_plan)
        if match:
            return match.group(1)
        
        # 기본값 반환
        return "AI-101"  # 기본 이슈 키
    
    def _get_myself(self) -> str:
        """현재 사용자 정보 조회"""
        response = self._call_api("/myself", "GET")
        
        if "error" in response:
            return f"사용자 정보 조회 오류: {response['error']}"
        
        result = "## 내 사용자 정보\n\n"
        result += f"사용자명: {response.get('name', 'N/A')}\n"
        result += f"이메일: {response.get('emailAddress', 'N/A')}\n"
        result += f"표시 이름: {response.get('displayName', 'N/A')}\n"
        result += f"상태: {'활성' if response.get('active', False) else '비활성'}\n"
        
        # 그룹 정보
        if "groups" in response and "items" in response["groups"]:
            groups = [item["name"] for item in response["groups"]["items"]]
            result += f"그룹: {', '.join(groups)}\n"
        
        # 권한 정보
        if "applicationRoles" in response and "items" in response["applicationRoles"]:
            roles = [item["name"] for item in response["applicationRoles"]["items"]]
            result += f"역할: {', '.join(roles)}\n"
        
        return result
    
    def _get_projects(self) -> str:
        """프로젝트 목록 조회"""
        response = self._call_api("/project", "GET")
        
        if "error" in response:
            return f"프로젝트 목록 조회 오류: {response['error']}"
        
        result = "## Jira 프로젝트 목록\n\n"
        
        if not response:
            return result + "프로젝트가 없습니다."
        
        for project in response:
            result += f"- **{project.get('name', 'N/A')}** ({project.get('key', 'N/A')})\n"
            result += f"  유형: {project.get('projectTypeKey', 'N/A')}\n"
            result += f"  리더: {project.get('lead', {}).get('name', 'N/A')}\n"
            result += "\n"
        
        return result
    
    def _create_issue(self, query: str, action_plan: str) -> str:
        """
        이슈 생성
        
        Args:
            query: 자연어 쿼리
            action_plan: 실행 계획
            
        Returns:
            이슈 생성 결과
        """
        # 이슈 정보 추출을 위한 프롬프트
        prompt = f"""Jira 이슈를 생성하기 위해 다음 정보를 추출해주세요:

쿼리: {query}
실행 계획: {action_plan}

추출해야 할 정보:
1. 프로젝트 키: 이슈를 생성할 프로젝트의 키 (예: AI, SWDP)
2. 이슈 제목: 간결하고 명확한 이슈 제목
3. 이슈 설명: 이슈에 대한 상세 설명
4. 이슈 유형: Task, Bug, Story 등
5. 우선순위: Highest, High, Medium, Low, Lowest
6. 담당자: 이슈를 담당할 사용자 (없으면 빈칸)

각 정보를 추출하여 아래 형식으로 응답해주세요:
```json
{
  "project_key": "프로젝트 키",
  "summary": "이슈 제목",
  "description": "이슈 설명",
  "issue_type": "이슈 유형",
  "priority": "우선순위",
  "assignee": "담당자"
}
```
"""
        
        # 메시지 구성
        messages = [llm_service.format_user_message(prompt)]
        
        # LLM 호출
        extraction_result = llm_service.generate(messages)
        
        # JSON 추출
        import re
        json_match = re.search(r'```json\s*(.*?)\s*```', extraction_result, re.DOTALL)
        
        issue_data = {}
        if json_match:
            try:
                issue_data = json.loads(json_match.group(1))
            except json.JSONDecodeError:
                return "이슈 정보 추출 오류: JSON 파싱 실패"
        else:
            return "이슈 정보 추출 오류: JSON 포맷을 찾을 수 없음"
        
        # API 호출 데이터 구성
        api_data = {
            "fields": {
                "project": {
                    "key": issue_data.get("project_key", "AI")
                },
                "summary": issue_data.get("summary", "새 이슈"),
                "description": issue_data.get("description", ""),
                "issuetype": {
                    "name": issue_data.get("issue_type", "Task")
                },
                "priority": {
                    "name": issue_data.get("priority", "Medium")
                }
            }
        }
        
        # 담당자가 있는 경우 추가
        if issue_data.get("assignee"):
            api_data["fields"]["assignee"] = {"name": issue_data["assignee"]}
        
        # API 호출
        response = self._call_api("/issue", "POST", data=api_data)
        
        if "error" in response:
            return f"이슈 생성 오류: {response['error']}"
        
        # 결과 반환
        result = "## 이슈 생성 완료\n\n"
        result += f"이슈 키: **{response.get('key', 'N/A')}**\n"
        result += f"이슈 링크: {response.get('self', '#')}\n\n"
        result += f"제목: {issue_data.get('summary', 'N/A')}\n"
        result += f"프로젝트: {issue_data.get('project_key', 'N/A')}\n"
        result += f"유형: {issue_data.get('issue_type', 'N/A')}\n"
        result += f"우선순위: {issue_data.get('priority', 'N/A')}\n"
        
        if issue_data.get("assignee"):
            result += f"담당자: {issue_data['assignee']}\n"
        
        result += f"\n설명:\n{issue_data.get('description', 'N/A')}\n"
        
        return result
    
    def _search_issues(self, query: str, action_plan: str) -> str:
        """
        이슈 검색
        
        Args:
            query: 자연어 쿼리
            action_plan: 실행 계획
            
        Returns:
            이슈 검색 결과
        """
        # 검색 조건 추출을 위한 프롬프트
        prompt = f"""Jira 이슈를 검색하기 위한 JQL(Jira Query Language)을 작성해주세요:

쿼리: {query}
실행 계획: {action_plan}

주요 JQL 예시:
- project = "프로젝트키"
- status = "상태" (예: "To Do", "In Progress", "Done")
- assignee = "담당자"
- reporter = "보고자"
- priority = "우선순위"
- created >= "2023-01-01"
- labels = "라벨"
- summary ~ "검색어" (제목에 포함)
- description ~ "검색어" (설명에 포함)
- ORDER BY 필드 ASC/DESC (정렬)

쿼리를 분석하여 적절한 JQL을 작성해주세요.
```jql
여기에 JQL 작성
```
"""
        
        # 메시지 구성
        messages = [llm_service.format_user_message(prompt)]
        
        # LLM 호출
        jql_result = llm_service.generate(messages)
        
        # JQL 추출
        import re
        jql_match = re.search(r'```jql\s*(.*?)\s*```', jql_result, re.DOTALL)
        
        jql = "project = AI AND status != Done ORDER BY priority DESC"  # 기본 JQL
        if jql_match:
            jql = jql_match.group(1).strip()
        
        # API 호출 데이터 구성
        api_data = {
            "jql": jql,
            "startAt": 0,
            "maxResults": 10,
            "fields": ["summary", "status", "assignee", "priority"]
        }
        
        # API 호출
        response = self._call_api("/search", "POST", data=api_data)
        
        if "error" in response:
            return f"이슈 검색 오류: {response['error']}"
        
        # 결과 반환
        result = "## 이슈 검색 결과\n\n"
        result += f"검색 조건: `{jql}`\n\n"
        
        if "issues" not in response or not response["issues"]:
            return result + "검색 결과가 없습니다."
        
        for issue in response["issues"]:
            result += f"- **{issue.get('key', 'N/A')}**: {issue.get('fields', {}).get('summary', 'N/A')}\n"
            
            # 상태 정보
            status = issue.get('fields', {}).get('status', {}).get('name', 'N/A')
            result += f"  상태: {status}\n"
            
            # 담당자 정보
            assignee = issue.get('fields', {}).get('assignee', {})
            if assignee:
                result += f"  담당자: {assignee.get('displayName', assignee.get('name', 'N/A'))}\n"
            else:
                result += f"  담당자: 미할당\n"
            
            # 우선순위 정보
            priority = issue.get('fields', {}).get('priority', {}).get('name', 'N/A')
            result += f"  우선순위: {priority}\n"
            
            result += "\n"
        
        # 총 결과 수
        total = response.get("total", 0)
        if total > len(response["issues"]):
            result += f"\n**참고**: 총 {total}개 중 {len(response['issues'])}개 표시됨\n"
        
        return result
    
    def _get_issue_details(self, issue_key: str) -> str:
        """
        이슈 상세 조회
        
        Args:
            issue_key: 이슈 키
            
        Returns:
            이슈 상세 정보
        """
        response = self._call_api(f"/issue/{issue_key}", "GET")
        
        if "error" in response:
            return f"이슈 상세 조회 오류: {response['error']}"
        
        fields = response.get("fields", {})
        
        result = f"## 이슈 상세: {issue_key}\n\n"
        result += f"제목: {fields.get('summary', 'N/A')}\n"
        result += f"유형: {fields.get('issuetype', {}).get('name', 'N/A')}\n"
        
        # 프로젝트 정보
        project = fields.get("project", {})
        result += f"프로젝트: {project.get('name', 'N/A')} ({project.get('key', 'N/A')})\n"
        
        # 상태 정보
        result += f"상태: {fields.get('status', {}).get('name', 'N/A')}\n"
        
        # 담당자 & 보고자 정보
        assignee = fields.get("assignee", {})
        reporter = fields.get("reporter", {})
        
        if assignee:
            result += f"담당자: {assignee.get('displayName', assignee.get('name', 'N/A'))}\n"
        
        if reporter:
            result += f"보고자: {reporter.get('displayName', reporter.get('name', 'N/A'))}\n"
        
        # 우선순위 정보
        result += f"우선순위: {fields.get('priority', {}).get('name', 'N/A')}\n"
        
        # 날짜 정보
        result += f"생성일: {fields.get('created', 'N/A')}\n"
        result += f"수정일: {fields.get('updated', 'N/A')}\n"
        
        if "duedate" in fields and fields["duedate"]:
            result += f"마감일: {fields['duedate']}\n"
        
        # 라벨 정보
        if "labels" in fields and fields["labels"]:
            result += f"라벨: {', '.join(fields['labels'])}\n"
        
        # 컴포넌트 정보
        if "components" in fields and fields["components"]:
            components = [comp.get("name", "N/A") for comp in fields["components"]]
            result += f"컴포넌트: {', '.join(components)}\n"
        
        result += f"\n### 설명\n{fields.get('description', 'N/A')}\n"
        
        # 댓글 정보
        if "comment" in fields and "comments" in fields["comment"]:
            result += f"\n### 댓글 ({len(fields['comment']['comments'])}개)\n\n"
            
            for comment in fields["comment"]["comments"][:3]:  # 최대 3개만 표시
                author = comment.get("author", {}).get("displayName", "N/A")
                created = comment.get("created", "N/A")
                body = comment.get("body", "N/A")
                
                result += f"**{author}** ({created}):\n{body}\n\n"
            
            if len(fields["comment"]["comments"]) > 3:
                result += f"_...외 {len(fields['comment']['comments']) - 3}개 댓글_\n"
        
        return result