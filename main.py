"""AI Agent Core API 서버

이 모듈은 온프레미스 AI Agent 시스템 API 서버를 시작하고 관리합니다.
"""

import os
import sys
import logging
import warnings
import uvicorn
import requests

# SSL 경고 비활성화
warnings.filterwarnings('ignore', message='Unverified HTTPS request')
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

# 설정 모듈 임포트
from src.core.config import load_config, get_settings
from src.core.router import app
from src.core.llm_service import LLMService

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
    
    # 설정 로드
    load_config()
    settings = get_settings()
    
    # 데이터 디렉토리 생성
    os.makedirs("data/docs", exist_ok=True)
    os.makedirs("data/chroma_db", exist_ok=True)
    
    # LLM 서비스 초기화
    llm_service.change_model(settings["llm"]["default_model"])
    
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
    
    logger.info(f"AI Agent Core API 서버 시작 (호스트: {host}, 포트: {port})")
    
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

if __name__ == "__main__":
    # API 키 환경 변수 체크
    if "ANTHROPIC_API_KEY" not in os.environ and "OPENROUTER_API_KEY" not in os.environ:
        logger.warning("ANTHROPIC_API_KEY 또는 OPENROUTER_API_KEY 환경 변수가 설정되지 않았습니다.")
    
    # 시스템 초기화
    init_system()
    
    # 서버 시작
    start_server()
