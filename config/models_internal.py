"""
내부망 LLM 모델 구성

이 파일은 내부망에서 사용 가능한 LLM 모델 설정을 정의합니다.
모든 모델 엔드포인트는 내부망에서만 접근 가능합니다.
"""

from src.core.env_loader import get_env, get_int_env, get_float_env, get_boolean_env

# 내부 모델 구성
INTERNAL_MODELS = {
    "internal-model": {
        "name": "내부 LLM 모델",
        "id": "internal-model-v1",
        "description": "내부망 LLM 서비스 모델",
        "provider": "internal",
        "endpoint": get_env("INTERNAL_LLM_ENDPOINT", "http://internal-llm-service/api"),
        "apiKey": get_env("INTERNAL_LLM_API_KEY", ""),
        "maxTokens": get_int_env("INTERNAL_LLM_MAX_TOKENS", 4096),
        "temperature": get_float_env("INTERNAL_LLM_TEMPERATURE", 0.7),
        "requestTemplate": {
            "headers": {
                "Authorization": "Bearer ${API_KEY}",
                "Content-Type": "application/json"
            },
            "payload": {
                "model": "internal-model-v1",
                "max_tokens": 4096,
                "temperature": "${TEMPERATURE}",
                "stream": "${STREAM}",
                "messages": []
            }
        }
    },
    "internal-model-ko": {
        "name": "내부 한국어 LLM 모델",
        "id": "internal-model-ko-v1",
        "description": "내부망 한국어 특화 LLM 서비스 모델",
        "provider": "internal",
        "endpoint": get_env("INTERNAL_LLM_KO_ENDPOINT", "http://internal-llm-ko-service/api"),
        "apiKey": get_env("INTERNAL_LLM_KO_API_KEY", ""),
        "maxTokens": get_int_env("INTERNAL_LLM_KO_MAX_TOKENS", 4096),
        "temperature": get_float_env("INTERNAL_LLM_KO_TEMPERATURE", 0.7),
        "requestTemplate": {
            "headers": {
                "Authorization": "Bearer ${API_KEY}",
                "Content-Type": "application/json"
            },
            "payload": {
                "model": "internal-model-ko-v1",
                "max_tokens": 4096,
                "temperature": "${TEMPERATURE}",
                "stream": "${STREAM}",
                "messages": []
            }
        }
    },
    "internal-embedding": {
        "name": "내부 임베딩 모델",
        "id": "internal-embedding-v1",
        "description": "내부망 임베딩 서비스 모델",
        "provider": "internal",
        "endpoint": get_env("INTERNAL_EMBEDDING_ENDPOINT", "http://internal-embedding-service/api"),
        "apiKey": get_env("INTERNAL_EMBEDDING_API_KEY", ""),
        "maxTokens": 0,  # 임베딩 모델은 max_tokens가 필요 없음
        "temperature": 0.0,  # 임베딩 모델은 temperature가 필요 없음
        "requestTemplate": {
            "headers": {
                "Authorization": "Bearer ${API_KEY}",
                "Content-Type": "application/json"
            },
            "payload": {
                "model": "internal-embedding-v1",
                "input": [],
                "encoding_format": "float"
            }
        }
    }
}

# 기본 내부 모델 키
DEFAULT_INTERNAL_MODEL = "internal-model"

def get_internal_models():
    """내부망 모델 구성 반환"""
    return INTERNAL_MODELS

def get_default_internal_model():
    """기본 내부망 모델 키 반환"""
    return DEFAULT_INTERNAL_MODEL