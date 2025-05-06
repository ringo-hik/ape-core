"""AI Agent Core API 서버

이 모듈은 온프레미스 AI Agent 시스템 API 서버를 시작하고 관리합니다.
내부망/외부망 모드에 따라 다른 설정을 사용합니다.
"""

import os
import sys
import logging
import warnings
import uvicorn
import requests
from typing import Dict, Any

# 환경 변수 로드 (시작 전 반드시 필요)
from dotenv import load_dotenv
load_dotenv()

# SSL 경고 비활성화
warnings.filterwarnings('ignore', message='Unverified HTTPS request')
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

# 설정 모듈 임포트
from src.core.config import load_config, get_settings
from src.core.router import app
from src.core.llm_service import LLMService
from src.core.network_manager import network_manager

# 로거 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("main")

# LLM 서비스 초기화
llm_service = LLMService()

def init_system():
    """시스템 초기화"""
    logger.info("AI Agent 시스템 초기화")
    
    # 네트워크 모드 확인
    network_mode = os.environ.get("NETWORK_MODE", "external")
    logger.info(f"네트워크 모드: {network_mode.upper()}")
    
    # 설정 로드
    load_config()
    settings = get_settings()
    
    # 데이터 디렉토리 생성
    os.makedirs("data/docs", exist_ok=True)
    os.makedirs("data/chroma_db", exist_ok=True)
    
    # 네트워크 모드에 따른 기본 모델 선택
    default_model = network_manager.get_default_model_key()
    logger.info(f"기본 모델: {default_model}")
    
    # LLM 서비스 초기화
    llm_service.change_model(default_model)
    
    # 네트워크 상태 정보 로깅
    network_status = network_manager.get_status()
    logger.info(f"사용 가능한 모델: {network_status['model_keys']}")
    
    logger.info("시스템 초기화 완료")

def start_server():
    """API 서버 시작"""
    # 설정 가져오기
    settings = get_settings()
    host = settings["api"]["host"]
    port = int(settings["api"]["port"])
    use_ssl = settings["security"]["use_ssl"]
    ssl_cert = settings["security"]["ssl_cert"]
    ssl_key = settings["security"]["ssl_key"]
    
    # 네트워크 모드 표시
    network_mode = network_manager.current_mode
    logger.info(f"AI Agent Core API 서버 시작 (호스트: {host}, 포트: {port}, 네트워크 모드: {network_mode.upper()})")
    
    # SSL 설정
    ssl_certfile = ssl_cert if use_ssl else None
    ssl_keyfile = ssl_key if use_ssl else None
    
    # 서버 시작
    uvicorn.run(
        app,
        host=host,
        port=port,
        ssl_certfile=ssl_certfile,
        ssl_keyfile=ssl_keyfile
    )

def get_llm_service() -> LLMService:
    """LLM 서비스 인스턴스 반환"""
    return llm_service

def get_network_info() -> Dict[str, Any]:
    """현재 네트워크 상태 정보 반환"""
    return network_manager.get_status()

if __name__ == "__main__":
    # 네트워크 모드에 따른 API 키 환경 변수 체크
    network_mode = os.environ.get("NETWORK_MODE", "external")
    
    if network_mode == "external" and "OPENROUTER_API_KEY" not in os.environ:
        logger.warning("외부망 모드에서 OPENROUTER_API_KEY 환경 변수가 설정되지 않았습니다.")
    
    if network_mode == "internal" and "INTERNAL_LLM_API_KEY" not in os.environ:
        logger.warning("내부망 모드에서 INTERNAL_LLM_API_KEY 환경 변수가 설정되지 않았습니다.")
    
    # 시스템 초기화
    init_system()
    
    # 서버 시작
    start_server()
