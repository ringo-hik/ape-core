"""
S3 에이전트 - 클라우드 스토리지 관리 에이전트

이 모듈은 AWS S3 API를 통해 버킷 및 객체 관리 기능을 제공합니다.
"""

import uuid
import logging
from typing import Dict, Any, Optional, List

import config
from src.core.llm_service import llm_service

# 로깅 설정
logger = logging.getLogger("s3_agent")

class S3Agent:
    """AWS S3 스토리지 관리 에이전트"""
    
    def __init__(self):
        """S3 에이전트 초기화"""
        self.agent_id = f"s3-{uuid.uuid4()}"
        
        # 설정 로드
        s3_config = config.get_s3_tool_config() if hasattr(config, 'get_s3_tool_config') else {}
        self.enabled = s3_config.get("enabled", True)
        self.username = s3_config.get("username", "")
        self.password = s3_config.get("password", "")
        self.region_name = s3_config.get("region_name", "us-east-1")
        self.timeout = s3_config.get("timeout", 30)
        
        logger.info(f"S3 에이전트 초기화: {self.agent_id} (활성화: {self.enabled})")
    
    def run(self, query: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        S3 작업 실행
        
        Args:
            query: 자연어 쿼리
            metadata: 추가 메타데이터 (버킷 정보 등)
            
        Returns:
            에이전트 응답
        """
        logger.info(f"S3 쿼리 실행: {query}")
        metadata = metadata or {}
        
        if not self.enabled:
            return self._format_response("오류: S3 도구가 비활성화되어 있습니다.")
            
        # 버킷 정보 확인
        bucket_info = metadata.get("bucket", "")
        
        # 프롬프트 구성
        prompt = f"""S3 클라우드 스토리지 어시스턴트로서 버킷과 객체 관리를 도와줍니다.

{'버킷 정보:\n' + bucket_info if bucket_info else ''}

작업: {query}

다음 S3 작업을 지원합니다:
1. 버킷 목록 조회
2. 버킷 내 객체 목록 조회
3. 객체 메타데이터 조회
4. 객체 업로드/다운로드
5. 객체 삭제
6. 버킷 생성/삭제

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
        connection_note = "\n\n# 참고\n이 응답은 시뮬레이션된 것으로, 실제 AWS S3에 연결되지 않았습니다."
        content = content + connection_note
        
        # 응답 반환
        return self._format_response(content)
    
    def _format_response(self, content: str) -> Dict[str, Any]:
        """응답 형식화"""
        return {
            "content": content,
            "model": llm_service.model_id,
            "agent_id": self.agent_id
        }