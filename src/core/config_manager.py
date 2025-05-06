"""
설정 관리 모듈

시스템 전체 설정을 관리하고 로드하는 기능을 제공합니다.
환경 변수, 설정 파일, 기본값 간의 우선순위를 관리합니다.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, Union, List

# 로깅 설정
logger = logging.getLogger("config_manager")

class ConfigManager:
    """설정 관리 클래스"""
    
    def __init__(self, config_paths: List[str] = None):
        """
        설정 관리자 초기화
        
        Args:
            config_paths: 설정 파일 경로 목록 (선택적)
        """
        self._config: Dict[str, Any] = {}
        self._default_config: Dict[str, Any] = {}
        self._env_prefix = "APE_"
        
        # 기본 설정 파일 경로
        self._config_paths = config_paths or [
            "./config.json",
            "./config.dev.json",
            "./config.prod.json"
        ]
        
        # 기본 설정 초기화
        self._init_default_config()
    
    def _init_default_config(self) -> None:
        """기본 설정 초기화"""
        self._default_config = {
            "server": {
                "host": "localhost",
                "port": 8001,
                "debug": False,
                "cors_origins": ["*"]
            },
            "security": {
                "verify_ssl": False,
                "auto_approve": True,
                "timeout": 30,
                "permissions": {
                    "allow": {"all": True},
                    "deny": []
                }
            },
            "llm": {
                "provider": "openai",
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 2000
            },
            "agents": {
                "enabled": True,
                "default_agent": "orchestrator"
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file": "./logs/ape.log"
            }
        }
        
        # 초기화 시 기본 설정 복사
        self._config = self._default_config.copy()
    
    def load_config(self) -> Dict[str, Any]:
        """
        설정 로드 (파일 + 환경 변수)
        
        Returns:
            현재 설정
        """
        # 1. 먼저 기본 설정 설정
        self._config = self._default_config.copy()
        
        # 2. 설정 파일에서 로드
        for config_path in self._config_paths:
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        file_config = json.load(f)
                        self._deep_update(self._config, file_config)
                    logger.info(f"설정 파일 로드됨: {config_path}")
                except Exception as e:
                    logger.error(f"설정 파일 로드 실패: {config_path}, 오류: {str(e)}")
        
        # 3. 환경 변수에서 로드
        self._load_from_env()
        
        # 4. 설정 검증
        self._validate_config()
        
        return self._config
    
    def _load_from_env(self) -> None:
        """환경 변수에서 설정 로드"""
        for env_name, env_value in os.environ.items():
            # APE_ 접두사로 시작하는 환경 변수만 처리
            if env_name.startswith(self._env_prefix):
                # 환경 변수 이름에서 접두사 제거
                config_key = env_name[len(self._env_prefix):].lower()
                
                # 중첩된 키는 '__'로 구분 (예: APE_SERVER__PORT -> server.port)
                if '__' in config_key:
                    parts = config_key.split('__')
                    self._set_nested_key(self._config, parts, self._parse_env_value(env_value))
                else:
                    self._config[config_key] = self._parse_env_value(env_value)
    
    def _parse_env_value(self, value: str) -> Any:
        """
        환경 변수 값 파싱
        
        Args:
            value: 환경 변수 값
            
        Returns:
            파싱된 값 (str, int, float, bool, dict, list)
        """
        # 정수 변환 시도
        try:
            return int(value)
        except ValueError:
            pass
        
        # 실수 변환 시도
        try:
            return float(value)
        except ValueError:
            pass
        
        # 불리언 변환 시도
        if value.lower() in ('true', 'yes', '1', 'y'):
            return True
        if value.lower() in ('false', 'no', '0', 'n'):
            return False
        
        # JSON 변환 시도
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            pass
        
        # 기본값은 문자열
        return value
    
    def _set_nested_key(self, config: Dict[str, Any], keys: List[str], value: Any) -> None:
        """
        중첩된 키에 값 설정
        
        Args:
            config: 설정 사전
            keys: 키 경로 (예: ['server', 'port'])
            value: 설정할 값
        """
        current = config
        
        # 마지막 키 이전까지 탐색하며 필요한 사전 생성
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            elif not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]
        
        # 마지막 키에 값 설정
        current[keys[-1]] = value
    
    def _deep_update(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """
        사전 깊은 병합
        
        Args:
            target: 대상 사전
            source: 원본 사전 (이 값이 우선)
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value
    
    def _validate_config(self) -> None:
        """설정 유효성 검사"""
        # 필수 설정 확인
        required_fields = [
            ("server", "port"),
            ("security", "permissions"),
            ("llm", "provider"),
            ("llm", "model")
        ]
        
        for field_path in required_fields:
            value = self.get_nested(*field_path)
            if value is None:
                logger.warning(f"필수 설정 누락: {'.'.join(field_path)}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        설정 값 조회
        
        Args:
            key: 설정 키
            default: 기본값 (키가 없을 경우)
            
        Returns:
            설정 값 또는 기본값
        """
        return self._config.get(key, default)
    
    def get_nested(self, *keys: str, default: Any = None) -> Any:
        """
        중첩된 설정 값 조회
        
        Args:
            *keys: 설정 키 경로 (예: 'server', 'port')
            default: 기본값 (키가 없을 경우)
            
        Returns:
            설정 값 또는 기본값
        """
        current = self._config
        
        for key in keys:
            if not isinstance(current, dict) or key not in current:
                return default
            current = current[key]
        
        return current
    
    def set(self, key: str, value: Any) -> None:
        """
        설정 값 설정
        
        Args:
            key: 설정 키
            value: 설정 값
        """
        self._config[key] = value
    
    def set_nested(self, value: Any, *keys: str) -> None:
        """
        중첩된 설정 값 설정
        
        Args:
            value: 설정 값
            *keys: 설정 키 경로 (예: 'server', 'port')
        """
        self._set_nested_key(self._config, list(keys), value)
    
    def get_all(self) -> Dict[str, Any]:
        """
        모든 설정 반환
        
        Returns:
            전체 설정 사전
        """
        return self._config.copy()
    
    def save_config(self, file_path: str) -> bool:
        """
        현재 설정 파일로 저장
        
        Args:
            file_path: 저장할 파일 경로
            
        Returns:
            bool: 저장 성공 여부
        """
        try:
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"설정 저장됨: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"설정 저장 실패: {file_path}, 오류: {str(e)}")
            return False

# 싱글톤 인스턴스
_instance = None

def get_config_manager() -> ConfigManager:
    """
    설정 관리자 인스턴스 반환 (싱글톤)
    
    Returns:
        ConfigManager: 설정 관리자 인스턴스
    """
    global _instance
    
    if _instance is None:
        _instance = ConfigManager()
        # 초기 설정 로드
        _instance.load_config()
    
    return _instance