"""
APE (Agentic Pipeline Engine) 시스템 설정

이 파일은 APE (Agentic Pipeline Engine) 시스템의 주요 설정을 포함합니다.
로컬 호스트 LLM API 설정, 기본 모델 구성 등을 포함합니다.
.env 파일에서 환경 변수를 로드합니다.
"""

import os
import logging
import json
from typing import Dict, Any, List, Optional

# 환경 변수 로더 모듈 임포트
from src.core.env_loader import get_env, get_boolean_env, get_int_env, get_float_env, get_list_env, get_dict_env, get_db_uri_env

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# API 설정
API_HOST = get_env("API_HOST", "0.0.0.0")
API_PORT = get_int_env("API_PORT", 8001)
API_TIMEOUT = get_int_env("API_TIMEOUT", 120)  # 초 단위
API_STREAM = get_boolean_env("API_STREAM", True)

# 보안 설정
USE_SSL = get_boolean_env("USE_SSL", False)
SSL_CERT = get_env("SSL_CERT")
SSL_KEY = get_env("SSL_KEY")
VERIFY_SSL = get_boolean_env("VERIFY_SSL", False)

# 기본 모델 설정
DEFAULT_MODEL = get_env("DEFAULT_MODEL", "internal-model")

# 임베딩 모델 설정
EMBEDDING_MODEL = {
    "name": get_env("EMBEDDING_MODEL_NAME", "KoSimCSE-roberta"),
    "path": get_env("EMBEDDING_MODEL_PATH", "models/KoSimCSE-roberta-multitask"),
    "dimension": get_int_env("EMBEDDING_DIMENSION", 768),
    "max_seq_length": get_int_env("EMBEDDING_MAX_SEQ_LENGTH", 512)
}

