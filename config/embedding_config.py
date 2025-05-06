"""
임베딩 설정 모듈

임베딩 모델, 벡터 데이터베이스 등의 설정을 관리합니다.
.env 파일에서 환경 변수를 로드합니다.
"""

import os
from typing import Dict, Any
from pathlib import Path

# 환경 변수 로더 모듈 임포트
from src.core.env_loader import get_env, get_boolean_env, get_int_env, get_float_env, get_list_env

# 기본 경로 설정
BASE_DIR = Path(__file__).parent.parent.absolute()
MODELS_DIR = BASE_DIR / "models"
DATA_DIR = BASE_DIR / "data"

# 기본 임베딩 모델 설정
DEFAULT_EMBEDDING_MODEL = {
    "name": get_env("EMBEDDING_MODEL_NAME", "KoSimCSE-roberta"),
    "path": str(MODELS_DIR / get_env("EMBEDDING_MODEL_PATH", "KoSimCSE-roberta-multitask").split("/")[-1]),
    "dimension": get_int_env("EMBEDDING_DIMENSION", 384),  # 벡터 DB에서 사용중인 차원수로 일치시킴
    "max_seq_length": get_int_env("EMBEDDING_MAX_SEQ_LENGTH", 512),
    "device": None  # None은 자동 감지 (GPU 있으면 GPU, 없으면 CPU)
}

# 벡터 데이터베이스 설정
VECTOR_DB_CONFIG = {
    "type": get_env("VECTOR_DB_TYPE", "chroma"),
    "persist_directory": str(DATA_DIR / get_env("VECTOR_DB_PATH", "chroma_db").split("/")[-1]),
    "collection_name": get_env("VECTOR_DB_COLLECTION", "documents"),
    "distance_func": get_env("VECTOR_DB_DISTANCE_FUNC", "cosine"),  # 'cosine', 'l2', 'ip' 중 하나
    "embedding_function": "custom"  # 'custom', 'sentence-transformers', 'openai' 중 하나
}

# 문서 처리 설정
DOCUMENT_PROCESSING = {
    "chunk_size": get_int_env("DOCUMENT_CHUNK_SIZE", 1000),
    "chunk_overlap": get_int_env("DOCUMENT_CHUNK_OVERLAP", 200),
    "file_types": get_list_env("DOCUMENT_FILE_TYPES", default=[".md", ".txt", ".pdf", ".docx", ".html"]),
    "exclude_patterns": get_list_env("DOCUMENT_EXCLUDE_PATTERNS", default=["*.temp.*", ".*", "**/node_modules/**"]),
    "index_metadata": get_boolean_env("DOCUMENT_INDEX_METADATA", True),
    "extract_images": get_boolean_env("DOCUMENT_EXTRACT_IMAGES", False)
}

# 검색 설정
SEARCH_CONFIG = {
    "default_top_k": get_int_env("SEARCH_DEFAULT_TOP_K", 3),
    "min_relevance_score": get_float_env("SEARCH_MIN_RELEVANCE_SCORE", 0.6),
    "rerank_results": get_boolean_env("SEARCH_RERANK_RESULTS", False),
    "use_hybrid_search": get_boolean_env("SEARCH_USE_HYBRID", False)  # 벡터 검색 + 키워드 검색 결합
}

def get_embedding_model_config() -> Dict[str, Any]:
    """
    임베딩 모델 설정 반환
    
    Returns:
        임베딩 모델 설정
    """
    return DEFAULT_EMBEDDING_MODEL

def get_vector_db_config() -> Dict[str, Any]:
    """
    벡터 데이터베이스 설정 반환
    
    Returns:
        벡터 데이터베이스 설정
    """
    return VECTOR_DB_CONFIG

def get_document_processing_config() -> Dict[str, Any]:
    """
    문서 처리 설정 반환
    
    Returns:
        문서 처리 설정
    """
    return DOCUMENT_PROCESSING

def get_search_config() -> Dict[str, Any]:
    """
    검색 설정 반환
    
    Returns:
        검색 설정
    """
    return SEARCH_CONFIG