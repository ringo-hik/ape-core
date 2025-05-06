"""LLM 서비스 모듈

LLM 모델 호출 및 관리하는 기능을 제공합니다.
내부망/외부망 연결 및 다양한 LLM 공급자 지원
"""

import os
import json
import time
import logging
import requests
from typing import Dict, List, Any, Optional, Union, Generator

from src.core.config import get_settings, get_model_config, get_available_models, get_default_model, set_default_model

# 로거 설정
logger = logging.getLogger("llm_service")

class LLMService:
    """LLM 서비스 클래스"""
    
    def __init__(self):
        """LLM 서비스 초기화"""
        self.settings = get_settings()
        self.current_model = get_default_model()
        self.model_config = get_model_config(self.current_model)
        self.available_providers = self._get_available_providers()
        self.model_id = self.model_config.get("id", "")
        
        # 내부망 연결 테스트 (internal 프로바이더가 사용 가능한 경우)
        if "internal" in self.available_providers:
            self._check_internal_connection()
    
    def _get_available_providers(self) -> List[str]:
        """사용 가능한 LLM 프로바이더 목록 반환"""
        providers = set()
        
        # 모든 사용 가능한 모델을 확인하여 프로바이더 목록 생성
        for model_key in get_available_models():
            model_config = get_model_config(model_key)
            provider = model_config.get("provider")
            if provider:
                providers.add(provider)
        
        return list(providers)
        
    def _check_internal_connection(self):
        """내부망 연결 테스트"""
        # 내부 모델 설정 가져오기
        internal_models = [model for model in get_available_models() 
                          if get_model_config(model).get("provider") == "internal"]
        
        if not internal_models:
            logger.warning("내부망 LLM 모델이 설정되지 않았습니다")
            return
        
        # 첫 번째 내부 모델의 엔드포인트 가져오기
        internal_model = internal_models[0]
        internal_config = get_model_config(internal_model)
        internal_endpoint = internal_config.get("endpoint", "")
        
        if not internal_endpoint:
            logger.warning("내부망 LLM 엔드포인트가 설정되지 않았습니다")
            return
        
        try:
            # 간단한 연결 테스트 (타임아웃 2초)
            response = requests.get(
                internal_endpoint + "/health", 
                timeout=2,
                verify=False  # SSL 검증 비활성화
            )
            
            if response.status_code == 200:
                # 프로바이더 사용 가능 상태 업데이트
                if "internal" not in self.available_providers:
                    self.available_providers.append("internal")
                logger.info("내부망 LLM 서비스 연결 가능")
            else:
                logger.warning(f"내부망 LLM 서비스 응답 오류: {response.status_code}")
                # 내부망 연결 실패 시 프로바이더 목록에서 제거
                if "internal" in self.available_providers:
                    self.available_providers.remove("internal")
        except requests.exceptions.RequestException as e:
            logger.warning(f"내부망 LLM 서비스 연결 실패: {e}")
            # 내부망 연결 실패 시 프로바이더 목록에서 제거
            if "internal" in self.available_providers:
                self.available_providers.remove("internal")
    
    def list_available_models(self) -> List[Dict[str, Any]]:
        """사용 가능한 모델 목록 반환 (상세 정보 포함)"""
        models_info = []
        
        for model_key in get_available_models():
            model_config = get_model_config(model_key)
            models_info.append({
                "key": model_key,
                "name": model_config.get("name", model_key),
                "provider": model_config.get("provider", "unknown"),
                "description": model_config.get("description", ""),
                "id": model_config.get("id", model_key)
            })
        
        return models_info
    
    def get_current_model(self) -> str:
        """현재 사용 중인 모델 키 반환"""
        return self.current_model
    
    def change_model(self, model_key: str) -> bool:
        """사용 모델 변경"""
        available_models = get_available_models()
        
        if model_key not in available_models:
            logger.error(f"사용할 수 없는 모델: {model_key}")
            return False
        
        # 모델 설정 변경
        self.current_model = model_key
        self.model_config = get_model_config(model_key)
        self.model_id = self.model_config.get("id", "")
        
        # 기본 모델 설정 업데이트
        set_default_model(model_key)
        
        logger.info(f"모델 변경 완료: {model_key} ({self.model_config.get('name')})")
        return True
    
    def format_system_message(self, content: str) -> Dict[str, str]:
        """시스템 메시지 형식화"""
        return {"role": "system", "content": content}
    
    def format_user_message(self, content: str) -> Dict[str, str]:
        """사용자 메시지 형식화"""
        return {"role": "user", "content": content}
    
    def format_assistant_message(self, content: str) -> Dict[str, str]:
        """어시스턴트 메시지 형식화"""
        return {"role": "assistant", "content": content}
    
    def generate(self, messages: List[Dict[str, str]], stream: bool = False) -> Union[str, Generator[str, None, None]]:
        """메시지 생성"""
        if stream:
            return self._generate_stream(messages)
        else:
            return self._generate_sync(messages)
    
    def _generate_sync(self, messages: List[Dict[str, str]]) -> str:
        """동기 방식 메시지 생성"""
        # API 키가 mock으로 시작하면 가짜 응답 반환
        api_key = self.model_config.get("apiKey", "")
        if api_key.startswith("mock_"):
            logger.info(f"MOCK 모드로 {self.model_config.get('provider')} LLM 호출")
            return self._generate_mock_response(messages)
            
        # 현재 선택된 모델의 프로바이더 확인
        provider = self.model_config.get("provider", "")
        
        if provider == "internal" and "internal" in self.available_providers:
            # 내부망 LLM 서비스 사용
            try:
                return self._call_provider_llm(messages, "internal")
            except Exception as e:
                logger.warning(f"내부망 LLM 호출 실패, 대체 서비스 사용 시도: {e}")
        
        elif provider == "openrouter" and "openrouter" in self.available_providers:
            # OpenRouter 서비스 사용
            try:
                return self._call_provider_llm(messages, "openrouter")
            except Exception as e:
                logger.error(f"OpenRouter LLM 호출 실패: {e}")
        
        # 현재 선택된 모델로 호출 실패 시 대체 프로바이더 시도
        for fallback_provider in self.available_providers:
            if fallback_provider != provider:
                try:
                    logger.info(f"대체 프로바이더로 시도: {fallback_provider}")
                    return self._call_provider_llm(messages, fallback_provider)
                except Exception as e:
                    logger.error(f"{fallback_provider} LLM 호출 실패: {e}")
        
        # 모든 방법 실패 시
        error_msg = "모든 LLM 서비스 호출 방법이 실패했습니다. API 키와 연결 상태를 확인하세요."
        logger.error(error_msg)
        return {"error": error_msg}
        
    def _generate_mock_response(self, messages: List[Dict[str, str]]) -> str:
        """목(Mock) 응답 생성
        
        테스트 환경에서만 사용되는 가짜 응답 생성기
        """
        # 마지막 사용자 메시지 찾기
        user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break
        
        # 질문에 대한 기본 응답
        if "APE" in user_message or "에이전트" in user_message:
            return """APE(Agentic Pipeline Engine)는 다양한 LLM 모델과 RAG(Retrieval-Augmented Generation) 및 LangGraph 기능을 제공하는 백엔드 서버입니다. 

주요 기능:
1. 다양한 LLM 모델 연결 (내부망/외부망 자동 전환)
2. RAG를 통한 문서 검색 및 지식 기반 응답
3. 에이전트 시스템을 통한 다양한 태스크 처리
4. LangGraph를 통한 워크플로우 자동화

자세한 내용은 문서를 참조하세요."""
        else:
            return f"죄송합니다만, '{user_message}'에 대한 정보를 찾을 수 없습니다. 다른 질문을 해주시겠어요?"
    
    def _generate_stream(self, messages: List[Dict[str, str]]) -> Generator[str, None, None]:
        """스트리밍 방식 메시지 생성"""
        # API 키가 mock으로 시작하면 가짜 응답 반환
        api_key = self.model_config.get("apiKey", "")
        if api_key.startswith("mock_"):
            logger.info(f"MOCK 모드로 {self.model_config.get('provider')} LLM 스트리밍 호출")
            yield from self._generate_mock_stream(messages)
            return
            
        # 현재 선택된 모델의 프로바이더 확인
        provider = self.model_config.get("provider", "")
        
        if provider == "internal" and "internal" in self.available_providers:
            # 내부망 LLM 서비스 사용
            try:
                yield from self._call_provider_llm_stream(messages, "internal")
                return
            except Exception as e:
                logger.warning(f"내부망 LLM 스트리밍 호출 실패, 대체 서비스 사용 시도: {e}")
        
        elif provider == "openrouter" and "openrouter" in self.available_providers:
            # OpenRouter 서비스 사용
            try:
                yield from self._call_provider_llm_stream(messages, "openrouter")
                return
            except Exception as e:
                logger.error(f"OpenRouter LLM 스트리밍 호출 실패: {e}")
        
        # 현재 선택된 모델로 호출 실패 시 대체 프로바이더 시도
        for fallback_provider in self.available_providers:
            if fallback_provider != provider:
                try:
                    logger.info(f"대체 프로바이더로 스트리밍 시도: {fallback_provider}")
                    yield from self._call_provider_llm_stream(messages, fallback_provider)
                    return
                except Exception as e:
                    logger.error(f"{fallback_provider} LLM 스트리밍 호출 실패: {e}")
        
        # 모든 방법 실패 시
        error_msg = "모든 LLM 서비스 스트리밍 호출 방법이 실패했습니다. API 키와 연결 상태를 확인하세요."
        logger.error(error_msg)
        yield error_msg
        
    def _generate_mock_stream(self, messages: List[Dict[str, str]]) -> Generator[str, None, None]:
        """목(Mock) 스트리밍 응답 생성
        
        테스트 환경에서만 사용되는 가짜 스트리밍 응답 생성기
        """
        # 마지막 사용자 메시지 찾기
        user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break
        
        # APE 관련 질문인 경우
        if "APE" in user_message or "에이전트" in user_message:
            chunks = [
                "APE(Agentic Pipeline Engine)는 ", 
                "다양한 LLM 모델과 ", 
                "RAG(Retrieval-Augmented Generation) 및 ", 
                "LangGraph 기능을 제공하는 ", 
                "백엔드 서버입니다.\n\n",
                "주요 기능:\n",
                "1. 다양한 LLM 모델 연결 (내부망/외부망 자동 전환)\n",
                "2. RAG를 통한 문서 검색 및 지식 기반 응답\n",
                "3. 에이전트 시스템을 통한 다양한 태스크 처리\n",
                "4. LangGraph를 통한 워크플로우 자동화\n\n",
                "자세한 내용은 문서를 참조하세요."
            ]
        else:
            chunks = [
                "죄송합니다만, ",
                f"'{user_message}'에 대한 ",
                "정보를 찾을 수 없습니다. ",
                "다른 질문을 해주시겠어요?"
            ]
            
        # 각 청크마다 약간의 지연 추가하여 스트리밍처럼 보이게 함
        for chunk in chunks:
            time.sleep(0.1)  # 100ms 지연
            yield chunk
    
    def _get_provider_model(self, provider: str) -> str:
        """지정된 프로바이더에 해당하는 첫 번째 모델 키 반환"""
        for model_key in get_available_models():
            model_config = get_model_config(model_key)
            if model_config.get("provider") == provider:
                return model_key
        return None
    
    def _call_provider_llm(self, messages: List[Dict[str, str]], provider: str) -> str:
        """지정된 프로바이더의 LLM 서비스 호출"""
        # 현재 모델이 지정된, 프로바이더인지 확인
        current_provider = self.model_config.get("provider")
        
        # 현재 모델의 프로바이더가 지정된 프로바이더와 다르면 해당 프로바이더의 첫 번째 모델 사용
        if current_provider != provider:
            model_key = self._get_provider_model(provider)
            if not model_key:
                raise Exception(f"사용 가능한 {provider} 프로바이더 모델을 찾을 수 없습니다")
            
            # 임시로 모델 설정 변경
            model_config = get_model_config(model_key)
        else:
            # 현재 모델 설정 사용
            model_config = self.model_config
        
        # 프로바이더별 호출 방식 선택
        if provider == "internal":
            return self._call_internal_llm(messages, model_config)
        elif provider == "openrouter":
            return self._call_openrouter(messages, model_config)
        else:
            raise Exception(f"지원하지 않는 프로바이더: {provider}")
    
    def _call_provider_llm_stream(self, messages: List[Dict[str, str]], provider: str) -> Generator[str, None, None]:
        """지정된 프로바이더의 LLM 서비스 스트리밍 호출"""
        # 현재 모델이 지정된 프로바이더인지 확인
        current_provider = self.model_config.get("provider")
        
        # 현재 모델의 프로바이더가 지정된 프로바이더와 다르면 해당 프로바이더의 첫 번째 모델 사용
        if current_provider != provider:
            model_key = self._get_provider_model(provider)
            if not model_key:
                raise Exception(f"사용 가능한 {provider} 프로바이더 모델을 찾을 수 없습니다")
            
            # 임시로 모델 설정 변경
            model_config = get_model_config(model_key)
        else:
            # 현재 모델 설정 사용
            model_config = self.model_config
        
        # 프로바이더별 호출 방식 선택
        if provider == "internal":
            yield from self._call_internal_llm_stream(messages, model_config)
        elif provider == "openrouter":
            yield from self._call_openrouter_stream(messages, model_config)
        else:
            raise Exception(f"지원하지 않는 프로바이더: {provider}")
    
    def _call_internal_llm(self, messages: List[Dict[str, str]], model_config: Dict[str, Any]) -> str:
        """내부망 LLM 서비스 호출"""
        endpoint = model_config.get("endpoint", "")
        if not endpoint:
            raise Exception("내부망 LLM 엔드포인트가 설정되지 않았습니다")
        
        # 요청 템플릿 가져오기
        request_template = model_config.get("requestTemplate", {})
        headers = request_template.get("headers", {}).copy()
        payload = request_template.get("payload", {}).copy()
        
        # API 키 설정
        api_key = model_config.get("apiKey", "")
        for key, value in headers.items():
            headers[key] = value.replace("${API_KEY}", api_key)
        
        # 모델 설정
        payload["messages"] = messages
        payload["temperature"] = model_config.get("temperature", 0.7)
        payload["max_tokens"] = model_config.get("maxTokens", 4096)
        payload["stream"] = False
        
        # 요청 및 응답 처리
        response = requests.post(
            endpoint + "/chat/completions",
            json=payload,
            headers=headers,
            verify=False,  # SSL 검증 비활성화
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"내부망 LLM 서비스 응답 오류: {response.status_code}, {response.text}")
        
        result = response.json()
        return result.get("choices", [{}])[0].get("message", {}).get("content", "")
    
    def _call_internal_llm_stream(self, messages: List[Dict[str, str]], model_config: Dict[str, Any]) -> Generator[str, None, None]:
        """내부망 LLM 서비스 스트리밍 호출"""
        endpoint = model_config.get("endpoint", "")
        if not endpoint:
            raise Exception("내부망 LLM 엔드포인트가 설정되지 않았습니다")
        
        # 요청 템플릿 가져오기
        request_template = model_config.get("requestTemplate", {})
        headers = request_template.get("headers", {}).copy()
        payload = request_template.get("payload", {}).copy()
        
        # API 키 설정
        api_key = model_config.get("apiKey", "")
        for key, value in headers.items():
            headers[key] = value.replace("${API_KEY}", api_key)
        
        # 모델 설정
        payload["messages"] = messages
        payload["temperature"] = model_config.get("temperature", 0.7)
        payload["max_tokens"] = model_config.get("maxTokens", 4096)
        payload["stream"] = True
        
        # 요청 및 응답 처리
        response = requests.post(
            endpoint + "/chat/completions",
            json=payload,
            headers=headers,
            verify=False,  # SSL 검증 비활성화
            stream=True,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"내부망 LLM 서비스 스트리밍 응답 오류: {response.status_code}, {response.text}")
        
        for chunk in response.iter_lines():
            if chunk:
                try:
                    data = chunk.decode('utf-8')
                    if data.startswith('data: '):
                        data = data[6:]
                    if data == "[DONE]":
                        break
                    
                    json_data = json.loads(data)
                    delta = json_data.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    
                    if content:
                        yield content
                except Exception as e:
                    logger.error(f"내부망 LLM 스트리밍 청크 처리 오류: {e}")
    
    def _call_openrouter(self, messages: List[Dict[str, str]], model_config: Dict[str, Any]) -> str:
        """OpenRouter 호출"""
        endpoint = model_config.get("endpoint", "")
        if not endpoint:
            raise Exception("OpenRouter 엔드포인트가 설정되지 않았습니다")
        
        api_key = model_config.get("apiKey", "")
        if not api_key and "OPENROUTER_API_KEY" in os.environ:
            api_key = os.environ["OPENROUTER_API_KEY"]
        
        if not api_key:
            raise Exception("OpenRouter API 키가 설정되지 않았습니다")
        
        # 요청 템플릿 가져오기
        request_template = model_config.get("requestTemplate", {})
        headers = request_template.get("headers", {}).copy()
        payload = request_template.get("payload", {}).copy()
        
        # API 키 설정
        for key, value in headers.items():
            if isinstance(value, str):
                headers[key] = value.replace("${API_KEY}", api_key)
        
        # 모델 설정
        model_id = model_config.get("id", "")
        payload["model"] = model_id
        payload["messages"] = messages
        payload["temperature"] = model_config.get("temperature", 0.7)
        payload["max_tokens"] = model_config.get("maxTokens", 4096)
        payload["stream"] = False
        
        # 요청 및 응답 처리
        response = requests.post(
            endpoint,
            json=payload,
            headers=headers,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"OpenRouter 응답 오류: {response.status_code}, {response.text}")
        
        result = response.json()
        return result.get("choices", [{}])[0].get("message", {}).get("content", "")
    
    def _call_openrouter_stream(self, messages: List[Dict[str, str]], model_config: Dict[str, Any]) -> Generator[str, None, None]:
        """OpenRouter 스트리밍 호출"""
        endpoint = model_config.get("endpoint", "")
        if not endpoint:
            raise Exception("OpenRouter 엔드포인트가 설정되지 않았습니다")
        
        api_key = model_config.get("apiKey", "")
        if not api_key and "OPENROUTER_API_KEY" in os.environ:
            api_key = os.environ["OPENROUTER_API_KEY"]
        
        if not api_key:
            raise Exception("OpenRouter API 키가 설정되지 않았습니다")
        
        # 요청 템플릿 가져오기
        request_template = model_config.get("requestTemplate", {})
        headers = request_template.get("headers", {}).copy()
        payload = request_template.get("payload", {}).copy()
        
        # API 키 설정
        for key, value in headers.items():
            if isinstance(value, str):
                headers[key] = value.replace("${API_KEY}", api_key)
        
        # 모델 설정
        model_id = model_config.get("id", "")
        payload["model"] = model_id
        payload["messages"] = messages
        payload["temperature"] = model_config.get("temperature", 0.7)
        payload["max_tokens"] = model_config.get("maxTokens", 4096)
        payload["stream"] = True
        
        # 요청 및 응답 처리
        response = requests.post(
            endpoint,
            json=payload,
            headers=headers,
            stream=True,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"OpenRouter 스트리밍 응답 오류: {response.status_code}, {response.text}")
        
        for chunk in response.iter_lines():
            if chunk:
                try:
                    data = chunk.decode('utf-8')
                    if data.startswith('data: '):
                        data = data[6:]
                    if data == "[DONE]":
                        break
                    
                    json_data = json.loads(data)
                    delta = json_data.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    
                    if content:
                        yield content
                except Exception as e:
                    logger.error(f"OpenRouter 스트리밍 청크 처리 오류: {e}")

# 싱글톤 인스턴스
llm_service = LLMService()