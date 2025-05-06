"""네트워크 관리 모듈

이 모듈은 내부망과 외부망 설정을 전환하고 관리하는 기능을 제공합니다.
네트워크 전환 시 관련 설정을 모두 업데이트합니다.
"""

import os
import logging
from typing import Dict, Any, List, Optional, Union, Literal

# 네트워크 설정 모듈 임포트
from config.network_config import (
    get_network_mode, set_network_mode, is_internal_network_enabled, 
    is_external_network_enabled, get_network_info
)
from config.models_internal import get_internal_models, get_default_internal_model
from config.models_external import get_external_models, get_default_external_model

# 로거 설정
logger = logging.getLogger("network_manager")

# 네트워크 모드 타입
NetworkMode = Literal["internal", "external"]

class NetworkManager:
    """네트워크 모드 관리 클래스"""
    
    def __init__(self):
        """네트워크 관리자 초기화"""
        self.current_mode = get_network_mode()
        self.available_models = self._get_available_models()
        
    def _get_available_models(self) -> Dict[str, Dict[str, Any]]:
        """현재 네트워크 모드에 따라 사용 가능한 모델 목록 반환"""
        available_models = {}
        
        # 내부망 모델 추가
        if is_internal_network_enabled():
            available_models.update(get_internal_models())
        
        # 외부망 모델 추가
        if is_external_network_enabled():
            available_models.update(get_external_models())
        
        return available_models
    
    def switch_network_mode(self, mode: NetworkMode) -> bool:
        """네트워크 모드 변경
        
        Args:
            mode (NetworkMode): 변경할 네트워크 모드 ('internal' 또는 'external')
            
        Returns:
            bool: 성공 여부
        """
        if mode not in ("internal", "external"):
            logger.error(f"잘못된 네트워크 모드: {mode}")
            return False
        
        # 이미 같은 모드라면 변경하지 않음
        if self.current_mode == mode:
            logger.info(f"이미 {mode} 네트워크 모드로 실행 중입니다.")
            return True
        
        # 환경 변수 설정
        os.environ["NETWORK_MODE"] = mode
        
        # 네트워크 모드 설정
        set_network_mode(mode)
        self.current_mode = mode
        
        # 사용 가능한 모델 업데이트
        self.available_models = self._get_available_models()
        
        logger.info(f"네트워크 모드 변경 완료: {mode}")
        return True
    
    def get_default_model_key(self) -> str:
        """현재 네트워크 모드에 따른 기본 모델 키 반환"""
        if self.current_mode == "internal":
            return get_default_internal_model()
        else:
            return get_default_external_model()
    
    def get_available_model_keys(self) -> List[str]:
        """사용 가능한 모델 키 목록 반환"""
        return list(self.available_models.keys())
    
    def get_model_config(self, model_key: str) -> Optional[Dict[str, Any]]:
        """모델 구성 반환
        
        Args:
            model_key (str): 모델 키
            
        Returns:
            Optional[Dict[str, Any]]: 모델 구성 또는 None (모델 없음)
        """
        return self.available_models.get(model_key)
    
    def get_status(self) -> Dict[str, Any]:
        """네트워크 상태 정보 반환"""
        return {
            "mode": self.current_mode,
            "available_models": len(self.available_models),
            "model_keys": self.get_available_model_keys(),
            "default_model": self.get_default_model_key(),
            "network_info": get_network_info()
        }

# 싱글톤 인스턴스
network_manager = NetworkManager()