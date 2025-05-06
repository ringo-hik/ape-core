"""
네트워크 설정 관리 모듈

이 모듈은 APE의 내부망/외부망 연결 설정을 관리합니다.
서로 다른 네트워크 환경을 완전히 분리하여 관리할 수 있게 합니다.
"""

import os
import logging
import json
from typing import Dict, Any, List, Optional, Union, Literal
from pathlib import Path

from src.core.env_loader import get_env, get_boolean_env, get_int_env, get_float_env

# 로거 설정
logger = logging.getLogger("network_config")

# 네트워크 모드 설정
NetworkMode = Literal["internal", "external", "hybrid"]

# 기본 네트워크 모드는 환경 변수에서 가져옴 (없으면 hybrid)
NETWORK_MODE = get_env("NETWORK_MODE", "hybrid").lower()
if NETWORK_MODE not in ["internal", "external", "hybrid"]:
    logger.warning(f"알 수 없는 네트워크 모드: {NETWORK_MODE}, 기본값 'hybrid'로 설정됩니다.")
    NETWORK_MODE = "hybrid"

# 네트워크 분리 강제 여부
STRICT_NETWORK_SEPARATION = get_boolean_env("STRICT_NETWORK_SEPARATION", False)

# 내부망 설정
INTERNAL_NETWORK_ENABLED = NETWORK_MODE in ["internal", "hybrid"]
INTERNAL_NETWORK_UNAVAILABLE_POLICY = get_env("INTERNAL_NETWORK_UNAVAILABLE_POLICY", "fallback_if_possible")  # fallback_if_possible, fail, ignore

# 외부망 설정
EXTERNAL_NETWORK_ENABLED = NETWORK_MODE in ["external", "hybrid"]
EXTERNAL_NETWORK_UNAVAILABLE_POLICY = get_env("EXTERNAL_NETWORK_UNAVAILABLE_POLICY", "fallback_if_possible")  # fallback_if_possible, fail, ignore

# 내부망 LLM 설정
INTERNAL_LLM_ENDPOINT = get_env("INTERNAL_LLM_ENDPOINT", "http://internal-llm-service/api")
INTERNAL_LLM_API_KEY = get_env("INTERNAL_LLM_API_KEY", "")
INTERNAL_LLM_TIMEOUT = get_int_env("INTERNAL_LLM_TIMEOUT", 30)
INTERNAL_LLM_VERIFY_SSL = get_boolean_env("INTERNAL_LLM_VERIFY_SSL", False)

# 외부망 LLM 설정
EXTERNAL_LLM_PROVIDER = get_env("EXTERNAL_LLM_PROVIDER", "openrouter")
OPENROUTER_ENDPOINT = get_env("OPENROUTER_ENDPOINT", "https://openrouter.ai/api/v1/chat/completions")
OPENROUTER_API_KEY = get_env("OPENROUTER_API_KEY", "")
EXTERNAL_LLM_TIMEOUT = get_int_env("EXTERNAL_LLM_TIMEOUT", 30)

def get_network_mode() -> str:
    """현재 네트워크 모드 반환"""
    return NETWORK_MODE

def is_internal_network_enabled() -> bool:
    """내부망 사용 가능 여부 반환"""
    return INTERNAL_NETWORK_ENABLED

def is_external_network_enabled() -> bool:
    """외부망 사용 가능 여부 반환"""
    return EXTERNAL_NETWORK_ENABLED

def is_strict_network_separation() -> bool:
    """엄격한 네트워크 분리 모드 여부 반환"""
    return STRICT_NETWORK_SEPARATION

def can_fallback_to_external() -> bool:
    """내부망 실패 시 외부망으로 대체 가능 여부 반환"""
    if STRICT_NETWORK_SEPARATION and NETWORK_MODE == "internal":
        return False
    
    return (INTERNAL_NETWORK_UNAVAILABLE_POLICY == "fallback_if_possible" and
            EXTERNAL_NETWORK_ENABLED)

def can_fallback_to_internal() -> bool:
    """외부망 실패 시 내부망으로 대체 가능 여부 반환"""
    if STRICT_NETWORK_SEPARATION and NETWORK_MODE == "external":
        return False
    
    return (EXTERNAL_NETWORK_UNAVAILABLE_POLICY == "fallback_if_possible" and
            INTERNAL_NETWORK_ENABLED)

def get_internal_llm_config() -> Dict[str, Any]:
    """내부망 LLM 설정 반환"""
    return {
        "endpoint": INTERNAL_LLM_ENDPOINT,
        "api_key": INTERNAL_LLM_API_KEY,
        "timeout": INTERNAL_LLM_TIMEOUT,
        "verify_ssl": INTERNAL_LLM_VERIFY_SSL
    }

def get_external_llm_config() -> Dict[str, Any]:
    """외부망 LLM 설정 반환"""
    return {
        "provider": EXTERNAL_LLM_PROVIDER,
        "openrouter_endpoint": OPENROUTER_ENDPOINT,
        "openrouter_api_key": OPENROUTER_API_KEY,
        "timeout": EXTERNAL_LLM_TIMEOUT
    }

def get_network_info() -> Dict[str, Any]:
    """현재 네트워크 설정 정보 반환"""
    return {
        "mode": NETWORK_MODE,
        "strict_separation": STRICT_NETWORK_SEPARATION,
        "internal": {
            "enabled": INTERNAL_NETWORK_ENABLED,
            "unavailable_policy": INTERNAL_NETWORK_UNAVAILABLE_POLICY,
            "llm_endpoint": INTERNAL_LLM_ENDPOINT,
            "llm_api_key_set": bool(INTERNAL_LLM_API_KEY)
        },
        "external": {
            "enabled": EXTERNAL_NETWORK_ENABLED,
            "unavailable_policy": EXTERNAL_NETWORK_UNAVAILABLE_POLICY,
            "llm_provider": EXTERNAL_LLM_PROVIDER,
            "openrouter_endpoint": OPENROUTER_ENDPOINT,
            "openrouter_api_key_set": bool(OPENROUTER_API_KEY)
        },
        "fallback": {
            "internal_to_external": can_fallback_to_external(),
            "external_to_internal": can_fallback_to_internal()
        }
    }