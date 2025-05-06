"""
Pocket 에이전트 - 내부 클라우드 스토리지 인터페이스 에이전트

이 모듈은 내부 클라우드 스토리지 서비스(Pocket)와 상호작용하여 버킷, 객체 관리 기능을 제공합니다.
Mock 모드를 지원하여 내부망 연결 없이도 테스트 가능합니다.
"""

import uuid
import logging
import json
import os
import re
from typing import Dict, Any, List, Optional, Union

from src.core.llm_service import llm_service
import config
from src.core.requests_config import get_secure_http_session
from src.utils.response_utils import format_agent_response as format_response
from src.agents.base_interface import BaseAgent

# 로깅 설정
logger = logging.getLogger("pocket_agent")

class PocketAgent(BaseAgent):
    """내부 클라우드 스토리지 인터페이스 에이전트"""
    
    def __init__(self, **kwargs):
        """Pocket 에이전트 초기화"""
        self.agent_id = f"pocket-{uuid.uuid4()}"
        self.agent_type = "pocket"
        
        # 설정 로드
        self.pocket_config = config.get_pocket_tool_config() if hasattr(config, 'get_pocket_tool_config') else {}
        self.enabled = self.pocket_config.get('enabled', True)
        self.api_url = self.pocket_config.get('api_url', "https://pocket.internal.example.com/api/v1")
        self.username = self.pocket_config.get('username', "")
        self.password = self.pocket_config.get('password', "")
        
        # Mock 모드 설정
        self.mock_mode = True  # 항상 Mock 모드로 실행
        
        # 스키마 정보 로드
        self.schema_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                        "src", "schema", "pocket.json")
        self.schema_info = self._load_schema()
        
        # API 세션 초기화 (실제 연결 시 사용)
        if not self.mock_mode:
            self.session = get_secure_http_session(timeout=30, verify_ssl=False)
            
            # API 인증 헤더 설정
            if self.username and self.password:
                import base64
                auth_str = f"{self.username}:{self.password}"
                encoded_auth = base64.b64encode(auth_str.encode()).decode()
                self.session.headers.update({
                    "Authorization": f"Basic {encoded_auth}",
                    "Content-Type": "application/json"
                })
        
        # 가상 저장소 데이터 초기화 (Mock 모드용)
        self.mock_buckets = {
            "documents": {
                "creation_date": "2023-01-15",
                "region": "ap-northeast-2",
                "objects": {
                    "readme.md": {
                        "size": 2048,
                        "last_modified": "2023-01-16T10:30:00",
                        "etag": "a1b2c3d4e5f6",
                        "storage_class": "STANDARD"
                    },
                    "reports/q1_2023.pdf": {
                        "size": 5242880,
                        "last_modified": "2023-03-31T18:45:00",
                        "etag": "f6e5d4c3b2a1",
                        "storage_class": "STANDARD"
                    },
                    "reports/q2_2023.pdf": {
                        "size": 6291456,
                        "last_modified": "2023-06-30T19:15:00",
                        "etag": "1a2b3c4d5e6f",
                        "storage_class": "STANDARD"
                    }
                }
            },
            "images": {
                "creation_date": "2023-02-10",
                "region": "ap-northeast-2",
                "objects": {
                    "logo.png": {
                        "size": 524288,
                        "last_modified": "2023-02-10T14:20:00",
                        "etag": "abcdef123456",
                        "storage_class": "STANDARD"
                    },
                    "banners/main.jpg": {
                        "size": 1048576,
                        "last_modified": "2023-02-15T11:10:00",
                        "etag": "123456abcdef",
                        "storage_class": "STANDARD"
                    }
                }
            },
            "backups": {
                "creation_date": "2023-01-01",
                "region": "ap-northeast-2",
                "objects": {
                    "database/jan_2023.sql": {
                        "size": 104857600,
                        "last_modified": "2023-01-31T23:59:00",
                        "etag": "11aa22bb33cc",
                        "storage_class": "STANDARD_IA"
                    },
                    "database/feb_2023.sql": {
                        "size": 115343360,
                        "last_modified": "2023-02-28T23:59:00",
                        "etag": "44dd55ee66ff",
                        "storage_class": "STANDARD_IA"
                    },
                    "database/mar_2023.sql": {
                        "size": 125829120,
                        "last_modified": "2023-03-31T23:59:00",
                        "etag": "77gg88hh99ii",
                        "storage_class": "ARCHIVE"
                    }
                }
            }
        }
        
        logger.info(f"Pocket 에이전트 초기화: {self.agent_id} (Mock 모드: {self.mock_mode})")
    
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
    
    def run(self, query: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Pocket 쿼리 실행
        
        Args:
            query: 자연어 쿼리
            metadata: 추가 메타데이터
            
        Returns:
            에이전트 응답
        """
        logger.info(f"Pocket 쿼리 실행: {query}")
        metadata = metadata or {}
        
        if not self.enabled:
            return format_response(self.agent_id, "오류: Pocket 에이전트가 비활성화되어 있습니다.", llm_service.model_id)
        
        # 작업 분석 (Pocket 쿼리 의도 파악)
        action_plan = self._analyze_query(query)
        logger.info(f"Pocket 작업 분석: {action_plan}")
        
        # 작업 수행
        action_type = self._determine_action_type(action_plan)
        
        # 작업 유형별 처리
        if "버킷 목록" in action_type:
            result = self._list_buckets()
        elif "버킷 생성" in action_type:
            bucket_name = self._extract_bucket_name(query, action_plan)
            result = self._create_bucket(bucket_name)
        elif "객체 목록" in action_type:
            bucket_name, prefix = self._extract_list_objects_params(query, action_plan)
            result = self._list_objects(bucket_name, prefix)
        elif "객체 정보" in action_type:
            bucket_name, object_key = self._extract_object_params(query, action_plan)
            result = self._get_object_info(bucket_name, object_key)
        elif "업로드" in action_type:
            bucket_name, object_key = self._extract_object_params(query, action_plan)
            result = self._upload_object(bucket_name, object_key, query)
        elif "다운로드" in action_type:
            bucket_name, object_key = self._extract_object_params(query, action_plan)
            result = self._download_object(bucket_name, object_key)
        elif "삭제" in action_type and "객체" in action_type:
            bucket_name, object_key = self._extract_object_params(query, action_plan)
            result = self._delete_object(bucket_name, object_key)
        elif "삭제" in action_type and "버킷" in action_type:
            bucket_name = self._extract_bucket_name(query, action_plan)
            result = self._delete_bucket(bucket_name)
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
        prompt = f"""Pocket(내부 클라우드 스토리지 서비스) 에이전트로서 다음 쿼리를 분석하고 수행할 작업을 결정하세요:

쿼리: {query}

가능한 작업:
1. 버킷 목록 조회
2. 버킷 생성
3. 버킷 삭제
4. 객체 목록 조회
5. 객체 정보 조회
6. 객체 업로드
7. 객체 다운로드
8. 객체 삭제

쿼리를 분석하여 어떤 작업을 수행해야 하는지 결정하세요.
결정한 작업을 작업 번호와 함께 명확하게 설명하세요.
버킷 이름과 객체 경로가 있다면 정확히 명시하세요.
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
        action_types = [
            "버킷 목록", "버킷 생성", "버킷 삭제", 
            "객체 목록", "객체 정보", "객체 업로드", "객체 다운로드", "객체 삭제"
        ]
        for action in action_types:
            if action in action_plan:
                return action
        return "알 수 없는 작업"
    
    def _extract_bucket_name(self, query: str, action_plan: str) -> str:
        """쿼리와 실행 계획에서 버킷 이름 추출"""
        # 먼저 실행 계획에서 추출 시도
        bucket_patterns = [
            r"버킷\s+이름[은는:\s]+['\"]([\w-]+)['\"]",
            r"버킷[은는:\s]+['\"]([\w-]+)['\"]",
            r"['\"]([\w-]+)['\"]라는\s+버킷",
            r"['\"]([\w-]+)['\"]?\s+버킷"
        ]
        
        for pattern in bucket_patterns:
            match = re.search(pattern, action_plan)
            if match:
                return match.group(1)
        
        # 쿼리에서 추출 시도
        for pattern in bucket_patterns:
            match = re.search(pattern, query)
            if match:
                return match.group(1)
        
        # 다른 패턴으로 재시도
        bucket_match = re.search(r'[\'"]([\w-]+)[\'"]', action_plan)
        if bucket_match:
            return bucket_match.group(1)
            
        bucket_match = re.search(r'[\'"]([\w-]+)[\'"]', query)
        if bucket_match:
            return bucket_match.group(1)
        
        # 기본값 반환
        return "documents"
    
    def _extract_list_objects_params(self, query: str, action_plan: str) -> tuple:
        """
        객체 목록 조회 파라미터 추출
        
        Returns:
            (버킷 이름, 접두사)
        """
        # 버킷 이름 추출
        bucket_name = self._extract_bucket_name(query, action_plan)
        
        # 접두사 추출
        prefix_patterns = [
            r"접두사[는은:\s]+['\"]([\w/-]+)['\"]",
            r"경로[는은:\s]+['\"]([\w/-]+)['\"]",
            r"디렉터리[는은:\s]+['\"]([\w/-]+)['\"]",
            r"폴더[는은:\s]+['\"]([\w/-]+)['\"]"
        ]
        
        prefix = ""
        for pattern in prefix_patterns:
            match = re.search(pattern, action_plan)
            if match:
                prefix = match.group(1)
                break
                
        if not prefix:
            for pattern in prefix_patterns:
                match = re.search(pattern, query)
                if match:
                    prefix = match.group(1)
                    break
        
        return bucket_name, prefix
    
    def _extract_object_params(self, query: str, action_plan: str) -> tuple:
        """
        객체 작업 파라미터 추출
        
        Returns:
            (버킷 이름, 객체 키)
        """
        # 버킷 이름 추출
        bucket_name = self._extract_bucket_name(query, action_plan)
        
        # 객체 키 추출
        object_patterns = [
            r"객체\s+키[는은:\s]+['\"]([\w/-\.]+)['\"]",
            r"객체[는은:\s]+['\"]([\w/-\.]+)['\"]",
            r"파일[은는:\s]+['\"]([\w/-\.]+)['\"]",
            r"['\"]([\w/-\.]+)['\"]라는\s+(?:객체|파일)",
            r"['\"]([\w/-\.]+)['\"]?\s+(?:객체|파일)"
        ]
        
        object_key = ""
        for pattern in object_patterns:
            match = re.search(pattern, action_plan)
            if match:
                object_key = match.group(1)
                break
                
        if not object_key:
            for pattern in object_patterns:
                match = re.search(pattern, query)
                if match:
                    object_key = match.group(1)
                    break
        
        # 다른 패턴으로 재시도
        if not object_key:
            # 따옴표로 둘러싸인 문자열 검색 (버킷 이름이 아닌 것)
            quoted_pattern = r'[\'"]([^\'"\s]+\.[^\'"\s]+)[\'"]'
            match = re.search(quoted_pattern, action_plan)
            if match and match.group(1) != bucket_name:
                object_key = match.group(1)
            else:
                match = re.search(quoted_pattern, query)
                if match and match.group(1) != bucket_name:
                    object_key = match.group(1)
        
        return bucket_name, object_key
    
    def _list_buckets(self) -> str:
        """버킷 목록 조회"""
        if self.mock_mode:
            buckets = self.mock_buckets.keys()
            result = "## 버킷 목록\n\n"
            
            for bucket_name in buckets:
                bucket_info = self.mock_buckets[bucket_name]
                result += f"- **{bucket_name}**\n"
                result += f"  생성일: {bucket_info['creation_date']}\n"
                result += f"  리전: {bucket_info['region']}\n"
                result += f"  객체 수: {len(bucket_info['objects'])}\n\n"
            
            return result
        else:
            # 실제 API 호출 로직
            pass
    
    def _create_bucket(self, bucket_name: str) -> str:
        """
        버킷 생성
        
        Args:
            bucket_name: 버킷 이름
            
        Returns:
            결과 메시지
        """
        if self.mock_mode:
            if bucket_name in self.mock_buckets:
                return f"오류: '{bucket_name}' 버킷이 이미 존재합니다. 다른 이름을 선택하세요."
            
            # 버킷 이름 검증
            if not re.match(r'^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$', bucket_name):
                return "오류: 버킷 이름은 소문자, 숫자, 하이픈, 마침표만 포함할 수 있으며, 3-63자 길이여야 합니다."
            
            # 가상 버킷 생성
            import datetime
            today = datetime.date.today().strftime("%Y-%m-%d")
            
            self.mock_buckets[bucket_name] = {
                "creation_date": today,
                "region": "ap-northeast-2",
                "objects": {}
            }
            
            return f"## 버킷 생성 완료\n\n버킷 '{bucket_name}'이(가) 성공적으로 생성되었습니다.\n\n- 생성일: {today}\n- 리전: ap-northeast-2"
        else:
            # 실제 API 호출 로직
            pass
    
    def _delete_bucket(self, bucket_name: str) -> str:
        """
        버킷 삭제
        
        Args:
            bucket_name: 버킷 이름
            
        Returns:
            결과 메시지
        """
        if self.mock_mode:
            if bucket_name not in self.mock_buckets:
                return f"오류: '{bucket_name}' 버킷이 존재하지 않습니다."
            
            # 버킷이 비어있는지 확인
            if self.mock_buckets[bucket_name]["objects"]:
                return f"오류: '{bucket_name}' 버킷이 비어있지 않습니다. 먼저 버킷의 모든 객체를 삭제하세요."
            
            # 가상 버킷 삭제
            del self.mock_buckets[bucket_name]
            
            return f"## 버킷 삭제 완료\n\n버킷 '{bucket_name}'이(가) 성공적으로 삭제되었습니다."
        else:
            # 실제 API 호출 로직
            pass
    
    def _list_objects(self, bucket_name: str, prefix: str = "") -> str:
        """
        객체 목록 조회
        
        Args:
            bucket_name: 버킷 이름
            prefix: 객체 접두사 (선택적)
            
        Returns:
            결과 메시지
        """
        if self.mock_mode:
            if bucket_name not in self.mock_buckets:
                return f"오류: '{bucket_name}' 버킷이 존재하지 않습니다."
            
            # 접두사로 필터링
            objects = {}
            for key, info in self.mock_buckets[bucket_name]["objects"].items():
                if not prefix or key.startswith(prefix):
                    objects[key] = info
            
            result = f"## '{bucket_name}' 버킷 객체 목록\n\n"
            
            # 접두사가 있는 경우 표시
            if prefix:
                result += f"접두사: {prefix}\n\n"
            
            if not objects:
                result += "객체가 없습니다." if not prefix else f"'{prefix}' 접두사를 가진 객체가 없습니다."
                return result
            
            # 객체 정보 표시
            result += "| 객체 키 | 크기 | 최종 수정일 | 스토리지 클래스 |\n"
            result += "|---------|------|------------|----------------|\n"
            
            for key, info in objects.items():
                size = self._format_size(info["size"])
                last_modified = info["last_modified"]
                storage_class = info["storage_class"]
                
                result += f"| {key} | {size} | {last_modified} | {storage_class} |\n"
            
            return result
        else:
            # 실제 API 호출 로직
            pass
    
    def _get_object_info(self, bucket_name: str, object_key: str) -> str:
        """
        객체 정보 조회
        
        Args:
            bucket_name: 버킷 이름
            object_key: 객체 키
            
        Returns:
            결과 메시지
        """
        if self.mock_mode:
            if bucket_name not in self.mock_buckets:
                return f"오류: '{bucket_name}' 버킷이 존재하지 않습니다."
            
            if not object_key or object_key not in self.mock_buckets[bucket_name]["objects"]:
                return f"오류: '{bucket_name}' 버킷에 '{object_key}' 객체가 존재하지 않습니다."
            
            # 객체 정보 가져오기
            info = self.mock_buckets[bucket_name]["objects"][object_key]
            
            result = f"## 객체 정보: '{object_key}'\n\n"
            result += f"- **버킷**: {bucket_name}\n"
            result += f"- **객체 키**: {object_key}\n"
            result += f"- **크기**: {self._format_size(info['size'])}\n"
            result += f"- **최종 수정일**: {info['last_modified']}\n"
            result += f"- **ETag**: {info['etag']}\n"
            result += f"- **스토리지 클래스**: {info['storage_class']}\n"
            
            # 미리 서명된 URL (가상)
            result += f"\n### 미리 서명된 URL\n\n"
            result += f"https://pocket.internal.example.com/{bucket_name}/{object_key}?X-Auth-Token=mocktoken123\n"
            result += f"\n이 URL은 1시간 동안 유효합니다."
            
            return result
        else:
            # 실제 API 호출 로직
            pass
    
    def _upload_object(self, bucket_name: str, object_key: str, query: str) -> str:
        """
        객체 업로드
        
        Args:
            bucket_name: 버킷 이름
            object_key: 객체 키
            query: 원본 쿼리 (추가 정보 추출용)
            
        Returns:
            결과 메시지
        """
        if self.mock_mode:
            if bucket_name not in self.mock_buckets:
                return f"오류: '{bucket_name}' 버킷이 존재하지 않습니다."
            
            if not object_key:
                return "오류: 업로드할 객체의 키를 지정해야 합니다."
            
            # 파일 크기 추출 (가상)
            file_size = 1024  # 기본 1KB
            size_match = re.search(r'(\d+)(?:\s*)(kb|mb|gb)', query, re.IGNORECASE)
            if size_match:
                size_num = int(size_match.group(1))
                size_unit = size_match.group(2).lower()
                
                if size_unit == 'kb':
                    file_size = size_num * 1024
                elif size_unit == 'mb':
                    file_size = size_num * 1024 * 1024
                elif size_unit == 'gb':
                    file_size = size_num * 1024 * 1024 * 1024
            
            # 스토리지 클래스 추출
            storage_class = "STANDARD"
            if "아카이브" in query or "archive" in query.lower():
                storage_class = "ARCHIVE"
            elif "ia" in query.lower() or "비정기적" in query:
                storage_class = "STANDARD_IA"
            
            # 가상 객체 업로드
            import datetime
            now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            
            self.mock_buckets[bucket_name]["objects"][object_key] = {
                "size": file_size,
                "last_modified": now,
                "etag": f"{uuid.uuid4().hex[:12]}",
                "storage_class": storage_class
            }
            
            result = f"## 객체 업로드 완료\n\n"
            result += f"'{object_key}' 객체가 '{bucket_name}' 버킷에 성공적으로 업로드되었습니다.\n\n"
            result += f"- **크기**: {self._format_size(file_size)}\n"
            result += f"- **스토리지 클래스**: {storage_class}\n"
            result += f"- **업로드 시간**: {now}\n"
            
            return result
        else:
            # 실제 API 호출 로직
            pass
    
    def _download_object(self, bucket_name: str, object_key: str) -> str:
        """
        객체 다운로드
        
        Args:
            bucket_name: 버킷 이름
            object_key: 객체 키
            
        Returns:
            결과 메시지
        """
        if self.mock_mode:
            if bucket_name not in self.mock_buckets:
                return f"오류: '{bucket_name}' 버킷이 존재하지 않습니다."
            
            if not object_key or object_key not in self.mock_buckets[bucket_name]["objects"]:
                return f"오류: '{bucket_name}' 버킷에 '{object_key}' 객체가 존재하지 않습니다."
            
            # 객체 정보 가져오기
            info = self.mock_buckets[bucket_name]["objects"][object_key]
            
            # 아카이브 클래스인 경우 복원 필요
            if info["storage_class"] == "ARCHIVE":
                return f"오류: '{object_key}' 객체는 ARCHIVE 스토리지 클래스에 있습니다. 다운로드하기 전에 복원이 필요합니다."
            
            result = f"## 객체 다운로드 시작됨\n\n"
            result += f"'{object_key}' 객체를 '{bucket_name}' 버킷에서 다운로드하고 있습니다.\n\n"
            result += f"- **크기**: {self._format_size(info['size'])}\n"
            result += f"- **ETag**: {info['etag']}\n"
            
            # 다운로드 완료 메시지 (가상)
            result += f"\n다운로드가 완료되었습니다. 파일이 로컬 시스템에 저장되었습니다.\n"
            
            return result
        else:
            # 실제 API 호출 로직
            pass
    
    def _delete_object(self, bucket_name: str, object_key: str) -> str:
        """
        객체 삭제
        
        Args:
            bucket_name: 버킷 이름
            object_key: 객체 키
            
        Returns:
            결과 메시지
        """
        if self.mock_mode:
            if bucket_name not in self.mock_buckets:
                return f"오류: '{bucket_name}' 버킷이 존재하지 않습니다."
            
            if not object_key or object_key not in self.mock_buckets[bucket_name]["objects"]:
                return f"오류: '{bucket_name}' 버킷에 '{object_key}' 객체가 존재하지 않습니다."
            
            # 가상 객체 삭제
            del self.mock_buckets[bucket_name]["objects"][object_key]
            
            result = f"## 객체 삭제 완료\n\n"
            result += f"'{object_key}' 객체가 '{bucket_name}' 버킷에서 성공적으로 삭제되었습니다."
            
            return result
        else:
            # 실제 API 호출 로직
            pass
    
    def _format_size(self, size_in_bytes: int) -> str:
        """
        바이트 크기를 사람이 읽기 쉬운 형식으로 변환
        
        Args:
            size_in_bytes: 바이트 단위 크기
            
        Returns:
            포맷팅된 크기 문자열
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_in_bytes < 1024 or unit == 'TB':
                break
            size_in_bytes /= 1024
        
        return f"{size_in_bytes:.2f} {unit}"