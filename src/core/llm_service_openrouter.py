"""
OpenRouter LLM 서비스 모듈

OpenRouter API를 사용하여 다양한 LLM 모델에 접근하는 기능을 제공합니다.
"""

import json
import logging
import requests
from typing import List, Dict, Any, Optional, Union

# 환경 변수 로더 임포트
from src.core.env_loader import get_env

# 로깅 설정
logger = logging.getLogger("llm_service_openrouter")

class OpenRouterLLMService:
    """OpenRouter 기반 LLM 서비스"""
    
    def __init__(self, api_key: str = None, model_id: str = None):
        """
        OpenRouter LLM 서비스 초기화
        
        Args:
            api_key: OpenRouter API 키 (None인 경우 환경 변수에서 로드)
            model_id: 사용할 모델 ID (None인 경우 기본값 사용)
        """
        # API 키 설정
        self.api_key = api_key or get_env("OPENROUTER_API_KEY", "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")
        
        # 모델 ID 설정
        self.model_id = model_id or get_env("OPENROUTER_MODEL_ID", "meta-llama/llama-4-maverick")
        
        # API 엔드포인트
        self.api_endpoint = "https://openrouter.ai/api/v1/chat/completions"
        
        # 헤더 설정
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://localhost:8001"  # 필수: 요청 출처
        }
        
        logger.info(f"OpenRouter LLM 서비스 초기화 (모델: {self.model_id})")
    
    def generate(self, messages: List[Dict[str, str]], 
                 temperature: float = 0.7, 
                 max_tokens: int = 2000,
                 stream: bool = False) -> Union[str, Dict[str, Any]]:
        """
        LLM을 사용하여 텍스트 생성
        
        Args:
            messages: 메시지 목록 (역할과 내용 포함)
            temperature: 생성 온도 (높을수록 더 창의적)
            max_tokens: 최대 토큰 수
            stream: 스트리밍 여부
            
        Returns:
            생성된 텍스트 또는 에러 정보
        """
        # 요청 데이터 구성
        request_data = {
            "model": self.model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }
        
        try:
            # API 호출
            logger.info(f"OpenRouter API 호출 (모델: {self.model_id})")
            
            response = requests.post(
                self.api_endpoint,
                headers=self.headers,
                json=request_data,
                stream=stream
            )
            
            # 응답 확인
            if response.status_code != 200:
                error_msg = f"API 오류 (상태 코드: {response.status_code}): {response.text}"
                logger.error(error_msg)
                return {"error": error_msg}
            
            # 스트리밍 응답 처리
            if stream:
                return response.iter_lines()
            
            # 일반 응답 처리
            response_data = response.json()
            
            # 응답에서 텍스트 추출
            if "choices" in response_data and len(response_data["choices"]) > 0:
                message = response_data["choices"][0]["message"]
                return message.get("content", "")
            
            # 응답 형식이 예상과 다른 경우
            logger.warning(f"예상치 못한 응답 형식: {response_data}")
            return {"error": "응답에서 텍스트를 추출할 수 없습니다", "response": response_data}
            
        except Exception as e:
            logger.error(f"API 호출 오류: {e}")
            return {"error": str(e)}
    
    def format_user_message(self, content: str) -> Dict[str, str]:
        """
        사용자 메시지 포맷팅
        
        Args:
            content: 메시지 내용
            
        Returns:
            포맷팅된 메시지
        """
        return {
            "role": "user",
            "content": content
        }
    
    def format_system_message(self, content: str) -> Dict[str, str]:
        """
        시스템 메시지 포맷팅
        
        Args:
            content: 메시지 내용
            
        Returns:
            포맷팅된 메시지
        """
        return {
            "role": "system",
            "content": content
        }
    
    def format_assistant_message(self, content: str) -> Dict[str, str]:
        """
        어시스턴트 메시지 포맷팅
        
        Args:
            content: 메시지 내용
            
        Returns:
            포맷팅된 메시지
        """
        return {
            "role": "assistant",
            "content": content
        }

# 서비스 인스턴스
llm_service = OpenRouterLLMService()