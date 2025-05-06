"""
설정 로더 모듈

settings.json 파일에서 애플리케이션 설정을 로드하고 관리하는 기능을 제공합니다.
"""

import os
import json
import logging
import re
from typing import Dict, Any, Optional
from pathlib import Path

# 환경 변수 로더 임포트
from src.core.env_loader import get_env, get_boolean_env, get_int_env, get_float_env

# 로깅 설정
logger = logging.getLogger("settings_loader")

def load_settings(settings_file: Optional[str] = None) -> Dict[str, Any]:
    """
    settings.json 파일에서 애플리케이션 설정을 로드합니다.
    
    Args:
        settings_file: settings.json 파일 경로 (기본값: config/settings.json)
        
    Returns:
        설정 사전
    """
    if settings_file is None:
        # 프로젝트 루트 디렉토리 찾기
        project_root = Path(__file__).parent.parent.parent.absolute()
        settings_file = project_root / "config" / "settings.json"
    
    # settings.json 파일 로드
    try:
        with open(settings_file, "r", encoding="utf-8") as f:
            settings = json.load(f)
        
        # 환경 변수 플레이스홀더 처리
        settings = _replace_env_vars(settings)
        logger.info(f"설정 파일 로드 완료: {settings_file}")
        return settings
    except FileNotFoundError:
        logger.warning(f"설정 파일을 찾을 수 없습니다: {settings_file}")
        return {}
    except json.JSONDecodeError:
        logger.error(f"설정 파일 파싱 오류: {settings_file}")
        return {}

def _replace_env_vars(obj: Any) -> Any:
    """
    객체에서 환경 변수 플레이스홀더를 실제 값으로 대체합니다.
    
    Args:
        obj: 대체할 객체 (사전, 리스트, 또는 기본 타입)
        
    Returns:
        환경 변수가 대체된 객체
    """
    if isinstance(obj, dict):
        # 사전의 경우 각 값에 대해 재귀 호출
        return {k: _replace_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        # 리스트의 경우 각 항목에 대해 재귀 호출
        return [_replace_env_vars(v) for v in obj]
    elif isinstance(obj, str):
        # 문자열의 경우 환경 변수 플레이스홀더 대체
        return _replace_env_var_in_string(obj)
    else:
        # 기타 타입은 그대로 반환
        return obj

def _replace_env_var_in_string(s: str) -> Any:
    """
    문자열에서 환경 변수 플레이스홀더를 실제 값으로 대체합니다.
    
    Args:
        s: 대체할 문자열
        
    Returns:
        환경 변수가 대체된 값 (문자열, 정수, 실수, 또는 부울)
    """
    if not isinstance(s, str):
        return s
    
    # ${VAR} 또는 ${VAR:default} 형식의 플레이스홀더 처리
    pattern = r"\${([A-Za-z0-9_]+)(?::([^}]+))?}"
    
    def replace_match(match):
        var_name = match.group(1)
        default_value = match.group(2)
        
        # 환경 변수 값 가져오기
        env_value = os.environ.get(var_name)
        
        # 환경 변수가 없고 기본값이 있는 경우
        if env_value is None and default_value is not None:
            return default_value
        
        # 환경 변수가 있는 경우
        if env_value is not None:
            return env_value
        
        # 환경 변수와 기본값이 모두 없는 경우
        return ""
    
    # 플레이스홀더 대체
    result = re.sub(pattern, replace_match, s)
    
    # 결과 타입 변환
    return _convert_type(result)

def _convert_type(s: str) -> Any:
    """
    문자열을 적절한 타입으로 변환합니다.
    
    Args:
        s: 변환할 문자열
        
    Returns:
        변환된 값 (문자열, 정수, 실수, 또는 부울)
    """
    # 부울 처리
    if s.lower() in ("true", "yes", "y", "t", "1"):
        return True
    if s.lower() in ("false", "no", "n", "f", "0"):
        return False
    
    # 정수 처리
    try:
        if s.isdigit() or (s.startswith("-") and s[1:].isdigit()):
            return int(s)
    except ValueError:
        pass
    
    # 실수 처리
    try:
        if "." in s:
            return float(s)
    except ValueError:
        pass
    
    # 기본: 문자열
    return s

# 설정 로드
settings = load_settings()