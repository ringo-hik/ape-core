"""
응답 처리 유틸리티 함수

API 응답, 에이전트 응답 등의 포맷팅과 처리를 위한 함수들
"""

from typing import Dict, Any, List, Optional

def format_agent_response(agent_type: str, response: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    에이전트 응답을 API 응답 형식으로 포맷팅
    
    Args:
        agent_type: 에이전트 유형
        response: 에이전트 응답 내용
        metadata: 추가 메타데이터 (선택 사항)
        
    Returns:
        포맷팅된 응답 객체
    """
    formatted_response = {
        "agent_type": agent_type,
        "content": response,
        "metadata": metadata or {}
    }
    
    return formatted_response

def format_error_response(error_message: str, error_type: str = "processing_error", details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    오류 응답 포맷팅
    
    Args:
        error_message: 오류 메시지
        error_type: 오류 유형
        details: 상세 오류 정보 (선택 사항)
        
    Returns:
        포맷팅된 오류 응답
    """
    error_response = {
        "error": {
            "type": error_type,
            "message": error_message,
            "details": details or {}
        }
    }
    
    return error_response

def format_streaming_response(content: str, is_end: bool = False) -> Dict[str, Any]:
    """
    스트리밍 응답 포맷팅
    
    Args:
        content: 응답 내용 조각
        is_end: 스트림 종료 여부
        
    Returns:
        포맷팅된 스트리밍 응답
    """
    return {
        "content": content,
        "is_end": is_end
    }
