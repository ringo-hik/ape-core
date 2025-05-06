#!/usr/bin/env python3
"""
APE (Agentic Pipeline Engine) 실행 스크립트

이 스크립트는 APE (Agentic Pipeline Engine) API 서버를 시작합니다.
보안 경고 비활성화 및 환경 설정을 처리합니다.
"""

import os
import sys
import warnings
import logging

# 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# 보안 경고 비활성화
def disable_security_warnings():
    """
    보안 관련 경고 비활성화
    - Unverified HTTPS 요청 경고
    - InsecureRequestWarning
    """
    warnings.filterwarnings('ignore', message='Unverified HTTPS request')
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except ImportError:
        pass
    try:
        import requests.packages.urllib3
        requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
    except (ImportError, AttributeError):
        pass

# 실행
if __name__ == "__main__":
    # 보안 경고 비활성화
    disable_security_warnings()
    
    # main 모듈 임포트 및 실행
    from main import init_system, start_server
    
    # 시스템 초기화
    init_system()
    
    # 서버 시작
    start_server()
