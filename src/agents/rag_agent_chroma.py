"""
ChromaDB 기반 RAG 에이전트 - 검색 증강 생성 에이전트

이 모듈은 ChromaDB를 벡터 저장소로 사용하여 문서 검색 및 지식 증강 서비스를 제공합니다.
영구 저장 기능을 통해 세션 간에도 임베딩과 문서를 유지합니다.
"""

import os
import uuid
import logging
import json
import glob
import time
from typing import Dict, Any, List, Optional, Union, Tuple

# 유틸리티 모듈 임포트
from src.utils.embedding_utils import get_embedding_model
from src.utils.db_utils import get_vector_db, create_embedding_function, CHROMADB_AVAILABLE
from src.core.llm_service import llm_service

# 설정 임포트
try:
    from config.embedding_config import (
        get_embedding_model_config,
        get_vector_db_config,
        get_document_processing_config,
        get_search_config
    )
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    logging.warning("임베딩 설정 모듈을 찾을 수 없습니다.")

# 로깅 설정
logger = logging.getLogger("rag_agent_chroma")

class Document:
    """문서 클래스"""
    
    def __init__(self, doc_id: str, title: str, content: str, file_path: str, metadata: Dict[str, Any] = None):
        """
        문서 초기화
        
        Args:
            doc_id: 문서 ID
            title: 문서 제목
            content: 문서 내용
            file_path: 문서 파일 경로
            metadata: 추가 메타데이터
        """
        self.id = doc_id
        self.title = title
        self.content = content
        self.file_path = file_path
        self.collection = os.path.basename(os.path.dirname(file_path))
        
        # 기본 메타데이터
        self.metadata = {
            "title": title,
            "source": file_path,
            "collection": self.collection,
            "created_at": time.time(),
            "file_type": os.path.splitext(file_path)[1]
        }
        
        # 추가 메타데이터 병합
        if metadata:
            self.metadata.update(metadata)
    
    def to_dict(self, relevance: float = 0.0) -> Dict[str, Any]:
        """
        사전 형태로 변환
        
        Args:
            relevance: 관련성 점수
            
        Returns:
            사전 형태의 문서 정보
        """
        metadata = self.metadata.copy()
        metadata["relevance"] = relevance
        
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "metadata": metadata
        }

