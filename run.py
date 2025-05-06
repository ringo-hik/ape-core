#!/usr/bin/env python3
"""
APE (Agentic Pipeline Engine) 실행 스크립트

이 스크립트는 APE (Agentic Pipeline Engine) API 서버를 시작합니다.
보안 경고 비활성화 및 환경 설정을 처리합니다.
내부망/외부망 빌드 모드를 선택할 수 있습니다.
"""

import os
import sys
import warnings
import logging
import argparse

# 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# 로거 설정
logger = logging.getLogger("run")

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

def parse_arguments():
    """명령줄 인수 파싱"""
    parser = argparse.ArgumentParser(description='APE (Agentic Pipeline Engine) 실행')
    parser.add_argument(
        '--mode', 
        type=str, 
        choices=['internal', 'external'], 
        default='external',
        help='네트워크 모드 선택 (internal: 내부망, external: 외부망, 기본값: external)'
    )
    parser.add_argument(
        '--debug', 
        action='store_true', 
        help='디버그 모드 활성화'
    )
    return parser.parse_args()

# 실행
if __name__ == "__main__":
    # 명령줄 인수 파싱
    args = parse_arguments()
    
    # 디버그 모드 설정
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("디버그 모드 활성화")
    
    # 네트워크 모드 설정
    os.environ["NETWORK_MODE"] = args.mode
    logger.info(f"네트워크 모드: {args.mode.upper()}")
    
    # 보안 경고 비활성화
    disable_security_warnings()
    
    # 환경 변수 로드 (.env 파일)
    try:
        from dotenv import load_dotenv
        dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        if os.path.exists(dotenv_path):
            load_dotenv(dotenv_path)
            logger.debug(f".env 파일 로드: {dotenv_path}")
    except ImportError:
        logger.warning("python-dotenv가 설치되지 않았습니다. .env 파일을 사용할 수 없습니다.")
    
    # 네트워크 모드에 따른 설정 로드
    from config.network_config import set_network_mode
    set_network_mode(args.mode)
    
    # main 모듈 임포트 및 실행
    from main import init_system, start_server
    
    # 시스템 초기화
    init_system()
    
    # 서버 시작
    start_server()
