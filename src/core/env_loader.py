"""
환경 변수 로더 모듈

.env 파일에서 환경 변수를 로드하고 관리하는 기능을 제공합니다.
"""

import os
import logging
import urllib.parse
from typing import Dict, Any, Optional, Union, List
from pathlib import Path
from dotenv import load_dotenv

# 로깅 설정
logger = logging.getLogger("env_loader")

def load_env(env_file: Optional[str] = None) -> None:
    """
    .env 파일에서 환경 변수를 로드합니다.
    
    Args:
        env_file: .env 파일 경로 (기본값: 프로젝트 루트 디렉토리의 .env)
    """
    if env_file is None:
        # 프로젝트 루트 디렉토리 찾기
        project_root = Path(__file__).parent.parent.parent.absolute()
        env_file = project_root / ".env"
    
    # 환경 변수 로드
    load_dotenv(env_file)
    logger.info(f".env 파일 로드 완료: {env_file}")

def get_env(key: str, default: Any = None) -> Any:
    """
    환경 변수 값을 가져옵니다.
    
    Args:
        key: 환경 변수 이름
        default: 기본값 (환경 변수가 없는 경우 반환)
        
    Returns:
        환경 변수 값 또는 기본값
    """
    return os.environ.get(key, default)

def get_boolean_env(key: str, default: bool = False) -> bool:
    """
    부울 환경 변수 값을 가져옵니다.
    
    Args:
        key: 환경 변수 이름
        default: 기본값 (환경 변수가 없는 경우 반환)
        
    Returns:
        부울 환경 변수 값 (true, 1, yes, y는 True로 변환)
    """
    value = os.environ.get(key)
    if value is None:
        return default
    
    return value.lower() in ("true", "1", "yes", "y", "t")

def get_int_env(key: str, default: int = 0) -> int:
    """
    정수 환경 변수 값을 가져옵니다.
    
    Args:
        key: 환경 변수 이름
        default: 기본값 (환경 변수가 없거나 정수로 변환할 수 없는 경우 반환)
        
    Returns:
        정수 환경 변수 값
    """
    value = os.environ.get(key)
    if value is None:
        return default
    
    try:
        return int(value)
    except ValueError:
        logger.warning(f"환경 변수 {key}를 정수로 변환할 수 없습니다: {value}")
        return default

def get_float_env(key: str, default: float = 0.0) -> float:
    """
    실수 환경 변수 값을 가져옵니다.
    
    Args:
        key: 환경 변수 이름
        default: 기본값 (환경 변수가 없거나 실수로 변환할 수 없는 경우 반환)
        
    Returns:
        실수 환경 변수 값
    """
    value = os.environ.get(key)
    if value is None:
        return default
    
    try:
        return float(value)
    except ValueError:
        logger.warning(f"환경 변수 {key}를 실수로 변환할 수 없습니다: {value}")
        return default

def get_list_env(key: str, delimiter: str = ",", default: Optional[List[str]] = None) -> List[str]:
    """
    리스트 환경 변수 값을 가져옵니다.
    
    Args:
        key: 환경 변수 이름
        delimiter: 구분자 (기본값: ',')
        default: 기본값 (환경 변수가 없는 경우 반환)
        
    Returns:
        리스트 환경 변수 값
    """
    value = os.environ.get(key)
    if value is None:
        return default or []
    
    return [item.strip() for item in value.split(delimiter)]

def get_dict_env(key: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    딕셔너리 환경 변수 값을 가져옵니다. (JSON 형식)
    
    Args:
        key: 환경 변수 이름
        default: 기본값 (환경 변수가 없거나 JSON으로 파싱할 수 없는 경우 반환)
        
    Returns:
        딕셔너리 환경 변수 값
    """
    import json
    
    value = os.environ.get(key)
    if value is None:
        return default or {}
    
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        logger.warning(f"환경 변수 {key}를 JSON으로 파싱할 수 없습니다: {value}")
        return default or {}

def get_db_uri_env(key: str, default: str = "") -> str:
    """
    데이터베이스 URI 환경 변수 값을 가져옵니다.
    사용자 이름과 비밀번호에 특수 문자(@, :, / 등)가 포함된 경우 URL 인코딩을 적용합니다.
    
    Args:
        key: 환경 변수 이름
        default: 기본값 (환경 변수가 없는 경우 반환)
        
    Returns:
        URL 인코딩이 적용된 데이터베이스 URI 문자열
    """
    uri = os.environ.get(key, default)
    if not uri:
        return default
    
    # URI 분석하여 사용자 이름과 비밀번호 추출 및 URL 인코딩 적용
    # 형식: postgresql://username:password@hostname:port/database
    try:
        if '@' in uri:
            # 스키마/프로토콜 분리
            scheme, rest = uri.split('://', 1)
            
            # 인증 정보와 호스트 정보 분리
            auth_part, host_part = rest.split('@', 1)
            
            # 사용자 이름과 비밀번호 분리
            if ':' in auth_part:
                username, password = auth_part.split(':', 1)
                
                # URL 인코딩 적용
                encoded_username = urllib.parse.quote_plus(username)
                encoded_password = urllib.parse.quote_plus(password)
                
                # URI 재구성
                return f"{scheme}://{encoded_username}:{encoded_password}@{host_part}"
            
    except Exception as e:
        logger.warning(f"데이터베이스 URI 인코딩 중 오류 발생: {e}")
    
    # 파싱에 실패하거나 인증 정보가 없는 경우 원래 URI 반환
    return uri

# 초기화: 모듈 임포트 시 자동으로 환경 변수 로드
load_env()