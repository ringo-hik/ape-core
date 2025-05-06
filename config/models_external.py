"""
외부망 LLM 모델 구성

이 파일은 외부망에서 사용 가능한 LLM 모델 설정을 정의합니다.
모든 모델 엔드포인트는 외부망을 통해 접근합니다.
"""

from src.core.env_loader import get_env, get_int_env, get_float_env, get_boolean_env

# 외부 모델 구성
EXTERNAL_MODELS = {
    "openrouter-llama": {
        "name": "OpenRouter Llama3",
        "id": "meta/llama-3-70b-instruct",
        "description": "OpenRouter를 통한 Llama3 70B 모델",
        "provider": "openrouter",
        "endpoint": get_env("OPENROUTER_ENDPOINT", "https://openrouter.ai/api/v1/chat/completions"),
        "apiKey": get_env("OPENROUTER_API_KEY", ""),
        "maxTokens": get_int_env("OPENROUTER_MAX_TOKENS", 4096),
        "temperature": get_float_env("OPENROUTER_TEMPERATURE", 0.7),
        "requestTemplate": {
            "headers": {
                "Authorization": "Bearer ${API_KEY}",
                "HTTP-Referer": "APE-Core-API",
                "X-Title": "APE (Agentic Pipeline Engine)",
                "Content-Type": "application/json"
            },
            "payload": {
                "model": "meta/llama-3-70b-instruct",
                "max_tokens": 4096,
                "temperature": "${TEMPERATURE}",
                "stream": "${STREAM}",
                "messages": []
            }
        }
    },
    "openrouter-mixtral": {
        "name": "OpenRouter Mixtral",
        "id": "mistralai/mixtral-8x7b-instruct",
        "description": "OpenRouter를 통한 Mixtral 8x7B 모델",
        "provider": "openrouter",
        "endpoint": get_env("OPENROUTER_ENDPOINT", "https://openrouter.ai/api/v1/chat/completions"),
        "apiKey": get_env("OPENROUTER_API_KEY", ""),
        "maxTokens": get_int_env("OPENROUTER_MAX_TOKENS", 4096),
        "temperature": get_float_env("OPENROUTER_TEMPERATURE", 0.7),
        "requestTemplate": {
            "headers": {
                "Authorization": "Bearer ${API_KEY}",
                "HTTP-Referer": "APE-Core-API",
                "X-Title": "APE (Agentic Pipeline Engine)",
                "Content-Type": "application/json"
            },
            "payload": {
                "model": "mistralai/mixtral-8x7b-instruct",
                "max_tokens": 4096,
                "temperature": "${TEMPERATURE}",
                "stream": "${STREAM}",
                "messages": []
            }
        }
    }
}

# 기본 외부 모델 키
DEFAULT_EXTERNAL_MODEL = "openrouter-llama"

def get_external_models():
    """외부망 모델 구성 반환"""
    return EXTERNAL_MODELS

def get_default_external_model():
    """기본 외부망 모델 키 반환"""
    return DEFAULT_EXTERNAL_MODEL