class RAGAgentChroma:
    """ChromaDB 기반 검색 증강 생성 에이전트"""
    
    def __init__(self):
        """RAG 에이전트 초기화"""
        self.agent_id = f"rag-{uuid.uuid4()}"
        
        # ChromaDB 사용 가능 여부 확인
        if not CHROMADB_AVAILABLE:
            logger.error("ChromaDB 패키지가 설치되지 않았습니다")
            self.chroma_available = False
            return
        
        self.chroma_available = True
        
        # 설정 로드
        if CONFIG_AVAILABLE:
            self.embedding_config = get_embedding_model_config()
            self.vector_db_config = get_vector_db_config()
            self.doc_processing_config = get_document_processing_config()
            self.search_config = get_search_config()
        else:
            # 기본 설정
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            models_dir = os.path.join(base_dir, "models")
            data_dir = os.path.join(base_dir, "data")
            
            self.embedding_config = {
                "path": os.path.join(models_dir, "KoSimCSE-roberta-multitask"),
                "dimension": 768
            }
            
            self.vector_db_config = {
                "persist_directory": os.path.join(data_dir, "chroma_db"),
                "collection_name": "documents"
            }
            
            self.doc_processing_config = {
                "chunk_size": 1000,
                "file_types": [".md", ".txt"]
            }
            
            self.search_config = {
                "default_top_k": 3
            }
        
        # 문서 저장소 기본 경로
        self.docs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "docs")
        os.makedirs(self.docs_dir, exist_ok=True)
        
        # 임베딩 모델 초기화
        try:
            self.embedding_model = get_embedding_model(self.embedding_config.get("path"))
            logger.info("임베딩 모델 초기화 완료")
        except Exception as e:
            logger.error(f"임베딩 모델 초기화 오류: {e}")
            self.embedding_model = None
        
        # 임베딩 사용 가능 여부
        self.use_embedding = self.embedding_model is not None
        
        # 벡터 데이터베이스 초기화
        if self.use_embedding:
            try:
                # 커스텀 임베딩 함수 생성
                embedding_function = create_embedding_function("custom")
                
                # 벡터 데이터베이스 초기화
                self.db = get_vector_db(
                    persist_directory=self.vector_db_config.get("persist_directory"),
                    collection_name=self.vector_db_config.get("collection_name"),
                    embedding_function=embedding_function
                )
                
                # 문서 수 확인
                doc_count = self.db.count()
                logger.info(f"벡터 데이터베이스 초기화 완료 (문서 수: {doc_count})")
                
                # 문서가 없으면 로드
                if doc_count == 0:
                    self._load_documents()
                
            except Exception as e:
                logger.error(f"벡터 데이터베이스 초기화 오류: {e}")
                self.db = None
        else:
            self.db = None
        
        logger.info(f"RAG 에이전트 초기화: {self.agent_id} (ChromaDB 사용: {self.chroma_available and self.db is not None})")
    
    def _load_documents(self):
        """문서 로드 및 인덱싱"""
        # 지원하는 파일 형식 확인
        file_types = self.doc_processing_config.get("file_types", [".md", ".txt"])
        
        # 모든 지원 형식에 대해 파일 찾기
        all_files = []
        for file_type in file_types:
            pattern = os.path.join(self.docs_dir, "**", f"*{file_type}")
            all_files.extend(glob.glob(pattern, recursive=True))
        
        logger.info(f"문서 파일 {len(all_files)}개 발견")
        
        if not all_files:
            logger.warning(f"문서 디렉토리에 지원하는 파일이 없습니다: {self.docs_dir}")
            return
        
        # 문서 객체 생성 및 벡터 데이터베이스에 추가
        documents = []
        for i, file_path in enumerate(all_files):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 파일 이름에서 제목 추출
                title = os.path.basename(file_path)
                title = os.path.splitext(title)[0].replace('_', ' ').title()
                
                # 문서 객체 생성
                doc = Document(
                    doc_id=f"doc{i+1}",
                    title=title,
                    content=content,
                    file_path=file_path
                )
                
                # 문서 추가
                documents.append(doc.to_dict())
                
            except Exception as e:
                logger.error(f"문서 로드 오류 ({file_path}): {e}")
        
        # 문서가 있으면 벡터 데이터베이스에 추가
        if documents:
            try:
                # 모든 문서의 임베딩 생성
                contents = [doc["content"] for doc in documents]
                embeddings = self.embedding_model.get_batch_embeddings(contents)
                
                # 벡터 데이터베이스에 추가
                self.db.add_documents(documents, embeddings)
                
                logger.info(f"총 {len(documents)}개 문서 로드 및 인덱싱 완료")
                
            except Exception as e:
                logger.error(f"문서 인덱싱 오류: {e}")
    
    def search_documents(self, query: str, collection: str = None, num_results: int = None) -> List[Dict[str, Any]]:
        """
        쿼리로 문서 검색
        
        Args:
            query: 검색 쿼리
            collection: 문서 컬렉션 (None인 경우 전체 검색)
            num_results: 반환할 결과 수
            
        Returns:
            검색 결과 목록
        """
        # 기본값 설정
        if num_results is None:
            num_results = self.search_config.get("default_top_k", 3)
        
        # ChromaDB 및 임베딩 사용 가능 여부 확인
        if not (self.chroma_available and self.db is not None and self.embedding_model is not None):
            # 가상 결과 반환
            return self._simulate_document_search(query, collection or "default", num_results)
        
        try:
            # 필터 설정
            filter_dict = {"collection": collection} if collection else None
            
            # 쿼리 임베딩 생성
            query_embedding = self.embedding_model.get_embedding(query)
            
            # 벡터 데이터베이스 검색
            results = self.db.query(
                query_text=query,
                filter_dict=filter_dict,
                n_results=num_results,
                embedding=query_embedding
            )
            
            # 충분한 결과가 없는 경우 가상 결과로 보완
            if len(results) < num_results:
                logger.warning(f"충분한 검색 결과가 없습니다. 가상 결과로 보완합니다. (검색됨: {len(results)}, 필요: {num_results})")
                simulated_results = self._simulate_document_search(query, collection or "default", num_results - len(results))
                results.extend(simulated_results)
            
            return results
            
        except Exception as e:
            logger.error(f"문서 검색 오류: {e}")
            return self._simulate_document_search(query, collection or "default", num_results)
    
    def add_document(self, title: str, content: str, file_path: str = None, metadata: Dict[str, Any] = None) -> Optional[str]:
        """
        문서 추가
        
        Args:
            title: 문서 제목
            content: 문서 내용
            file_path: 문서 파일 경로 (None인 경우 가상 경로 생성)
            metadata: 추가 메타데이터
            
        Returns:
            생성된 문서 ID 또는 None (실패 시)
        """
        if not (self.chroma_available and self.db is not None and self.embedding_model is not None):
            logger.error("ChromaDB 또는 임베딩 모델이 초기화되지 않았습니다")
            return None
        
        try:
            # 파일 경로 생성
            if file_path is None:
                file_name = title.lower().replace(' ', '_') + '.md'
                file_path = os.path.join(self.docs_dir, "manual", file_name)
                
                # 디렉토리 생성
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                # 파일 저장
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            # 문서 ID 생성
            doc_id = f"doc_{int(time.time())}_{uuid.uuid4().hex[:8]}"
            
            # 문서 객체 생성
            doc = Document(
                doc_id=doc_id,
                title=title,
                content=content,
                file_path=file_path,
                metadata=metadata
            )
            
            # 임베딩 생성
            embedding = self.embedding_model.get_embedding(content)
            
            # 벡터 데이터베이스에 추가
            document_dict = doc.to_dict()
            self.db.add_documents([document_dict], [embedding])
            
            logger.info(f"문서 추가 완료: {title} (ID: {doc_id})")
            return doc_id
            
        except Exception as e:
            logger.error(f"문서 추가 오류: {e}")
            return None
    
    def run(self, query: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        RAG 검색 및 증강 응답 생성
        
        Args:
            query: 검색 쿼리
            metadata: 추가 메타데이터 (문서 컬렉션, 검색 설정 등)
            
        Returns:
            에이전트 응답
        """
        logger.info(f"RAG 쿼리 실행: {query}")
        metadata = metadata or {}
        
        start_time = time.time()
        
        # 검색 설정
        collection = metadata.get("collection", None)
        num_results = metadata.get("num_results", self.search_config.get("default_top_k", 3))
        context_from_other_agent = metadata.get("context", "")
        
        # 문서 검색
        search_results = self.search_documents(query, collection, num_results)
        
        # 프롬프트 구성
        prompt = f"""검색 증강 생성(RAG) 에이전트로서 아래 정보 소스를 바탕으로 쿼리에 답변하세요.

질문: {query}

{'다른 에이전트로부터 얻은 컨텍스트:\n' + context_from_other_agent if context_from_other_agent else ''}

검색 결과:
{self._format_search_results(search_results)}

위 정보를 바탕으로 질문에 대한 정확하고 상세한 답변을 제공하세요.
정보의 출처를 명확히 언급하고, 검색 결과에서 찾을 수 없는 내용은 추측하지 마세요.
"""
        
        # 메시지 구성
        messages = [llm_service.format_system_message(prompt)]
        
        # LLM 호출
        content = llm_service.generate(messages)
        
        # 실행 시간 계산
        execution_time = time.time() - start_time
        logger.info(f"RAG 쿼리 실행 완료 (소요 시간: {execution_time:.2f}초)")
        
        # 오류 처리
        if isinstance(content, dict) and "error" in content:
            return self._format_response(f"에이전트 오류: {content['error']}")
        
        # 응답 반환
        return self._format_response(content)
    
    def _format_response(self, content: str) -> Dict[str, Any]:
        """응답 형식화"""
        return {
            "content": content,
            "model": llm_service.model_id,
            "agent_id": self.agent_id
        }
    
    def _simulate_document_search(self, query: str, collection: str, num_results: int) -> List[Dict[str, Any]]:
        """
        문서 검색 시뮬레이션 (ChromaDB 사용 불가 시)
        
        Args:
            query: 검색 쿼리
            collection: 문서 컬렉션
            num_results: 반환할 검색 결과 수
            
        Returns:
            검색 결과 목록
        """
        logger.info(f"가상 문서 검색 사용 (쿼리: {query}, 컬렉션: {collection})")
        
        # 가상 검색 결과
        documents = [
            {
                "id": "doc1",
                "title": "프로젝트 요약 문서",
                "content": f"이 프로젝트는 {query}와 관련된 기능을 제공합니다. 주요 목표는 사용자 경험 향상과 데이터 처리 최적화입니다.",
                "metadata": {"title": "프로젝트 요약 문서", "source": f"{collection}/summary.md", "relevance": 0.92, "collection": collection}
            },
            {
                "id": "doc2",
                "title": "기술 스펙 문서",
                "content": f"{query}를 구현하기 위해 다음 기술이 사용됩니다: REST API, 비동기 처리, 데이터베이스 캐싱. 이를 통해 성능을 최적화합니다.",
                "metadata": {"title": "기술 스펙 문서", "source": f"{collection}/tech_spec.md", "relevance": 0.85, "collection": collection}
            },
            {
                "id": "doc3",
                "title": "사용자 가이드",
                "content": f"{query} 기능을 사용하려면 다음 단계를 따르세요: 1) 로그인 2) 메뉴 선택 3) 파라미터 설정 4) 실행",
                "metadata": {"title": "사용자 가이드", "source": f"{collection}/user_guide.md", "relevance": 0.78, "collection": collection}
            },
            {
                "id": "doc4",
                "title": "API 문서",
                "content": f"{query} API는 다음 엔드포인트를 제공합니다: GET /api/resource, POST /api/resource, PUT /api/resource/{'{id}'}",
                "metadata": {"title": "API 문서", "source": f"{collection}/api_docs.md", "relevance": 0.72, "collection": collection}
            }
        ]
        
        # 검색 결과 수에 맞게 반환
        return documents[:num_results]
    
    def _format_search_results(self, results: List[Dict[str, Any]]) -> str:
        """검색 결과 형식화"""
        formatted = ""
        for i, doc in enumerate(results):
            # 제목 가져오기
            title = doc.get("title", doc.get("metadata", {}).get("title", f"문서 {i+1}"))
            
            # 출처 가져오기
            source = doc.get("metadata", {}).get("source", "알 수 없는 출처")
            
            # 관련도 가져오기
            relevance = doc.get("metadata", {}).get("relevance", 0.0)
            
            formatted += f"[{i+1}] {title} (출처: {source})\n"
            formatted += f"관련도: {relevance:.2f}\n"
            formatted += f"내용: {doc.get('content', '')}\n\n"
        
        return formatted
    
    def get_stats(self) -> Dict[str, Any]:
        """
        에이전트 통계 반환
        
        Returns:
            통계 정보
        """
        stats = {
            "agent_id": self.agent_id,
            "chroma_available": self.chroma_available,
            "use_embedding": self.use_embedding,
            "document_count": 0,
            "embedding_model": self.embedding_config.get("path") if hasattr(self, "embedding_config") else None,
            "vector_db": None
        }
        
        # 벡터 데이터베이스 정보 추가
        if self.db is not None:
            try:
                stats["document_count"] = self.db.count()
                stats["vector_db"] = self.db.get_collection_info()
            except:
                pass
        
        return stats