# 모델 구성
MODELS_CONFIG = {
    "internal-model": {
        "name": "내부 LLM 모델",
        "id": "internal-model-v1",
        "description": "내부망 LLM 서비스 모델",
        "provider": "internal",
        "endpoint": get_env("INTERNAL_LLM_ENDPOINT", "http://internal-llm-service/api"),
        "apiKey": get_env("INTERNAL_LLM_API_KEY", ""),
        "maxTokens": 4096,
        "temperature": 0.7,
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
    "openrouter-llama": {
        "name": "OpenRouter Llama3",
        "id": "meta/llama-3-70b-instruct",
        "description": "OpenRouter를 통한 Llama3 70B 모델",
        "provider": "openrouter",
        "endpoint": get_env("OPENROUTER_ENDPOINT", "https://openrouter.ai/api/v1/chat/completions"),
        "apiKey": get_env("OPENROUTER_API_KEY", ""),
        "maxTokens": 4096,
        "temperature": 0.7,
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
    }
}

def get_default_model() -> str:
    """기본 모델 키 반환"""
    # 내부망 모델이 사용 가능한지 확인
    internal_endpoint = MODELS_CONFIG.get("internal-model", {}).get("endpoint", "")
    internal_key = MODELS_CONFIG.get("internal-model", {}).get("apiKey", "")
    
    if internal_endpoint and internal_key and DEFAULT_MODEL == "internal-model":
        # 내부망 모델 사용 가능하면 사용
        return "internal-model"
    elif "OPENROUTER_API_KEY" in os.environ:
        # 내부망 모델을 사용할 수 없고 OpenRouter 키가 있으면 OpenRouter 모델 사용
        return "openrouter-llama"  # 기본 오픈라우터 모델
    else:
        # 기본값 반환 (DEFAULT_MODEL이 사용 가능하면 사용)
        if DEFAULT_MODEL in MODELS_CONFIG:
            return DEFAULT_MODEL
        # 그 외의 경우 사용 가능한 첫 번째 모델 반환
        available_models = list(MODELS_CONFIG.keys())
        return available_models[0] if available_models else "internal-model"

def set_default_model(model_key: str) -> bool:
    """기본 모델 변경
    
    Args:
        model_key: 모델 키
        
    Returns:
        성공 여부
    """
    global DEFAULT_MODEL
    
    if model_key not in MODELS_CONFIG:
        return False
    
    DEFAULT_MODEL = model_key
    return True

def get_available_models() -> List[str]:
    """사용 가능한 모델 키 목록 반환"""
    available_models = []
    
    # 내부망 모델 사용 가능 여부 확인
    internal_model = "internal-model"
    internal_endpoint = MODELS_CONFIG.get(internal_model, {}).get("endpoint", "")
    internal_key = MODELS_CONFIG.get(internal_model, {}).get("apiKey", "")
    
    if internal_endpoint and internal_key:
        available_models.append(internal_model)
    
    # OpenRouter 모델 사용 가능 여부 확인
    if "OPENROUTER_API_KEY" in os.environ:
        for model_key, model_config in MODELS_CONFIG.items():
            if model_config.get("provider") == "openrouter":
                available_models.append(model_key)
    
    return available_models

def get_model_config(model_key: str) -> Dict[str, Any]:
    """
    모델 구성 반환
    
    Args:
        model_key: 모델 키
        
    Returns:
        모델 구성 사전
    """
    if model_key not in MODELS_CONFIG:
        raise ValueError(f"알 수 없는 모델 키: {model_key}")
        
    return MODELS_CONFIG[model_key]

# SWDP 툴 설정
SWDP_TOOL_CONFIG = {
    "enabled": get_boolean_env("SWDP_ENABLED", True),
    "api_url": get_env("SWDP_API_URL", "https://swdp.example.com/api"),
    "username": get_env("SWDP_USERNAME", "swdp_agent"),
    "password": get_env("SWDP_PASSWORD", "swdp_password"),
    "internal_swdp_api": get_env("SWDP_INTERNAL_API", "https://internal-swdp.example.com/api/v1"),
    "verify_ssl": get_boolean_env("VERIFY_SSL", False),
    "timeout": get_int_env("SWDP_TIMEOUT", 30),  # 초 단위
    "db_uri": get_db_uri_env("SWDP_DB_URI", "postgresql://user:password@localhost:5432/swdp_db")
}

def get_swdp_tool_config() -> Dict[str, Any]:
    """
    SWDP 도구 설정 반환
    
    Returns:
        SWDP 도구 설정 사전
    """
    return SWDP_TOOL_CONFIG

# Jira 툴 설정
JIRA_TOOL_CONFIG = {
    "enabled": get_boolean_env("JIRA_ENABLED", True),
    "api_url": get_env("JIRA_API_URL", "https://jira.example.com/rest/api/2"),
    "username": get_env("JIRA_USERNAME", "jira_agent"),
    "password": get_env("JIRA_PASSWORD", "jira_password"),
    "verify_ssl": get_boolean_env("VERIFY_SSL", False),
    "timeout": get_int_env("JIRA_TIMEOUT", 30),  # 초 단위
    "default_project": get_env("JIRA_DEFAULT_PROJECT", "DEMO")
}

def get_jira_tool_config() -> Dict[str, Any]:
    """
    Jira 도구 설정 반환
    
    Returns:
        Jira 도구 설정 사전
    """
    return JIRA_TOOL_CONFIG

# Bitbucket 툴 설정
BITBUCKET_TOOL_CONFIG = {
    "enabled": get_boolean_env("BITBUCKET_ENABLED", True),
    "api_url": get_env("BITBUCKET_API_URL", "https://bitbucket.example.com/rest/api/1.0"),
    "username": get_env("BITBUCKET_USERNAME", "bitbucket_agent"),
    "password": get_env("BITBUCKET_PASSWORD", "bitbucket_password"),
    "verify_ssl": get_boolean_env("VERIFY_SSL", False),
    "timeout": get_int_env("BITBUCKET_TIMEOUT", 30)  # 초 단위
}

def get_bitbucket_tool_config() -> Dict[str, Any]:
    """
    Bitbucket 도구 설정 반환
    
    Returns:
        Bitbucket 도구 설정 사전
    """
    return BITBUCKET_TOOL_CONFIG

# Pocket 툴 설정
POCKET_TOOL_CONFIG = {
    "enabled": get_boolean_env("POCKET_ENABLED", True),
    "api_url": get_env("POCKET_API_URL", "https://pocket.example.com/api"),
    "username": get_env("POCKET_USERNAME", "pocket_user"),
    "password": get_env("POCKET_PASSWORD", "pocket_password"),
    "region_name": get_env("POCKET_REGION", "us-east-1"),
    "verify_ssl": get_boolean_env("VERIFY_SSL", False),
    "timeout": get_int_env("POCKET_TIMEOUT", 30)  # 초 단위
}

def get_pocket_tool_config() -> Dict[str, Any]:
    """
    Pocket 도구 설정 반환
    
    Returns:
        Pocket 도구 설정 사전
    """
    return POCKET_TOOL_CONFIG
    
# S3 툴 설정
S3_TOOL_CONFIG = {
    "enabled": get_boolean_env("S3_ENABLED", True),
    "api_url": get_env("S3_API_URL", "https://s3.amazonaws.com"),
    "username": get_env("S3_USERNAME", "s3_user"),
    "password": get_env("S3_PASSWORD", "s3_password"),
    "region_name": get_env("S3_REGION", "us-east-1"),
    "verify_ssl": get_boolean_env("VERIFY_SSL", False),
    "timeout": get_int_env("S3_TIMEOUT", 30)  # 초 단위
}

def get_s3_tool_config() -> Dict[str, Any]:
    """
    S3 도구 설정 반환
    
    Returns:
        S3 도구 설정 사전
    """
    return S3_TOOL_CONFIG