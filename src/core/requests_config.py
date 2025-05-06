"""
Requests 라이브러리 설정

이 모듈은 안전한 HTTP 요청을 위한 세션 및 기본 설정을 제공합니다.
"""

import logging
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import requests

# 로깅 설정
logger = logging.getLogger("requests_config")

def get_secure_http_session(timeout: int = 30, max_retries: int = 3,
                           verify_ssl: bool = False) -> requests.Session:
    """
    안전한 HTTP 세션 생성 및 반환
    
    Args:
        timeout: 요청 타임아웃 (초)
        max_retries: 최대 재시도 횟수
        verify_ssl: SSL 인증서 검증 여부
        
    Returns:
        구성된 requests 세션
    """
    # 재시도 전략 설정
    retry_strategy = Retry(
        total=max_retries,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
    )
    
    # 어댑터 생성 및 세션에 추가
    adapter = HTTPAdapter(max_retries=retry_strategy)
    
    # 기본 세션 구성
    session = requests.Session()
    
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # 기존 설정 유지를 위한 추가 구성
    session.verify = verify_ssl
    session.timeout = timeout
    
    # 기본 헤더 설정
    session.headers.update({
        "Accept": "application/json",
        "Content-Type": "application/json"
    })
    
    logger.info(f"HTTP 세션 생성 완료 (타임아웃: {timeout}초, 최대 재시도: {max_retries}회, SSL 검증: {verify_ssl})")
    return session

def make_api_request(url: str, method: str = "GET", data: dict = None, 
                    params: dict = None, headers: dict = None, 
                    verify_ssl: bool = False, timeout: int = 30) -> dict:
    """
    API 요청 수행 및 응답 반환
    
    Args:
        url: API 엔드포인트 URL
        method: HTTP 메서드 (GET, POST, PUT, DELETE 등)
        data: 요청 본문 데이터
        params: URL 쿼리 파라미터
        headers: HTTP 헤더
        verify_ssl: SSL 인증서 검증 여부
        timeout: 요청 타임아웃 (초)
        
    Returns:
        응답 데이터 (JSON)
        
    Raises:
        requests.RequestException: API 요청 중 발생한 오류
    """
    session = get_secure_http_session(timeout=timeout, verify_ssl=verify_ssl)
    
    # 커스텀 헤더 추가
    if headers:
        session.headers.update(headers)
    
    # 메서드에 따른 요청 실행
    try:
        logger.info(f"API 요청: {method} {url}")
        
        if method.upper() == "GET":
            response = session.get(url, params=params)
        elif method.upper() == "POST":
            response = session.post(url, json=data, params=params)
        elif method.upper() == "PUT":
            response = session.put(url, json=data, params=params)
        elif method.upper() == "DELETE":
            response = session.delete(url, json=data, params=params)
        else:
            logger.error(f"지원되지 않는 HTTP 메서드: {method}")
            raise ValueError(f"지원되지 않는 HTTP 메서드: {method}")
        
        # 응답 상태 코드 확인
        response.raise_for_status()
        
        # JSON 응답 파싱
        if response.text:
            try:
                return response.json()
            except ValueError:
                logger.warning("JSON 아닌 응답 수신")
                return {"text": response.text}
        else:
            return {}
            
    except requests.RequestException as e:
        logger.error(f"API 요청 오류: {e}")
        return {"error": str(e)}