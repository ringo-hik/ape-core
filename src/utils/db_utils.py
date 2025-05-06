"""
데이터베이스 유틸리티 모듈

ChromaDB 벡터 데이터베이스 연결 및 관리 기능을 제공합니다.
"""

import os
import logging
import json
import shutil
import numpy as np
from typing import Optional, List, Dict, Any, Union, Tuple

try:
    import chromadb
    from chromadb.config import Settings
    from chromadb.utils import embedding_functions
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logging.warning("ChromaDB 패키지를 설치해야 합니다: pip install chromadb")

# 로깅 설정
logger = logging.getLogger("db_utils")

class VectorDatabase:
    """벡터 데이터베이스 클래스"""
    
    def __init__(self, 
                 persist_directory: str, 
                 collection_name: str = "documents",
                 embedding_function = None):
        """
        벡터 데이터베이스 초기화
        
        Args:
            persist_directory: 데이터 저장 디렉토리
            collection_name: 컬렉션 이름
            embedding_function: 임베딩 함수 (None인 경우 기본 함수 사용)
        """
        if not CHROMADB_AVAILABLE:
            raise ImportError("ChromaDB 패키지가 설치되지 않았습니다")
        
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        
        # 디렉토리 생성
        os.makedirs(persist_directory, exist_ok=True)
        
        # 임베딩 함수 설정
        self.embedding_function = embedding_function
        
        # ChromaDB 클라이언트 초기화
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # 컬렉션 초기화
        self._initialize_collection()
        
        logger.info(f"벡터 데이터베이스 초기화 완료: {persist_directory} (컬렉션: {collection_name})")
    
    def _initialize_collection(self):
        """컬렉션 초기화"""
        try:
            # 기존 컬렉션 가져오기 시도
            self.collection = self.client.get_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function
            )
            count = self.collection.count()
            logger.info(f"기존 컬렉션 로드: {self.collection_name} (문서 수: {count})")
            
        except ValueError:
            # 컬렉션이 없는 경우 새로 생성
            self.collection = self.client.create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function,
                metadata={"description": "문서 검색용 벡터 데이터베이스"}
            )
            logger.info(f"새 컬렉션 생성: {self.collection_name}")
    
    def add_documents(self, 
                    documents: List[Dict[str, Any]], 
                    embeddings: Optional[List[List[float]]] = None) -> List[str]:
        """
        문서 추가
        
        Args:
            documents: 문서 목록 (각 문서는 id, content, metadata를 포함해야 함)
            embeddings: 사전 계산된 임베딩 목록 (None인 경우 자동 생성)
            
        Returns:
            추가된 문서 ID 목록
        """
        if not documents:
            return []
        
        try:
            # 문서 데이터 추출
            ids = [str(doc.get("id", f"doc{i+1}")) for i, doc in enumerate(documents)]
            contents = [doc.get("content", "") for doc in documents]
            metadatas = [doc.get("metadata", {}) for doc in documents]
            
            # 문서 추가
            self.collection.add(
                ids=ids,
                documents=contents,
                metadatas=metadatas,
                embeddings=embeddings
            )
            
            logger.info(f"{len(documents)}개 문서 추가 완료")
            return ids
            
        except Exception as e:
            logger.error(f"문서 추가 오류: {e}")
            return []
    
    def update_document(self, 
                       doc_id: str, 
                       content: str, 
                       metadata: Dict[str, Any],
                       embedding: Optional[List[float]] = None) -> bool:
        """
        문서 업데이트
        
        Args:
            doc_id: 문서 ID
            content: 문서 내용
            metadata: 문서 메타데이터
            embedding: 사전 계산된 임베딩 (None인 경우 자동 생성)
            
        Returns:
            성공 여부
        """
        try:
            # 문서 업데이트
            self.collection.update(
                ids=[doc_id],
                documents=[content],
                metadatas=[metadata],
                embeddings=[embedding] if embedding is not None else None
            )
            
            logger.info(f"문서 업데이트 완료: {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"문서 업데이트 오류 ({doc_id}): {e}")
            return False
    
    def delete_document(self, doc_id: str) -> bool:
        """
        문서 삭제
        
        Args:
            doc_id: 문서 ID
            
        Returns:
            성공 여부
        """
        try:
            # 문서 삭제
            self.collection.delete(ids=[doc_id])
            
            logger.info(f"문서 삭제 완료: {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"문서 삭제 오류 ({doc_id}): {e}")
            return False
    
    def query(self, 
             query_text: str, 
             filter_dict: Optional[Dict[str, Any]] = None,
             n_results: int = 3,
             embedding: Optional[List[float]] = None) -> List[Dict[str, Any]]:
        """
        문서 검색
        
        Args:
            query_text: 검색 텍스트
            filter_dict: 필터링 조건
            n_results: 반환할 결과 수
            embedding: 사전 계산된 임베딩 (None인 경우 자동 생성)
            
        Returns:
            검색 결과 목록
        """
        if self.collection.count() == 0:
            logger.warning("벡터 데이터베이스가 비어 있습니다")
            return []
        
        try:
            # 검색 수행
            results = self.collection.query(
                query_texts=[query_text] if embedding is None else None,
                query_embeddings=[embedding] if embedding is not None else None,
                n_results=min(n_results, self.collection.count()),
                where=filter_dict
            )
            
            # 결과 포맷팅
            formatted_results = []
            for i in range(len(results["ids"][0])):
                doc_id = results["ids"][0][i]
                content = results["documents"][0][i]
                metadata = results["metadatas"][0][i]
                distance = results["distances"][0][i] if "distances" in results else 0.0
                
                # 유사도 점수 계산 (거리를 유사도로 변환)
                similarity = 1.0 / (1.0 + distance)
                
                formatted_results.append({
                    "id": doc_id,
                    "content": content,
                    "metadata": {**metadata, "relevance": similarity}
                })
            
            logger.info(f"쿼리 실행 완료: {query_text[:30]}... (결과 수: {len(formatted_results)})")
            return formatted_results
            
        except Exception as e:
            logger.error(f"쿼리 실행 오류: {e}")
            return []
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        문서 조회
        
        Args:
            doc_id: 문서 ID
            
        Returns:
            문서 정보 또는 None
        """
        try:
            # 문서 조회
            result = self.collection.get(ids=[doc_id])
            
            if not result["ids"]:
                return None
            
            return {
                "id": result["ids"][0],
                "content": result["documents"][0],
                "metadata": result["metadatas"][0]
            }
            
        except Exception as e:
            logger.error(f"문서 조회 오류 ({doc_id}): {e}")
            return None
    
    def count(self) -> int:
        """
        문서 수 반환
        
        Returns:
            문서 수
        """
        try:
            return self.collection.count()
        except Exception as e:
            logger.error(f"문서 수 조회 오류: {e}")
            return 0
    
    def reset(self) -> bool:
        """
        컬렉션 초기화 (모든 문서 삭제)
        
        Returns:
            성공 여부
        """
        try:
            self.client.delete_collection(self.collection_name)
            self._initialize_collection()
            
            logger.info(f"컬렉션 초기화 완료: {self.collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"컬렉션 초기화 오류: {e}")
            return False
    
    def get_collection_info(self) -> Dict[str, Any]:
        """
        컬렉션 정보 반환
        
        Returns:
            컬렉션 정보
        """
        return {
            "name": self.collection_name,
            "count": self.count(),
            "persist_directory": self.persist_directory
        }

# 전역 데이터베이스 인스턴스
_db_instance = None

def get_vector_db(persist_directory: str = None, 
                 collection_name: str = "documents",
                 embedding_function = None) -> VectorDatabase:
    """
    벡터 데이터베이스 인스턴스 반환 (싱글톤)
    
    Args:
        persist_directory: 데이터 저장 디렉토리 (None인 경우 기본 경로 사용)
        collection_name: 컬렉션 이름
        embedding_function: 임베딩 함수 (None인 경우 기본 함수 사용)
        
    Returns:
        VectorDatabase: 벡터 데이터베이스 인스턴스
    """
    global _db_instance
    
    # 기본 저장 경로 설정
    if persist_directory is None:
        # 현재 디렉토리 기준으로 저장 경로 결정
        current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        persist_directory = os.path.join(current_dir, "data", "chroma_db")
    
    # 데이터베이스가 초기화되지 않았거나 다른 설정을 요청한 경우
    if (_db_instance is None or 
        _db_instance.persist_directory != persist_directory or 
        _db_instance.collection_name != collection_name):
        try:
            _db_instance = VectorDatabase(
                persist_directory=persist_directory,
                collection_name=collection_name,
                embedding_function=embedding_function
            )
        except Exception as e:
            logger.error(f"벡터 데이터베이스 인스턴스 생성 실패: {e}")
            raise
    
    return _db_instance

def create_embedding_function(model_name: str = None) -> Any:
    """
    ChromaDB용 임베딩 함수 생성
    
    Args:
        model_name: 모델 이름 (None인 경우 기본 모델 사용)
        
    Returns:
        임베딩 함수
    """
    try:
        if model_name == "custom":
            # 커스텀 임베딩 함수 (직접 구현한 임베딩 모델 사용)
            from src.utils.embedding_utils import get_embedding_model
            
            model = get_embedding_model()
            
            def custom_embedding_function(texts):
                if isinstance(texts, str):
                    texts = [texts]
                return model.get_batch_embeddings(texts)
            
            return custom_embedding_function
        else:
            # 기본 모델 사용 (sentence-transformers)
            return embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=model_name or "all-MiniLM-L6-v2"
            )
    
    except Exception as e:
        logger.error(f"임베딩 함수 생성 오류: {e}")
        # 기본 임베딩 함수 반환
        return None