"""
임베딩 유틸리티 모듈

임베딩 모델 로드, 텍스트 임베딩 생성 등의 공통 기능을 제공합니다.
"""

import os
import logging
import torch
import numpy as np
from typing import Optional, List, Dict, Any, Union
from transformers import AutoModel, AutoTokenizer

# 로깅 설정
logger = logging.getLogger("embedding_utils")

class EmbeddingModel:
    """임베딩 모델 클래스"""
    
    def __init__(self, model_path: str, device: str = None):
        """
        임베딩 모델 초기화
        
        Args:
            model_path: 모델 파일 경로
            device: 사용할 장치 ('cpu' 또는 'cuda', None인 경우 자동 선택)
        """
        self.model_path = model_path
        
        # 장치 설정
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
        
        # 모델 속성
        self.model = None
        self.tokenizer = None
        self.dimension = 0
        
        # 모델 로드
        self._load_model()
        
        logger.info(f"임베딩 모델 초기화 완료: {model_path} (장치: {self.device})")
    
    def _load_model(self):
        """임베딩 모델 로드"""
        logger.info(f"임베딩 모델 로드 중: {self.model_path}")
        
        try:
            # 토크나이저 및 모델 로드
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            self.model = AutoModel.from_pretrained(self.model_path)
            
            # 장치로 모델 이동
            self.model = self.model.to(self.device)
            
            # 모델을 평가 모드로 설정
            self.model.eval()
            
            # 임베딩 차원 확인
            with torch.no_grad():
                # 임시 입력을 사용하여 출력 차원 확인
                dummy_input = self.tokenizer("테스트 문장", return_tensors="pt")
                dummy_input = {k: v.to(self.device) for k, v in dummy_input.items()}
                outputs = self.model(**dummy_input)
                self.dimension = outputs.last_hidden_state.size(-1)
            
            logger.info(f"임베딩 모델 로드 완료 (차원: {self.dimension})")
            
        except Exception as e:
            logger.error(f"임베딩 모델 로드 오류: {e}")
            raise RuntimeError(f"임베딩 모델 로드 실패: {str(e)}")
    
    def get_embedding(self, text: str, max_length: int = 512) -> np.ndarray:
        """
        텍스트 임베딩 생성
        
        Args:
            text: 임베딩할 텍스트
            max_length: 최대 토큰 길이
            
        Returns:
            임베딩 벡터
        """
        if not text.strip():
            # 빈 텍스트인 경우 0 벡터 반환
            return np.zeros(self.dimension)
        
        try:
            # 토큰화
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=max_length,
                padding="max_length"
            )
            
            # 장치로 입력 텐서 이동
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # 임베딩 생성
            with torch.no_grad():
                outputs = self.model(**inputs)
                # 문장 임베딩 (CLS 토큰)
                embedding = outputs.last_hidden_state[:, 0, :].cpu().numpy()[0]
            
            return embedding
            
        except Exception as e:
            logger.error(f"임베딩 생성 오류: {e}")
            return np.zeros(self.dimension)
    
    def get_batch_embeddings(self, texts: List[str], max_length: int = 512) -> List[np.ndarray]:
        """
        배치 텍스트 임베딩 생성
        
        Args:
            texts: 임베딩할 텍스트 목록
            max_length: 최대 토큰 길이
            
        Returns:
            임베딩 벡터 목록
        """
        if not texts:
            return []
        
        embeddings = []
        try:
            # 일괄 토큰화
            inputs = self.tokenizer(
                texts,
                return_tensors="pt",
                truncation=True,
                max_length=max_length,
                padding="max_length"
            )
            
            # 장치로 입력 텐서 이동
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # 임베딩 생성
            with torch.no_grad():
                outputs = self.model(**inputs)
                # 문장 임베딩 (CLS 토큰)
                batch_embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy()
            
            return batch_embeddings
            
        except Exception as e:
            logger.error(f"배치 임베딩 생성 오류: {e}")
            # 오류 발생 시 개별 처리
            for text in texts:
                embeddings.append(self.get_embedding(text, max_length))
            return embeddings
    
    @property
    def embedding_dimension(self) -> int:
        """임베딩 차원 반환"""
        return self.dimension

# 전역 임베딩 모델 인스턴스
_model_instance = None

def get_embedding_model(model_path: str = None) -> EmbeddingModel:
    """
    임베딩 모델 인스턴스 반환 (싱글톤)
    
    Args:
        model_path: 모델 파일 경로 (None인 경우 기본 모델 사용)
        
    Returns:
        EmbeddingModel: 임베딩 모델 인스턴스
    """
    global _model_instance
    
    # 기본 모델 경로 설정
    if model_path is None:
        # 현재 디렉토리 기준으로 모델 경로 결정
        current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        model_path = os.path.join(current_dir, "models", "KoSimCSE-roberta-multitask")
    
    # 모델이 초기화되지 않았거나 다른 모델을 요청한 경우
    if _model_instance is None or _model_instance.model_path != model_path:
        try:
            _model_instance = EmbeddingModel(model_path)
        except Exception as e:
            logger.error(f"임베딩 모델 인스턴스 생성 실패: {e}")
            raise
    
    return _model_instance