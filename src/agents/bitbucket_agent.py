"""
Bitbucket 에이전트 - 코드 저장소 관리 에이전트

이 모듈은 Bitbucket API를 통해 저장소 및 PR 관리 기능을 제공합니다.
"""

import uuid
import logging
import base64
import re
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple, Union

import config
from src.core.llm_service import llm_service

# 로깅 설정
logger = logging.getLogger("bitbucket_agent")

class BitbucketAgent:
    """Bitbucket 저장소 관리 에이전트"""
    
    def __init__(self):
        """Bitbucket 에이전트 초기화"""
        self.agent_id = f"bitbucket-{uuid.uuid4()}"
        
        # 설정 로드
        bitbucket_config = config.get_bitbucket_tool_config()
        self.enabled = bitbucket_config["enabled"]
        self.bitbucket_url = bitbucket_config["api_url"]
        self.username = bitbucket_config["username"]
        self.password = bitbucket_config["password"]
        self.timeout = bitbucket_config["timeout"]
        
        # 모크 모드 설정 (내부망 연결 불가능한 경우)
        self.mock_mode = True
        
        # 스키마 로드 (모크 모드에서 사용)
        self.schema_info = self._load_schema() if self.mock_mode else None
        
        # 모크 데이터 초기화
        if self.mock_mode:
            self._init_mock_data()
        
        logger.info(f"Bitbucket 에이전트 초기화: {self.agent_id} (활성화: {self.enabled}, 모크 모드: {self.mock_mode})")
    
    def run(self, query: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Bitbucket 작업 실행
        
        Args:
            query: 자연어 쿼리
            metadata: 추가 메타데이터 (저장소 정보 등)
            
        Returns:
            에이전트 응답
        """
        logger.info(f"Bitbucket 쿼리 실행: {query}")
        metadata = metadata or {}
        
        if not self.enabled:
            return self._format_response("오류: Bitbucket 도구가 비활성화되어 있습니다.")
        
        # 모크 모드인 경우 모크 API 호출
        if self.mock_mode:
            parsed_query = self._analyze_query(query, metadata)
            result = self._handle_mock_operation(parsed_query)
            
            # 모크 모드 안내 추가
            mock_note = "\n\n# 참고\n이 응답은 모크 모드로 생성되었으며, 실제 Bitbucket 인스턴스에 연결되지 않았습니다."
            if isinstance(result, str):
                result += mock_note
            elif isinstance(result, dict) and "content" in result:
                result["content"] += mock_note
            
            return self._format_response(result)
        
        # 실제 API 모드에서는 LLM을 통한 질의 처리
        # 저장소 정보 확인
        repo_info = metadata.get("repository", "")
        
        # 프롬프트 구성
        prompt = f"""Bitbucket 어시스턴트로서 저장소, 프로젝트, PR 관리를 도와줍니다.

{'저장소 정보:\n' + repo_info if repo_info else ''}

작업: {query}

다음 Bitbucket 작업을 지원합니다:
1. 저장소 목록 조회
2. 프로젝트 목록 조회
3. Pull Request 관리
4. 브랜치 관리
5. 커밋 히스토리 조회
6. 코드 검토 관리

요청을 분석하고 상세한 답변을 제공하세요.
"""
        
        # 메시지 구성
        messages = [llm_service.format_system_message(prompt)]
        
        # LLM 호출
        content = llm_service.generate(messages)
        
        # 오류 처리
        if isinstance(content, dict) and "error" in content:
            return self._format_response(f"에이전트 오류: {content['error']}")
        
        # API 연결 부재 안내 추가
        connection_note = "\n\n# 참고\n이 응답은 시뮬레이션된 것으로, 실제 Bitbucket 인스턴스에 연결되지 않았습니다."
        content = content + connection_note
        
        # 응답 반환
        return self._format_response(content)
    
    def _format_response(self, content: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """응답 형식화"""
        if isinstance(content, dict) and "content" in content:
            return {
                "content": content["content"],
                "model": llm_service.model_id,
                "agent_id": self.agent_id
            }
        return {
            "content": content if isinstance(content, str) else json.dumps(content, indent=2, ensure_ascii=False),
            "model": llm_service.model_id,
            "agent_id": self.agent_id
        }
    
    def _get_bitbucket_headers(self) -> Dict[str, str]:
        """Bitbucket API 헤더 생성 - Basic 인증 사용"""
        auth_str = f"{self.username}:{self.password}"
        auth_token = base64.b64encode(auth_str.encode()).decode()
        
        return {
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth_token}"
        }
    
    def _load_schema(self) -> Dict[str, Any]:
        """스키마 파일 로드"""
        schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "schema", "bitbucket.json")
        try:
            with open(schema_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except Exception as e:
            logger.error(f"스키마 로드 오류: {e}")
            return {}
    
    def _init_mock_data(self) -> None:
        """모크 데이터 초기화"""
        # 프로젝트 데이터
        self.mock_projects = {
            "TEST": {
                "key": "TEST",
                "name": "Test Project",
                "description": "This is a test project",
                "public": True,
                "type": "NORMAL",
                "id": 1001
            },
            "MOBILE": {
                "key": "MOBILE",
                "name": "Mobile Applications",
                "description": "All mobile application repositories",
                "public": False,
                "type": "NORMAL",
                "id": 1002
            },
            "BACKEND": {
                "key": "BACKEND",
                "name": "Backend Services",
                "description": "Backend service repositories",
                "public": False,
                "type": "NORMAL",
                "id": 1003
            },
            "WEB": {
                "key": "WEB",
                "name": "Web Applications",
                "description": "Web application repositories",
                "public": False,
                "type": "NORMAL",
                "id": 1004
            },
            "DOCS": {
                "key": "DOCS",
                "name": "Documentation",
                "description": "Project documentation",
                "public": True,
                "type": "NORMAL",
                "id": 1005
            }
        }
        
        # 저장소 데이터
        self.mock_repositories = {
            "TEST": {
                "my-repo": {
                    "slug": "my-repo",
                    "name": "My Repository",
                    "description": "This is a test repository",
                    "scmId": "git",
                    "public": True,
                    "forkable": True,
                    "id": 2001,
                    "project": {"key": "TEST"},
                    "updated_date": "2023-04-15"
                },
                "utils": {
                    "slug": "utils",
                    "name": "Utils",
                    "description": "Common utilities",
                    "scmId": "git",
                    "public": True,
                    "forkable": True,
                    "id": 2002,
                    "project": {"key": "TEST"},
                    "updated_date": "2023-03-20"
                },
                "documentation": {
                    "slug": "documentation",
                    "name": "Documentation",
                    "description": "Project documentation",
                    "scmId": "git",
                    "public": True,
                    "forkable": True,
                    "id": 2003,
                    "project": {"key": "TEST"},
                    "updated_date": "2023-04-10"
                }
            },
            "MOBILE": {
                "mobile-app": {
                    "slug": "mobile-app",
                    "name": "Mobile App",
                    "description": "Main mobile application",
                    "scmId": "git",
                    "public": False,
                    "forkable": True,
                    "id": 2004,
                    "project": {"key": "MOBILE"},
                    "updated_date": "2023-04-18"
                }
            },
            "BACKEND": {
                "api": {
                    "slug": "api",
                    "name": "API",
                    "description": "Main API for backend services",
                    "scmId": "git",
                    "public": False,
                    "forkable": True,
                    "id": 2005,
                    "project": {"key": "BACKEND"},
                    "updated_date": "2023-04-20"
                },
                "auth-service": {
                    "slug": "auth-service",
                    "name": "Authentication Service",
                    "description": "User authentication and authorization service",
                    "scmId": "git",
                    "public": False,
                    "forkable": True,
                    "id": 2006,
                    "project": {"key": "BACKEND"},
                    "updated_date": "2023-04-19"
                },
                "backend-api": {
                    "slug": "backend-api",
                    "name": "Backend API",
                    "description": "API for backend services",
                    "scmId": "git",
                    "public": False,
                    "forkable": True,
                    "id": 2007,
                    "project": {"key": "BACKEND"},
                    "updated_date": "2023-04-17"
                }
            },
            "WEB": {
                "web-client": {
                    "slug": "web-client",
                    "name": "Web Client",
                    "description": "Web client application",
                    "scmId": "git",
                    "public": False,
                    "forkable": True,
                    "id": 2008,
                    "project": {"key": "WEB"},
                    "updated_date": "2023-04-16"
                }
            },
            "DOCS": {
                "documentation": {
                    "slug": "documentation",
                    "name": "Documentation",
                    "description": "Project documentation",
                    "scmId": "git",
                    "public": True,
                    "forkable": True,
                    "id": 2009,
                    "project": {"key": "DOCS"},
                    "updated_date": "2023-04-14"
                }
            }
        }
        
        # Pull Request 데이터
        self.mock_pull_requests = {
            "MOBILE": {
                "mobile-app": [
                    {
                        "id": 25,
                        "title": "Add push notification support",
                        "description": "Implements push notification functionality for both Android and iOS",
                        "state": "OPEN",
                        "created_date": "2023-04-12",
                        "author": {"name": "John Smith", "email": "john.smith@example.com"},
                        "fromRef": {"id": "refs/heads/feature/push-notifications"},
                        "toRef": {"id": "refs/heads/master"},
                        "reviewers": [
                            {"user": {"name": "Alice Johnson"}, "status": "APPROVED"},
                            {"user": {"name": "Bob Williams"}, "status": "UNAPPROVED"}
                        ],
                        "version": 2
                    },
                    {
                        "id": 28,
                        "title": "Fix login screen crash",
                        "description": "Fixes a crash on the login screen when using biometric authentication",
                        "state": "OPEN",
                        "created_date": "2023-04-14",
                        "author": {"name": "Sarah Davis", "email": "sarah.davis@example.com"},
                        "fromRef": {"id": "refs/heads/bugfix/login-crash"},
                        "toRef": {"id": "refs/heads/master"},
                        "reviewers": [
                            {"user": {"name": "John Smith"}, "status": "APPROVED"},
                            {"user": {"name": "Alice Johnson"}, "status": "UNAPPROVED"}
                        ],
                        "version": 1
                    }
                ]
            },
            "BACKEND": {
                "backend-api": [
                    {
                        "id": 42,
                        "title": "Add user profile endpoints",
                        "description": "Adds endpoints for retrieving and updating user profiles",
                        "state": "OPEN",
                        "created_date": "2023-04-20",
                        "author": {"name": "David Wilson", "email": "david.wilson@example.com"},
                        "fromRef": {"id": "refs/heads/feature/user-profile-endpoints"},
                        "toRef": {"id": "refs/heads/master"},
                        "reviewers": [
                            {"user": {"name": "Emily Chen"}, "status": "UNAPPROVED"},
                            {"user": {"name": "Michael Brown"}, "status": "UNAPPROVED"}
                        ],
                        "version": 3
                    }
                ]
            }
        }
        
        # 브랜치 데이터
        self.mock_branches = {
            "TEST": {
                "my-repo": [
                    {"id": "refs/heads/master", "displayId": "master", "isDefault": True},
                    {"id": "refs/heads/develop", "displayId": "develop", "isDefault": False},
                    {"id": "refs/heads/feature/new-feature", "displayId": "feature/new-feature", "isDefault": False}
                ]
            },
            "MOBILE": {
                "mobile-app": [
                    {"id": "refs/heads/master", "displayId": "master", "isDefault": True},
                    {"id": "refs/heads/develop", "displayId": "develop", "isDefault": False},
                    {"id": "refs/heads/feature/push-notifications", "displayId": "feature/push-notifications", "isDefault": False},
                    {"id": "refs/heads/bugfix/login-crash", "displayId": "bugfix/login-crash", "isDefault": False}
                ]
            },
            "BACKEND": {
                "api": [
                    {"id": "refs/heads/master", "displayId": "master", "isDefault": True},
                    {"id": "refs/heads/develop", "displayId": "develop", "isDefault": False}
                ],
                "auth-service": [
                    {"id": "refs/heads/master", "displayId": "master", "isDefault": True},
                    {"id": "refs/heads/develop", "displayId": "develop", "isDefault": False},
                    {"id": "refs/heads/feature/user-auth", "displayId": "feature/user-auth", "isDefault": False}
                ],
                "backend-api": [
                    {"id": "refs/heads/master", "displayId": "master", "isDefault": True},
                    {"id": "refs/heads/feature/user-profile-endpoints", "displayId": "feature/user-profile-endpoints", "isDefault": False}
                ]
            },
            "WEB": {
                "web-client": [
                    {"id": "refs/heads/master", "displayId": "master", "isDefault": True},
                    {"id": "refs/heads/develop", "displayId": "develop", "isDefault": False}
                ]
            }
        }
        
        # 커밋 데이터
        self.mock_commits = {
            "BACKEND": {
                "api": [
                    {
                        "id": "abcdef1",
                        "message": "Fix rate limiting issue",
                        "author": {"name": "Emily Chen", "email": "emily.chen@example.com"},
                        "date": "2023-04-15 14:23",
                        "parents": ["bcdefa2"],
                        "files_changed": 3,
                        "additions": 47,
                        "deletions": 12
                    },
                    {
                        "id": "bcdefa2",
                        "message": "Add pagination to user endpoints",
                        "author": {"name": "David Wilson", "email": "david.wilson@example.com"},
                        "date": "2023-04-14 16:45",
                        "parents": ["cdefab3"],
                        "files_changed": 5,
                        "additions": 124,
                        "deletions": 37
                    },
                    {
                        "id": "cdefab3",
                        "message": "Update authentication middleware",
                        "author": {"name": "John Smith", "email": "john.smith@example.com"},
                        "date": "2023-04-13 11:12",
                        "parents": ["defabc4"],
                        "files_changed": 2,
                        "additions": 31,
                        "deletions": 15
                    },
                    {
                        "id": "defabc4",
                        "message": "Add documentation for new endpoints",
                        "author": {"name": "Sarah Davis", "email": "sarah.davis@example.com"},
                        "date": "2023-04-12 09:55",
                        "parents": ["efabcd5"],
                        "files_changed": 7,
                        "additions": 235,
                        "deletions": 0
                    },
                    {
                        "id": "efabcd5",
                        "message": "Fix security vulnerability in auth endpoint",
                        "author": {"name": "Michael Brown", "email": "michael.brown@example.com"},
                        "date": "2023-04-10 17:30",
                        "parents": ["123abc456"],
                        "files_changed": 1,
                        "additions": 8,
                        "deletions": 3
                    }
                ]
            }
        }
        
        # 파일 데이터
        self.mock_files = {
            "DOCS": {
                "documentation": {
                    "README.md": """# Company Documentation

This repository contains the official documentation for all company projects.

## Getting Started

To build the documentation locally:

1. Install dependencies: `npm install`
2. Start the development server: `npm start`
3. Visit http://localhost:8000 to view the documentation

## Contributing

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute to this documentation.

## License

This documentation is copyright © Company Name 2023.
"""
                }
            }
        }
    
    def _analyze_query(self, query: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """쿼리 분석"""
        result = {
            "original_query": query,
            "operation": None,
            "project_key": None,
            "repo_slug": None,
            "parameters": {}
        }
        
        # 프로젝트 키 추출
        project_key_match = re.search(r'(?:in|for|from|to)\s+(?:the\s+)?(?:\'|\")?([A-Z]+)(?:\'|\")?\s+project', query, re.IGNORECASE)
        if project_key_match:
            result["project_key"] = project_key_match.group(1).upper()
        elif "project_key" in metadata:
            result["project_key"] = metadata["project_key"]
        
        # 저장소 슬러그 추출
        repo_slug_match = re.search(r'(?:in|for|from|to)\s+(?:the\s+)?(?:\'|\")?([a-zA-Z0-9\-]+)(?:\'|\")?\s+(?:repo|repository)', query, re.IGNORECASE)
        if repo_slug_match:
            result["repo_slug"] = repo_slug_match.group(1).lower()
        elif "repo_slug" in metadata:
            result["repo_slug"] = metadata["repo_slug"]
        
        # 브랜치 이름 추출
        branch_match = re.search(r'branch\s+(?:\'|\")?([a-zA-Z0-9\-\/]+)(?:\'|\")?', query, re.IGNORECASE)
        if branch_match:
            result["parameters"]["branch"] = branch_match.group(1)
        
        # PR ID 추출
        pr_match = re.search(r'(?:pull request|PR)\s+#?(\d+)', query, re.IGNORECASE)
        if pr_match:
            result["parameters"]["pull_request_id"] = int(pr_match.group(1))
        
        # 태그 이름 추출
        tag_match = re.search(r'tag\s+(?:\'|\")?([a-zA-Z0-9\-\.]+)(?:\'|\")?', query, re.IGNORECASE)
        if tag_match:
            result["parameters"]["tag"] = tag_match.group(1)
        
        # 커밋 ID 추출
        commit_match = re.search(r'commit\s+(?:\'|\")?([a-zA-Z0-9]+)(?:\'|\")?', query, re.IGNORECASE)
        if commit_match:
            result["parameters"]["commit_id"] = commit_match.group(1)
        
        # 작업 유형 결정
        if 'list' in query.lower() and 'repositories' in query.lower():
            result["operation"] = "get_repositories"
        elif 'list' in query.lower() and 'projects' in query.lower():
            result["operation"] = "get_projects"
        elif ('create' in query.lower() or 'new' in query.lower()) and 'repository' in query.lower():
            result["operation"] = "create_repository"
            name_match = re.search(r'(?:called|named)\s+(?:\'|\")?([a-zA-Z0-9\-]+)(?:\'|\")?', query, re.IGNORECASE)
            if name_match:
                result["parameters"]["name"] = name_match.group(1)
        elif ('create' in query.lower() or 'new' in query.lower()) and 'branch' in query.lower():
            result["operation"] = "create_branch"
            result["parameters"]["startPoint"] = "master"  # 기본값
            start_point_match = re.search(r'from\s+(?:\'|\")?([a-zA-Z0-9\-\/]+)(?:\'|\")?', query, re.IGNORECASE)
            if start_point_match:
                result["parameters"]["startPoint"] = start_point_match.group(1)
        elif ('create' in query.lower() or 'new' in query.lower()) and ('pull request' in query.lower() or 'PR' in query.lower()):
            result["operation"] = "create_pull_request"
            result["parameters"]["title"] = f"Pull request from {result['parameters'].get('branch', 'feature_branch')}"
            from_branch_match = re.search(r'from\s+(?:\'|\")?([a-zA-Z0-9\-\/]+)(?:\'|\")?', query, re.IGNORECASE)
            if from_branch_match:
                result["parameters"]["fromRef"] = f"refs/heads/{from_branch_match.group(1)}"
            to_branch_match = re.search(r'(?:into|to)\s+(?:\'|\")?([a-zA-Z0-9\-\/]+)(?:\'|\")?', query, re.IGNORECASE)
            if to_branch_match:
                result["parameters"]["toRef"] = f"refs/heads/{to_branch_match.group(1)}"
            else:
                result["parameters"]["toRef"] = "refs/heads/master"
        elif ('show' in query.lower() or 'get' in query.lower()) and 'pull requests' in query.lower():
            result["operation"] = "get_pull_requests"
            state_match = re.search(r'(open|closed|all|merged)\s+pull\s+requests', query, re.IGNORECASE)
            if state_match:
                result["parameters"]["state"] = state_match.group(1).upper()
        elif ('show' in query.lower() or 'get' in query.lower()) and 'pull request' in query.lower() and 'pull_request_id' in result["parameters"]:
            result["operation"] = "get_pull_request"
        elif ('approve' in query.lower()) and ('pull request' in query.lower() or 'PR' in query.lower()):
            result["operation"] = "approve_pull_request"
        elif ('merge' in query.lower()) and ('pull request' in query.lower() or 'PR' in query.lower()):
            result["operation"] = "merge_pull_request"
            result["parameters"]["version"] = 1
            result["parameters"]["message"] = f"Merged pull request #{result['parameters'].get('pull_request_id', '0')}"
        elif ('show' in query.lower() or 'get' in query.lower() or 'list' in query.lower()) and 'branches' in query.lower():
            result["operation"] = "get_branches"
        elif ('create' in query.lower() or 'new' in query.lower()) and 'tag' in query.lower():
            result["operation"] = "create_tag"
            result["parameters"]["startPoint"] = "master"  # 기본값
        elif ('show' in query.lower() or 'get' in query.lower()) and ('README' in query or 'readme' in query):
            result["operation"] = "get_file_content"
            result["parameters"]["path"] = "README.md"
        elif ('show' in query.lower() or 'get' in query.lower() or 'recent' in query.lower()) and 'commits' in query.lower():
            result["operation"] = "get_commits"
        elif 'compare' in query.lower() and 'branches' in query.lower():
            result["operation"] = "compare_branches"
            branches = re.findall(r'(?:\'|\")?([a-zA-Z0-9\-\/]+)(?:\'|\")?', query)
            if len(branches) >= 2:
                result["parameters"]["from"] = branches[0]
                result["parameters"]["to"] = branches[1]
        
        return result
    
    def _handle_mock_operation(self, parsed_query: Dict[str, Any]) -> Union[str, Dict[str, Any]]:
        """모크 작업 처리"""
        operation = parsed_query.get("operation")
        project_key = parsed_query.get("project_key")
        repo_slug = parsed_query.get("repo_slug")
        parameters = parsed_query.get("parameters", {})
        
        if not operation:
            return "잘못된 작업입니다. 지원되는 Bitbucket 작업을 요청해주세요."
        
        # 프로젝트 관련 작업
        if operation == "get_projects":
            return self._get_mock_projects()
        
        # 저장소 관련 작업
        if operation == "get_repositories":
            if not project_key:
                return "저장소 조회를 위해 프로젝트 키가 필요합니다."
            return self._get_mock_repositories(project_key)
        
        if operation == "create_repository":
            if not project_key:
                return "저장소 생성을 위해 프로젝트 키가 필요합니다."
            if "name" not in parameters:
                return "저장소 생성을 위해 이름이 필요합니다."
            return self._create_mock_repository(project_key, parameters["name"])
        
        # 브랜치 관련 작업
        if operation == "get_branches":
            if not project_key or not repo_slug:
                return "브랜치 조회를 위해 프로젝트 키와 저장소 슬러그가 필요합니다."
            return self._get_mock_branches(project_key, repo_slug)
        
        if operation == "create_branch":
            if not project_key or not repo_slug:
                return "브랜치 생성을 위해 프로젝트 키와 저장소 슬러그가 필요합니다."
            if "branch" not in parameters:
                return "브랜치 생성을 위해 브랜치 이름이 필요합니다."
            return self._create_mock_branch(project_key, repo_slug, parameters["branch"], parameters.get("startPoint", "master"))
        
        # Pull Request 관련 작업
        if operation == "get_pull_requests":
            if not project_key or not repo_slug:
                return "PR 조회를 위해 프로젝트 키와 저장소 슬러그가 필요합니다."
            return self._get_mock_pull_requests(project_key, repo_slug, parameters.get("state", "OPEN"))
        
        if operation == "get_pull_request":
            if not project_key or not repo_slug:
                return "PR 조회를 위해 프로젝트 키와 저장소 슬러그가 필요합니다."
            if "pull_request_id" not in parameters:
                return "PR 조회를 위해 PR ID가 필요합니다."
            return self._get_mock_pull_request(project_key, repo_slug, parameters["pull_request_id"])
        
        if operation == "create_pull_request":
            if not project_key or not repo_slug:
                return "PR 생성을 위해 프로젝트 키와 저장소 슬러그가 필요합니다."
            if "fromRef" not in parameters or "toRef" not in parameters:
                return "PR 생성을 위해 소스 브랜치와 대상 브랜치가 필요합니다."
            return self._create_mock_pull_request(project_key, repo_slug, parameters)
        
        if operation == "approve_pull_request":
            if not project_key or not repo_slug:
                return "PR 승인을 위해 프로젝트 키와 저장소 슬러그가 필요합니다."
            if "pull_request_id" not in parameters:
                return "PR 승인을 위해 PR ID가 필요합니다."
            return self._approve_mock_pull_request(project_key, repo_slug, parameters["pull_request_id"])
        
        if operation == "merge_pull_request":
            if not project_key or not repo_slug:
                return "PR 병합을 위해 프로젝트 키와 저장소 슬러그가 필요합니다."
            if "pull_request_id" not in parameters:
                return "PR 병합을 위해 PR ID가 필요합니다."
            return self._merge_mock_pull_request(project_key, repo_slug, parameters["pull_request_id"], parameters.get("version", 1), parameters.get("message", ""))
        
        # 커밋 관련 작업
        if operation == "get_commits":
            if not project_key or not repo_slug:
                return "커밋 조회를 위해 프로젝트 키와 저장소 슬러그가 필요합니다."
            return self._get_mock_commits(project_key, repo_slug, parameters.get("limit", 5))
        
        # 파일 관련 작업
        if operation == "get_file_content":
            if not project_key or not repo_slug:
                return "파일 내용 조회를 위해 프로젝트 키와 저장소 슬러그가 필요합니다."
            if "path" not in parameters:
                return "파일 내용 조회를 위해 파일 경로가 필요합니다."
            return self._get_mock_file_content(project_key, repo_slug, parameters["path"])
        
        # 태그 관련 작업
        if operation == "create_tag":
            if not project_key or not repo_slug:
                return "태그 생성을 위해 프로젝트 키와 저장소 슬러그가 필요합니다."
            if "tag" not in parameters:
                return "태그 생성을 위해 태그 이름이 필요합니다."
            return self._create_mock_tag(project_key, repo_slug, parameters["tag"], parameters.get("startPoint", "master"), parameters.get("message", ""))
        
        # 브랜치 비교
        if operation == "compare_branches":
            if not project_key or not repo_slug:
                return "브랜치 비교를 위해 프로젝트 키와 저장소 슬러그가 필요합니다."
            if "from" not in parameters or "to" not in parameters:
                return "브랜치 비교를 위해 소스 브랜치와 대상 브랜치가 필요합니다."
            return self._compare_mock_branches(project_key, repo_slug, parameters["from"], parameters["to"])
        
        return f"지원되지 않는 작업입니다: {operation}"
    
    def _get_mock_projects(self) -> str:
        """모크 프로젝트 조회"""
        projects = list(self.mock_projects.values())
        result = "프로젝트 목록:\n\n"
        
        for project in projects:
            result += f"1. {project['name']} ({project['key']})\n"
            result += f"   - 설명: {project['description']}\n"
            result += f"   - 공개: {'예' if project['public'] else '아니오'}\n\n"
        
        return result
    
    def _get_mock_repositories(self, project_key: str) -> str:
        """모크 저장소 조회"""
        if project_key not in self.mock_repositories:
            return f"프로젝트 '{project_key}'를 찾을 수 없습니다."
        
        repositories = self.mock_repositories[project_key]
        result = f"{project_key} 프로젝트의 모든 저장소:\n\n"
        
        for i, repo in enumerate(repositories.values(), 1):
            result += f"{i}. {repo['name']} ({repo['scmId']})\n"
            result += f"   - 설명: {repo['description']}\n"
            result += f"   - 마지막 업데이트: {repo['updated_date']}\n"
        
        return result
    
    def _create_mock_repository(self, project_key: str, name: str) -> str:
        """모크 저장소 생성"""
        if project_key not in self.mock_projects:
            return f"프로젝트 '{project_key}'를 찾을 수 없습니다."
        
        slug = name.lower().replace(" ", "-")
        
        if project_key in self.mock_repositories and slug in self.mock_repositories[project_key]:
            return f"저장소 '{slug}'는 이미 {project_key} 프로젝트에 존재합니다."
        
        if project_key not in self.mock_repositories:
            self.mock_repositories[project_key] = {}
        
        self.mock_repositories[project_key][slug] = {
            "slug": slug,
            "name": name,
            "description": f"Repository for {name}",
            "scmId": "git",
            "public": False,
            "forkable": True,
            "id": 3000 + len(self.mock_repositories[project_key]),
            "project": {"key": project_key},
            "updated_date": datetime.now().strftime("%Y-%m-%d")
        }
        
        return f"{project_key} 프로젝트에 '{name}' 저장소를 생성했습니다.\n\n저장소가 성공적으로 생성되었습니다! 다음을 사용하여 복제할 수 있습니다:\ngit clone https://bitbucket.org/company/{project_key}/{slug}.git"
    
    def _get_mock_branches(self, project_key: str, repo_slug: str) -> str:
        """모크 브랜치 조회"""
        if project_key not in self.mock_branches or repo_slug not in self.mock_branches.get(project_key, {}):
            return f"프로젝트 '{project_key}'의 저장소 '{repo_slug}'를 찾을 수 없거나 브랜치가 없습니다."
        
        branches = self.mock_branches[project_key][repo_slug]
        result = f"{project_key}/{repo_slug} 저장소의 브랜치:\n\n"
        
        for i, branch in enumerate(branches, 1):
            result += f"{i}. {branch['displayId']}"
            if branch['isDefault']:
                result += " (기본 브랜치)"
            result += "\n"
        
        return result
    
    def _create_mock_branch(self, project_key: str, repo_slug: str, branch_name: str, start_point: str) -> str:
        """모크 브랜치 생성"""
        if project_key not in self.mock_branches or repo_slug not in self.mock_branches.get(project_key, {}):
            return f"프로젝트 '{project_key}'의 저장소 '{repo_slug}'를 찾을 수 없습니다."
        
        # 시작점 브랜치 존재 여부 확인
        start_point_exists = False
        for branch in self.mock_branches[project_key][repo_slug]:
            if branch["displayId"] == start_point:
                start_point_exists = True
                break
        
        if not start_point_exists:
            return f"시작점 브랜치 '{start_point}'를 찾을 수 없습니다."
        
        # 이미 존재하는 브랜치인지 확인
        for branch in self.mock_branches[project_key][repo_slug]:
            if branch["displayId"] == branch_name:
                return f"브랜치 '{branch_name}'은(는) 이미 존재합니다."
        
        # 새 브랜치 추가
        self.mock_branches[project_key][repo_slug].append({
            "id": f"refs/heads/{branch_name}",
            "displayId": branch_name,
            "isDefault": False
        })
        
        return f"브랜치가 성공적으로 생성되었습니다! '{branch_name}' 브랜치가 '{start_point}' 브랜치에서 생성되었습니다. 다음을 사용하여 체크아웃할 수 있습니다:\ngit checkout {branch_name}"
    
    def _get_mock_pull_requests(self, project_key: str, repo_slug: str, state: str = "OPEN") -> str:
        """모크 PR 조회"""
        if project_key not in self.mock_pull_requests or repo_slug not in self.mock_pull_requests.get(project_key, {}):
            return f"프로젝트 '{project_key}'의 저장소 '{repo_slug}'에 PR이 없습니다."
        
        pull_requests = [pr for pr in self.mock_pull_requests[project_key][repo_slug] if state == "ALL" or pr["state"] == state]
        
        if not pull_requests:
            return f"프로젝트 '{project_key}'의 저장소 '{repo_slug}'에 {state.lower()} 상태의 PR이 없습니다."
        
        result = f"{project_key}/{repo_slug} 저장소의 {state.lower()} PR:\n\n"
        
        for pr in pull_requests:
            result += f"1. PR #{pr['id']}: \"{pr['title']}\" by {pr['author']['name']}\n"
            result += f"   - 생성: {pr['created_date']}\n"
            result += f"   - From: {pr['fromRef']['id'].replace('refs/heads/', '')} -> {pr['toRef']['id'].replace('refs/heads/', '')}\n"
            reviewers = [f"{reviewer['user']['name']} ({'승인됨' if reviewer['status'] == 'APPROVED' else '보류 중'})" for reviewer in pr["reviewers"]]
            result += f"   - 리뷰어: {', '.join(reviewers)}\n\n"
        
        return result
    
    def _get_mock_pull_request(self, project_key: str, repo_slug: str, pull_request_id: int) -> str:
        """모크 PR 상세 조회"""
        if project_key not in self.mock_pull_requests or repo_slug not in self.mock_pull_requests.get(project_key, {}):
            return f"프로젝트 '{project_key}'의 저장소 '{repo_slug}'에 PR이 없습니다."
        
        pull_request = None
        for pr in self.mock_pull_requests[project_key][repo_slug]:
            if pr["id"] == pull_request_id:
                pull_request = pr
                break
        
        if not pull_request:
            return f"PR #{pull_request_id}을(를) 찾을 수 없습니다."
        
        result = f"PR #{pull_request['id']}: {pull_request['title']}\n\n"
        result += f"설명: {pull_request['description']}\n\n"
        result += f"상태: {pull_request['state']}\n"
        result += f"생성일: {pull_request['created_date']}\n"
        result += f"작성자: {pull_request['author']['name']} ({pull_request['author']['email']})\n\n"
        result += f"소스 브랜치: {pull_request['fromRef']['id'].replace('refs/heads/', '')}\n"
        result += f"대상 브랜치: {pull_request['toRef']['id'].replace('refs/heads/', '')}\n\n"
        
        result += "리뷰어:\n"
        for reviewer in pull_request["reviewers"]:
            result += f"- {reviewer['user']['name']}: {'승인됨' if reviewer['status'] == 'APPROVED' else '보류 중'}\n"
        
        return result
    
    def _create_mock_pull_request(self, project_key: str, repo_slug: str, parameters: Dict[str, Any]) -> str:
        """모크 PR 생성"""
        if project_key not in self.mock_repositories or repo_slug not in self.mock_repositories.get(project_key, {}):
            return f"프로젝트 '{project_key}'의 저장소 '{repo_slug}'를 찾을 수 없습니다."
        
        # 소스 브랜치와 대상 브랜치 존재 여부 확인은 생략 (모크 데이터임)
        
        if project_key not in self.mock_pull_requests:
            self.mock_pull_requests[project_key] = {}
        
        if repo_slug not in self.mock_pull_requests[project_key]:
            self.mock_pull_requests[project_key][repo_slug] = []
        
        title = parameters.get("title", "New pull request")
        description = parameters.get("description", "This is a new pull request")
        fromRef = parameters.get("fromRef", "refs/heads/feature/new-feature")
        toRef = parameters.get("toRef", "refs/heads/master")
        
        pull_request_id = 100 + len(self.mock_pull_requests[project_key][repo_slug])
        
        # 새 PR 생성
        self.mock_pull_requests[project_key][repo_slug].append({
            "id": pull_request_id,
            "title": title,
            "description": description,
            "state": "OPEN",
            "created_date": datetime.now().strftime("%Y-%m-%d"),
            "author": {"name": "Current User", "email": "user@example.com"},
            "fromRef": {"id": fromRef},
            "toRef": {"id": toRef},
            "reviewers": [
                {"user": {"name": "Auto Reviewer 1"}, "status": "UNAPPROVED"},
                {"user": {"name": "Auto Reviewer 2"}, "status": "UNAPPROVED"}
            ],
            "version": 1
        })
        
        result = f"PR을 생성하겠습니다: {title}.\n\n"
        result += "풀 리퀘스트가 성공적으로 생성되었습니다!\n\n"
        result += f"PR #{pull_request_id}: \"{title}\"\n"
        result += f"설명: {description}\n\n"
        result += "저장소 설정에 따라 리뷰어가 자동으로 추가되었습니다. 다음에서 PR을 볼 수 있습니다: "
        result += f"https://bitbucket.org/company/{project_key}/{repo_slug}/pull-requests/{pull_request_id}"
        
        return result
    
    def _approve_mock_pull_request(self, project_key: str, repo_slug: str, pull_request_id: int) -> str:
        """모크 PR 승인"""
        if project_key not in self.mock_pull_requests or repo_slug not in self.mock_pull_requests.get(project_key, {}):
            return f"프로젝트 '{project_key}'의 저장소 '{repo_slug}'에 PR이 없습니다."
        
        pull_request = None
        pr_index = -1
        for i, pr in enumerate(self.mock_pull_requests[project_key][repo_slug]):
            if pr["id"] == pull_request_id:
                pull_request = pr
                pr_index = i
                break
        
        if not pull_request:
            return f"PR #{pull_request_id}을(를) 찾을 수 없습니다."
        
        if pull_request["state"] != "OPEN":
            return f"PR #{pull_request_id}은(는) OPEN 상태가 아니므로 승인할 수 없습니다."
        
        # 현재 사용자를 승인자로 설정
        current_user = {"user": {"name": "Current User"}, "status": "APPROVED"}
        reviewer_found = False
        
        for i, reviewer in enumerate(pull_request["reviewers"]):
            if reviewer["user"]["name"] == "Current User":
                pull_request["reviewers"][i]["status"] = "APPROVED"
                reviewer_found = True
                break
        
        if not reviewer_found:
            pull_request["reviewers"].append(current_user)
        
        self.mock_pull_requests[project_key][repo_slug][pr_index] = pull_request
        
        return f"PR #{pull_request_id} \"{pull_request['title']}\"가 성공적으로 승인되었습니다. 승인과 함께 다음 메시지를 남겼습니다: \"코드가 좋아 보이고 테스트가 통과되었습니다. 병합할 준비가 되었습니다.\""
    
    def _merge_mock_pull_request(self, project_key: str, repo_slug: str, pull_request_id: int, version: int, message: str) -> str:
        """모크 PR 병합"""
        if project_key not in self.mock_pull_requests or repo_slug not in self.mock_pull_requests.get(project_key, {}):
            return f"프로젝트 '{project_key}'의 저장소 '{repo_slug}'에 PR이 없습니다."
        
        pull_request = None
        pr_index = -1
        for i, pr in enumerate(self.mock_pull_requests[project_key][repo_slug]):
            if pr["id"] == pull_request_id:
                pull_request = pr
                pr_index = i
                break
        
        if not pull_request:
            return f"PR #{pull_request_id}을(를) 찾을 수 없습니다."
        
        if pull_request["state"] != "OPEN":
            return f"PR #{pull_request_id}은(는) 이미 {pull_request['state']} 상태입니다."
        
        if pull_request["version"] != version:
            return f"PR #{pull_request_id}의 버전이 일치하지 않습니다. 현재 버전: {pull_request['version']}, 요청 버전: {version}"
        
        # PR 상태 변경
        pull_request["state"] = "MERGED"
        self.mock_pull_requests[project_key][repo_slug][pr_index] = pull_request
        
        target_branch = pull_request["toRef"]["id"].replace("refs/heads/", "")
        commit_id = "".join([f"{i}{chr(97 + i)}" for i in range(8)])
        
        result = f"PR #{pull_request_id} \"{pull_request['title']}\"가 {target_branch} 브랜치로 성공적으로 병합되었습니다. 병합 커밋은 {commit_id}입니다.\n\n"
        result += "저장소 설정에 따라 기능 브랜치가 자동으로 삭제되었습니다."
        
        return result
    
    def _get_mock_commits(self, project_key: str, repo_slug: str, limit: int = 5) -> str:
        """모크 커밋 조회"""
        if project_key not in self.mock_commits or repo_slug not in self.mock_commits.get(project_key, {}):
            return f"프로젝트 '{project_key}'의 저장소 '{repo_slug}'에 커밋이 없습니다."
        
        commits = self.mock_commits[project_key][repo_slug][:limit]
        
        result = f"{repo_slug} 저장소의 최근 커밋:\n\n"
        
        for i, commit in enumerate(commits, 1):
            result += f"{i}. 커밋 {commit['id']}: \"{commit['message']}\" by {commit['author']['name']} ({commit['date']})\n"
            result += f"   - {commit['files_changed']}개 파일 변경, {commit['additions']}개 추가, {commit['deletions']}개 삭제\n\n"
        
        return result
    
    def _get_mock_file_content(self, project_key: str, repo_slug: str, path: str) -> str:
        """모크 파일 내용 조회"""
        if project_key not in self.mock_files or repo_slug not in self.mock_files.get(project_key, {}) or path not in self.mock_files[project_key][repo_slug]:
            if path == "README.md":
                return f"{repo_slug} 저장소의 README.md 파일 내용:\n\n# {repo_slug.capitalize()}\n\n이 저장소는 모크 데이터로, README.md 파일 내용을 생성했습니다."
            return f"프로젝트 '{project_key}'의 저장소 '{repo_slug}'에서 파일 '{path}'를 찾을 수 없습니다."
        
        content = self.mock_files[project_key][repo_slug][path]
        return f"{repo_slug} 저장소의 {path} 파일 내용:\n\n{content}"
    
    def _create_mock_tag(self, project_key: str, repo_slug: str, tag_name: str, start_point: str, message: str) -> str:
        """모크 태그 생성"""
        if project_key not in self.mock_repositories or repo_slug not in self.mock_repositories.get(project_key, {}):
            return f"프로젝트 '{project_key}'의 저장소 '{repo_slug}'를 찾을 수 없습니다."
        
        if not message:
            message = f"태그 {tag_name} 생성"
        
        return f"태그 '{tag_name}'이(가) 커밋 {start_point}에 대해 성공적으로 생성되었습니다. 태그에는 다음 메시지가 포함됩니다: \"{message}\""
    
    def _compare_mock_branches(self, project_key: str, repo_slug: str, from_branch: str, to_branch: str) -> str:
        """모크 브랜치 비교"""
        if project_key not in self.mock_branches or repo_slug not in self.mock_branches.get(project_key, {}):
            return f"프로젝트 '{project_key}'의 저장소 '{repo_slug}'를 찾을 수 없거나 브랜치가 없습니다."
        
        # 브랜치 존재 여부 확인
        from_exists = False
        to_exists = False
        
        for branch in self.mock_branches[project_key][repo_slug]:
            if branch["displayId"] == from_branch:
                from_exists = True
            if branch["displayId"] == to_branch:
                to_exists = True
        
        if not from_exists:
            return f"브랜치 '{from_branch}'를 찾을 수 없습니다."
        
        if not to_exists:
            return f"브랜치 '{to_branch}'를 찾을 수 없습니다."
        
        # 모크 비교 데이터 생성
        ahead = 7
        behind = 2
        
        result = f"{from_branch}과(와) {to_branch} 브랜치 비교:\n\n"
        result += f"{from_branch} 브랜치는 {to_branch}보다 {ahead}개 커밋 앞서 있고 {behind}개 커밋 뒤쳐져 있습니다.\n\n"
        
        result += "변경된 파일:\n"
        result += "1. src/auth/UserController.java (수정됨)\n"
        result += "   - 새로운 OAuth2 인증 메서드 추가\n"
        result += "   - 사용자 등록 흐름 업데이트\n\n"
        result += "2. src/auth/AuthConfig.java (수정됨)\n"
        result += "   - 새로운 인증 제공자에 대한 구성 추가\n\n"
        result += "3. src/auth/services/OAuthService.java (새로 생성)\n"
        result += "   - OAuth 인증을 처리하기 위한 새로운 서비스\n\n"
        result += "4. test/auth/OAuthServiceTest.java (새로 생성)\n"
        result += "   - 새로운 OAuth 서비스에 대한 테스트\n\n"
        result += "5. docs/authentication.md (수정됨)\n"
        result += "   - 새로운 인증 옵션에 대한 문서 업데이트"
        
        return result