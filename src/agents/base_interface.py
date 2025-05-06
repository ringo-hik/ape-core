"""
표준 에이전트 인터페이스 정의

모든 에이전트가 구현해야 하는 공통 인터페이스를 정의합니다.
이를 통해 에이전트 간의 일관성을 확보하고 상호작용을 표준화합니다.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseAgent(ABC):
    """기본 에이전트 인터페이스"""
    
    @abstractmethod
    def __init__(self, **kwargs):
        """
        에이전트 초기화
        
        Args:
            **kwargs: 에이전트 초기화에 필요한 인자들
        """
        self.agent_id = ""  # 에이전트 고유 ID (구현 클래스에서 설정)
        self.agent_type = ""  # 에이전트 유형 (구현 클래스에서 설정)
        self.enabled = True  # 활성화 여부
    
    @abstractmethod
    def run(self, query: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        에이전트 실행
        
        Args:
            query: 실행할 쿼리 또는 명령
            metadata: 추가 메타데이터
            
        Returns:
            에이전트 실행 결과
        """
        pass
    
    def is_enabled(self) -> bool:
        """
        에이전트 활성화 여부 확인
        
        Returns:
            bool: 활성화 여부
        """
        return self.enabled
    
    def get_agent_id(self) -> str:
        """
        에이전트 ID 반환
        
        Returns:
            str: 에이전트 ID
        """
        return self.agent_id
    
    def get_agent_type(self) -> str:
        """
        에이전트 유형 반환
        
        Returns:
            str: 에이전트 유형
        """
        return self.agent_type
    
    def get_agent_info(self) -> Dict[str, Any]:
        """
        에이전트 정보 반환
        
        Returns:
            Dict[str, Any]: 에이전트 정보
        """
        return {
            "id": self.agent_id,
            "type": self.agent_type,
            "enabled": self.enabled
        }
    
    def validate_query(self, query: str) -> bool:
        """
        쿼리 유효성 검사
        
        Args:
            query: 쿼리 문자열
            
        Returns:
            bool: 쿼리 유효성 여부
        """
        # 기본 구현: 빈 쿼리가 아니면 유효
        return query is not None and query.strip() != ""
    
    def handle_error(self, error: Exception, query: str = "") -> Dict[str, Any]:
        """
        에러 처리
        
        Args:
            error: 발생한 예외
            query: 에러를 발생시킨 쿼리
            
        Returns:
            Dict[str, Any]: 포맷팅된 에러 응답
        """
        from src.utils.response_utils import format_error_response
        
        error_message = f"에이전트 오류: {str(error)}"
        
        if query:
            error_message += f"\n\n쿼리: {query}"
        
        return format_error_response(
            error_message=error_message,
            agent_id=self.agent_id,
            status_code=500
        )