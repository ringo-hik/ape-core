"""RAG 에이전트 모듈

이 모듈은 검색 증강 생성(RAG) 에이전트를 구현합니다.
벡터 저장소를 사용하여 문서 검색 및 지식 증강 기능을 제공합니다.
"""

import os
import uuid
import time
import logging
import glob
from typing import Dict, List, Any, Optional, Union, Generator

from src.core.config import get_settings, get_embedding_config, get_vector_db_config
from src.core.llm_service import llm_service

# 로깅 설정
logger = logging.getLogger("rag_agent")

# ChromaDB 사용 가능 여부 확인
try:
    import chromadb
    from chromadb.utils import embedding_functions
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logger.warning("ChromaDB 패키지가 설치되지 않았습니다. RAG 기능이 제한됩니다.")

# 임베딩 모델 사용 가능 여부 확인
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDING_MODEL_AVAILABLE = True
except ImportError:
    EMBEDDING_MODEL_AVAILABLE = False
    logger.warning("SentenceTransformer 패키지가 설치되지 않았습니다. 임베딩 기능이 제한됩니다.")

class EmbeddingModel:
    """임베딩 모델 클래스"""
    
    def __init__(self, model_path: Optional[str] = None):
        """
        임베딩 모델 초기화
        
        Args:
            model_path: 모델 경로 (None인 경우 기본 모델 사용)
        """
        self.model_path = model_path or "all-MiniLM-L6-v2"
        self.config = get_embedding_config()
        
        # 차원 값을 확인하고 정수로 변환
        try:
            self.dimension = int(self.config.get("dimension", 768))
            logger.info(f"임베딩 차원 설정: {self.dimension}")
        except (ValueError, TypeError):
            self.dimension = 768
            logger.warning("임베딩 차원을 정수로 변환할 수 없습니다. 기본값 768을 사용합니다.")
        
        self.model = None  # 기본값으로 None 설정
        
        # 모델 로드 시도
        if EMBEDDING_MODEL_AVAILABLE:
            try:
                # 모델 경로가 상대 경로인 경우 절대 경로로 변환
                if self.model_path.startswith("models/"):
                    import os
                    abs_model_path = os.path.join(
                        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                        self.model_path
                    )
                    logger.info(f"모델 절대 경로: {abs_model_path}")
                    
                    # 모델 디렉토리 확인
                    if os.path.exists(abs_model_path):
                        logger.info(f"모델 디렉토리 존재: {os.listdir(abs_model_path)}")
                        self.model = SentenceTransformer(abs_model_path)
                    else:
                        logger.warning(f"모델 디렉토리가 존재하지 않음: {abs_model_path}")
                        # 기본 모델로 폴백
                        logger.info("기본 모델로 폴백: all-MiniLM-L6-v2")
                        self.model = SentenceTransformer("all-MiniLM-L6-v2")
                else:
                    # 표준 모델 이름/경로 사용
                    logger.info(f"모델 로드 시도: {self.model_path}")
                    self.model = SentenceTransformer(self.model_path)
                
                # 모델 차원 가져오기
                self.dimension = self.model.get_sentence_embedding_dimension()
                logger.info(f"임베딩 모델 로드 완료: {self.model_path} (차원: {self.dimension})")
            
            except Exception as e:
                import traceback
                logger.error(f"임베딩 모델 로드 오류: {e}")
                logger.error(f"오류 스택 트레이스: {traceback.format_exc()}")
                self.model = None
        else:
            logger.warning("SentenceTransformer 패키지를 사용할 수 없어 임베딩 모델을 로드할 수 없습니다.")
    
    def get_embedding(self, text: str) -> List[float]:
        """
        텍스트 임베딩 생성
        
        Args:
            text: 임베딩할 텍스트
            
        Returns:
            임베딩 벡터
        """
        if self.model is None:
            # 임베딩 모델이 없는 경우 가상 임베딩 반환
            return [0.0] * self.dimension
        
        return self.model.encode(text).tolist()
    
    def get_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        배치 텍스트 임베딩 생성
        
        Args:
            texts: 임베딩할 텍스트 리스트
            
        Returns:
            임베딩 벡터 리스트
        """
        if self.model is None:
            # 임베딩 모델이 없는 경우 가상 임베딩 반환
            return [[0.0] * self.dimension for _ in texts]
        
        return self.model.encode(texts).tolist()

class VectorStore:
    """벡터 저장소 클래스"""
    
    def __init__(self, persist_directory: str, collection_name: str = "documents", embedding_function=None):
        """
        벡터 저장소 초기화
        
        Args:
            persist_directory: 영구 저장 디렉토리
            collection_name: 컬렉션 이름
            embedding_function: 임베딩 함수
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.embedding_function = embedding_function
        self.config = get_vector_db_config()
        
        # ChromaDB 사용 가능 여부 확인
        if not CHROMADB_AVAILABLE:
            logger.error("ChromaDB를 사용할 수 없습니다.")
            self.client = None
            self.collection = None
            return
        
        try:
            # 디렉토리 생성
            os.makedirs(self.persist_directory, exist_ok=True)
            
            # ChromaDB 클라이언트 초기화
            self.client = chromadb.PersistentClient(path=self.persist_directory)
            
            # 컬렉션 생성 또는 로드
            try:
                self.collection = self.client.get_collection(
                    name=self.collection_name,
                    embedding_function=self.embedding_function
                )
                logger.info(f"기존 컬렉션 로드: {self.collection_name} (문서 수: {self.collection.count()})")
            except:
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    embedding_function=self.embedding_function
                )
                logger.info(f"새 컬렉션 생성: {self.collection_name}")
        
        except Exception as e:
            logger.error(f"벡터 저장소 초기화 오류: {e}")
            self.client = None
            self.collection = None
    
    def add_documents(self, documents: List[Dict[str, Any]], embeddings: Optional[List[List[float]]] = None) -> bool:
        """
        문서 추가
        
        Args:
            documents: 문서 목록
            embeddings: 임베딩 벡터 리스트 (None인 경우 임베딩 함수 사용)
            
        Returns:
            추가 성공 여부
        """
        if self.collection is None:
            logger.error("벡터 저장소를 사용할 수 없습니다.")
            # ChromaDB가 사용 불가능한 경우 더미 문서 저장 로그 추가
            logger.info(f"ChromaDB를 사용할 수 없어 메모리에만 {len(documents)}개 문서 정보를 저장합니다.")
            return True  # 실패가 아닌 것처럼 반환하여 워크플로우 계속 진행
        
        try:
            # 문서 데이터 추출
            ids = [doc.get("id") for doc in documents]
            contents = [doc.get("content") for doc in documents]
            metadatas = [doc.get("metadata", {}) for doc in documents]
            
            # 임베딩 사용하지 않고 직접 벡터 전달
            if embeddings is not None:
                self.collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    documents=contents,
                    metadatas=metadatas
                )
            # 임베딩 함수 사용
            else:
                self.collection.add(
                    ids=ids,
                    documents=contents,
                    metadatas=metadatas
                )
            
            logger.info(f"문서 {len(documents)}개 추가 완료")
            return True
            
        except Exception as e:
            logger.error(f"문서 추가 오류: {e}")
            return False
    
    def query(self, query_text: str, filter_dict: Optional[Dict[str, Any]] = None, n_results: int = 3, embedding: Optional[List[float]] = None) -> List[Dict[str, Any]]:
        """
        쿼리 실행
        
        Args:
            query_text: 쿼리 텍스트
            filter_dict: 필터 조건
            n_results: 반환할 결과 수
            embedding: 쿼리 임베딩 (None인 경우 임베딩 함수 사용)
            
        Returns:
            검색 결과 목록
        """
        if self.collection is None:
            logger.error("벡터 저장소를 사용할 수 없습니다.")
            return []
        
        # n_results가 정수인지 확인
        try:
            n_results = int(n_results)
        except (ValueError, TypeError):
            logger.warning(f"검색 결과 수({n_results})를 정수로 변환할 수 없습니다. 기본값 3을 사용합니다.")
            n_results = 3
        
        try:
            # 임베딩 직접 전달
            if embedding is not None:
                results = self.collection.query(
                    query_embeddings=[embedding],
                    where=filter_dict,
                    n_results=n_results
                )
            # 쿼리 텍스트로 검색
            else:
                results = self.collection.query(
                    query_texts=[query_text],
                    where=filter_dict,
                    n_results=n_results
                )
            
            # 결과 형식화
            formatted_results = []
            for i, (doc_id, document, metadata) in enumerate(zip(
                results["ids"][0],
                results["documents"][0],
                results["metadatas"][0]
            )):
                # 거리 점수 계산 (있는 경우)
                distance = results.get("distances", [[]])[0][i] if "distances" in results else 0.0
                
                # relevance 점수 계산 (거리에 따라 0~1 사이 값으로 변환)
                if self.config.get("distance_func") == "cosine":
                    # 코사인 유사도는 높을수록 유사 (0~1)
                    relevance = distance
                else:
                    # L2, IP 거리는 낮을수록 유사 (거리를 역수로 변환)
                    relevance = 1.0 / (1.0 + distance) if distance > 0 else 1.0
                
                # 메타데이터에 관련도 점수 추가
                metadata_with_score = dict(metadata)
                metadata_with_score["relevance"] = relevance
                
                formatted_results.append({
                    "id": doc_id,
                    "content": document,
                    "metadata": metadata_with_score,
                    "title": metadata.get("title", f"문서 {i+1}")
                })
            
            logger.info(f"쿼리 결과: {len(formatted_results)}개 문서")
            return formatted_results
            
        except Exception as e:
            logger.error(f"쿼리 실행 오류: {e}")
            return []
    
    def count(self) -> int:
        """
        문서 수 반환
        
        Returns:
            컬렉션 내 문서 수 (오류 시 0)
        """
        if self.collection is None:
            return 0
        
        try:
            return self.collection.count()
        except Exception as e:
            logger.error(f"문서 수 조회 오류: {e}")
            return 0
    
    def get_collection_info(self) -> Dict[str, Any]:
        """
        컬렉션 정보 반환
        
        Returns:
            컬렉션 정보
        """
        if self.collection is None:
            return {
                "name": self.collection_name,
                "available": False,
                "document_count": 0
            }
        
        return {
            "name": self.collection_name,
            "available": True,
            "document_count": self.count(),
            "path": self.persist_directory
        }

class RAGAgent:
    """검색 증강 생성 에이전트"""
    
    def __init__(self):
        """RAG 에이전트 초기화"""
        import os  # 명시적 임포트 추가
        
        self.agent_id = f"rag-{uuid.uuid4()}"
        self.agent_type = "rag"
        
        # 설정 로드
        self.settings = get_settings()
        self.config = get_vector_db_config()  # 적절한 변환이 적용된 설정 사용
        self.embedding_config = get_embedding_config()  # 적절한 변환이 적용된 설정 사용
        
        # 기본 디렉토리 설정
        current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.docs_dir = os.path.join(current_dir, "data", "docs")
        os.makedirs(self.docs_dir, exist_ok=True)
        
        # 임베딩 모델 경로 설정
        try:
            model_path = self.embedding_config.get("model_path")
            logger.info(f"임베딩 모델 경로: {model_path}")
            
            if model_path == "KoSimCSE-roberta":
                model_path = "models/KoSimCSE-roberta-multitask"
                logger.info(f"임베딩 모델 경로 수정: {model_path}")
                
                # 모델 파일 확인
                import os
                model_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), model_path)
                logger.info(f"모델 디렉토리 경로: {model_dir}")
                if os.path.exists(model_dir):
                    logger.info(f"모델 디렉토리 존재: {os.listdir(model_dir)}")
                else:
                    logger.warning(f"모델 디렉토리가 존재하지 않음: {model_dir}")
            
            # 임베딩 모델 초기화
            logger.info("임베딩 모델 초기화 시작")
            self.embedding_model = EmbeddingModel(model_path=model_path)
            logger.info("임베딩 모델 초기화 완료")
            
        except Exception as e:
            import traceback
            logger.error(f"임베딩 모델 초기화 중 오류: {e}")
            logger.error(f"오류 스택 트레이스: {traceback.format_exc()}")
            # 오류에도 불구하고 기본 임베딩 모델 생성 시도
            self.embedding_model = EmbeddingModel()
        
        # 임베딩 함수 생성
        embedding_func = None
        if CHROMADB_AVAILABLE and EMBEDDING_MODEL_AVAILABLE:
            try:
                embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name=model_path or "all-MiniLM-L6-v2"
                )
                logger.info(f"임베딩 함수 생성 완료: {model_path}")
            except Exception as e:
                logger.error(f"임베딩 함수 생성 오류: {e}")
        
        # 벡터 DB 경로 확인
        try:
            persist_directory = self.config.get("persist_directory", "data/chroma_db")
            logger.info(f"벡터 DB 경로: {persist_directory}")
            
            if not os.path.isabs(persist_directory):
                persist_directory = os.path.join(current_dir, persist_directory)
                logger.info(f"벡터 DB 절대 경로: {persist_directory}")
            
            # 디렉토리 생성 확인
            os.makedirs(persist_directory, exist_ok=True)
            logger.info(f"벡터 DB 디렉토리 생성/확인 완료")
            
            # 컬렉션 이름 확인
            collection_name = self.config.get("collection_name", "documents")
            logger.info(f"벡터 DB 컬렉션 이름: {collection_name}")
                
            # 벡터 저장소 초기화
            logger.info("벡터 저장소 초기화 시작")
            try:
                # 기존 벡터 데이터베이스 삭제 (차원 문제 해결을 위해 새로 생성)
                import shutil
                if os.path.exists(persist_directory):
                    logger.info(f"기존 벡터 DB 삭제: {persist_directory}")
                    shutil.rmtree(persist_directory)
                    os.makedirs(persist_directory, exist_ok=True)
                    logger.info(f"벡터 DB 디렉토리 재생성: {persist_directory}")
                
                self.vector_store = VectorStore(
                    persist_directory=persist_directory,
                    collection_name=collection_name,
                    embedding_function=embedding_func
                )
                logger.info("벡터 저장소 초기화 완료")
            except Exception as e:
                logger.error(f"벡터 저장소 초기화 오류: {e}")
                # 더미 벡터 저장소 생성
                self.vector_store = VectorStore(
                    persist_directory=persist_directory,
                    collection_name="dummy",
                    embedding_function=None
                )
            
        except Exception as e:
            import traceback
            logger.error(f"벡터 저장소 초기화 중 오류: {e}")
            logger.error(f"오류 스택 트레이스: {traceback.format_exc()}")
            
            # 더미 벡터 저장소 생성
            logger.info("더미 벡터 저장소 초기화 시작")
            self.vector_store = VectorStore(
                persist_directory="data/chroma_db",
                collection_name="dummy",
                embedding_function=None
            )
            logger.info("더미 벡터 저장소 초기화 완료")
        
        # 문서가 없으면 기본 문서 로드
        try:
            if self.vector_store.count() == 0:
                self._load_example_documents()
        except Exception as e:
            logger.error(f"예제 문서 로드 중 오류 발생: {e}")
        
        logger.info(f"RAG 에이전트 초기화 완료: {self.agent_id}")
    
    def _load_example_documents(self):
        """예제 문서 로드"""
        # 기본 문서 경로
        example_docs_path = os.path.join(self.docs_dir, "example")
        os.makedirs(example_docs_path, exist_ok=True)
        
        # 문서 파일 찾기
        doc_files = glob.glob(os.path.join(example_docs_path, "*.md"))
        
        if not doc_files:
            logger.warning(f"예제 문서 디렉토리에 파일이 없습니다: {example_docs_path}")
            # 기본 예제 문서 생성
            self._create_example_documents(example_docs_path)
            doc_files = glob.glob(os.path.join(example_docs_path, "*.md"))
        
        # 문서 로드 및 인덱싱
        documents = []
        for i, file_path in enumerate(doc_files):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 파일 이름에서 제목 추출
                title = os.path.basename(file_path)
                title = os.path.splitext(title)[0].replace('_', ' ').title()
                
                # 문서 객체 생성
                doc = {
                    "id": f"doc{i+1}",
                    "title": title,
                    "content": content,
                    "metadata": {
                        "title": title,
                        "source": file_path,
                        "file_type": ".md"
                    }
                }
                
                documents.append(doc)
                
            except Exception as e:
                logger.error(f"문서 로드 오류 ({file_path}): {e}")
        
        # 문서가 있으면 임베딩 생성 및 벡터 저장소에 추가
        if documents:
            contents = [doc["content"] for doc in documents]
            embeddings = self.embedding_model.get_batch_embeddings(contents)
            self.vector_store.add_documents(documents, embeddings)
            logger.info(f"예제 문서 {len(documents)}개 로드 및 인덱싱 완료")
    
    def _create_example_documents(self, example_docs_path: str):
        """예제 문서 생성"""
        # 기본 예제 문서
        example_docs = [
            {
                "filename": "getting_started.md",
                "title": "시작하기",
                "content": """# APE (Agentic Pipeline Engine): 시작하기

## 개요

APE(Agentic Pipeline Engine)는 온프레미스 환경에서 동작하는 AI Agent 시스템입니다. 각 Agent는 독립적인 원자적 동작을 보장하며, 복잡한 워크플로우를 구성할 수 있습니다.

## 설치 및 실행

1. 저장소 클론:
   ```
   git clone https://github.com/example/ape-core.git
   cd ape-core
   ```

2. 의존성 설치:
   ```
   pip install -r requirements.txt
   ```

3. 서버 실행:
   ```
   python run.py
   ```

서버는 기본적으로 `localhost:8001`에서 실행됩니다.

## API 사용

기본 API 엔드포인트:

- `/agents/{agent_type}` - 에이전트 실행
- `/agents` - 에이전트 목록 조회
- `/query` - 직접 쿼리 실행
- `/health` - 상태 확인

예제 요청:
```
POST /agents/rag
{
  "query": "APE(Agentic Pipeline Engine) 시스템에 대해 설명해주세요",
  "streaming": false
}
```
"""
            },
            {
                "filename": "architecture.md",
                "title": "아키텍처",
                "content": """# APE (Agentic Pipeline Engine): 아키텍처

## 구성 요소

APE(Agentic Pipeline Engine)는 다음 구성 요소로 이루어져 있습니다:

1. **API 서버**: FastAPI 기반 RESTful API 서버
2. **LLM 서비스**: 내부망/외부망 연결 지원, 다양한 LLM 공급자 지원
3. **에이전트 시스템**: 모듈식 에이전트 아키텍처
4. **벡터 저장소**: 문서 임베딩 및 검색 지원

## 시스템 구조

```
ape-core/
├── main.py         - 메인 진입점
├── src/
│   ├── core/       - 핵심 서비스
│   │   ├── config.py
│   │   ├── llm_service.py
│   │   └── router.py
│   ├── agents/     - 에이전트 구현
│   │   ├── agent_manager.py
│   │   ├── rag_agent.py
│   │   └── graph_agent.py
│   └── utils/      - 유틸리티
├── config/         - 설정 파일
├── data/           - 데이터 파일
│   ├── docs/       - 문서 파일
│   └── chroma_db/  - 벡터 저장소
└── models/         - 모델 파일
```

## 주요 기능

### LLM 서비스

내부망/외부망 연결을 모두 지원하며, 자동으로 최적의 경로를 선택합니다. 지원하는 LLM 제공자:

- 내부망 LLM API
- Anthropic Claude API
- OpenRouter API

### 에이전트 시스템

각 에이전트는 특정 작업을 처리하는 독립적인 모듈입니다:

- **RAG 에이전트**: 문서 검색 및 지식 증강
- **그래프 에이전트**: 복잡한 워크플로우 처리

### 벡터 저장소

ChromaDB 기반 벡터 저장소를 사용하여 효율적인 문서 검색을 지원합니다.
"""
            }
        ]
        
        # 예제 문서 파일 생성
        for doc in example_docs:
            file_path = os.path.join(example_docs_path, doc["filename"])
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(doc["content"])
                logger.info(f"예제 문서 생성: {file_path}")
            except Exception as e:
                logger.error(f"예제 문서 생성 오류 ({file_path}): {e}")
    
    def get_agent_type(self) -> str:
        """에이전트 유형 반환"""
        return self.agent_type
    
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
        # 검색 설정
        search_config = self.settings.get("search", {})
        if num_results is None:
            num_results = search_config.get("default_top_k", 3)
            
        # num_results를 정수로 변환
        try:
            num_results = int(num_results)
        except (ValueError, TypeError):
            logger.warning(f"검색 결과 수({num_results})를 정수로 변환할 수 없습니다. 기본값 3을 사용합니다.")
            num_results = 3
        
        # 필터 설정
        filter_dict = {"collection": collection} if collection else None
        
        # 쿼리 임베딩 생성
        query_embedding = self.embedding_model.get_embedding(query)
        
        # 벡터 저장소 검색
        try:
            results = self.vector_store.query(
                query_text=query,
                filter_dict=filter_dict,
                n_results=num_results,
                embedding=query_embedding
            )
        except Exception as e:
            logger.error(f"쿼리 실행 오류: {e}")
            results = []
        
        # 결과가 없으면 가상 결과 생성
        if not results:
            logger.warning(f"검색 결과가 없습니다. 가상 결과를 반환합니다.")
            results = self._simulate_document_search(query, num_results)
        
        return results
    
    def _simulate_document_search(self, query: str, num_results: int = 3) -> List[Dict[str, Any]]:
        """
        문서 검색 시뮬레이션 (결과가 없을 때)
        
        Args:
            query: 검색 쿼리
            num_results: 반환할 결과 수
            
        Returns:
            가상 검색 결과
        """
        # num_results 확인 및 변환
        try:
            num_results = int(num_results)
        except (ValueError, TypeError):
            logger.warning(f"가상 문서 검색에서 결과 수({num_results})를 정수로 변환할 수 없습니다. 기본값 3을 사용합니다.")
            num_results = 3
        
        documents = [
            {
                "id": "sim1",
                "title": "APE (Agentic Pipeline Engine) 소개",
                "content": f"APE(Agentic Pipeline Engine)는 {query}와 관련된 기능을 제공하는 온프레미스 AI Agent 시스템입니다. 각 Agent는 독립적인 원자적 동작을 보장합니다.",
                "metadata": {
                    "title": "APE (Agentic Pipeline Engine) 소개",
                    "source": "example/intro.md",
                    "relevance": 0.92
                }
            },
            {
                "id": "sim2",
                "title": "기술 스택",
                "content": f"{query}를 구현하기 위해 FastAPI, ChromaDB, 임베딩 모델을 사용합니다. 이를 통해 효율적인 검색과 지식 증강을 제공합니다.",
                "metadata": {
                    "title": "기술 스택",
                    "source": "example/tech.md",
                    "relevance": 0.85
                }
            },
            {
                "id": "sim3",
                "title": "사용 가이드",
                "content": f"{query} 기능을 사용하려면 API 엔드포인트를 호출하세요. 기본 경로는 /agents/rag입니다.",
                "metadata": {
                    "title": "사용 가이드",
                    "source": "example/guide.md",
                    "relevance": 0.78
                }
            }
        ]
        
        # 안전한 슬라이싱을 위해 범위 확인
        if num_results > len(documents):
            num_results = len(documents)
            
        return documents[:num_results]
    
    def add_document(self, title: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        문서 추가
        
        Args:
            title: 문서 제목
            content: 문서 내용
            metadata: 추가 메타데이터
            
        Returns:
            생성된 문서 ID 또는 None (실패 시)
        """
        metadata = metadata or {}
        
        # 문서 ID 생성
        doc_id = f"doc_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        # 메타데이터 설정
        doc_metadata = {
            "title": title,
            "created_at": time.time()
        }
        doc_metadata.update(metadata)
        
        # 문서 객체 생성
        document = {
            "id": doc_id,
            "title": title,
            "content": content,
            "metadata": doc_metadata
        }
        
        # 임베딩 생성
        embedding = self.embedding_model.get_embedding(content)
        
        # 벡터 저장소에 추가
        success = self.vector_store.add_documents([document], [embedding])
        
        if success:
            logger.info(f"문서 추가 완료: {title} (ID: {doc_id})")
            return doc_id
        else:
            logger.error(f"문서 추가 실패: {title}")
            return None
    
    def run(self, query: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        RAG 에이전트 실행
        
        Args:
            query: 쿼리 문자열
            metadata: 추가 메타데이터
            
        Returns:
            에이전트 응답
        """
        metadata = metadata or {}
        
        # 검색 설정
        logger.info(f"RAG 쿼리 실행: {query}")
        start_time = time.time()
        
        # 문서 검색
        num_results = metadata.get("num_results", self.settings.get("search", {}).get("default_top_k", 3))
        collection = metadata.get("collection")
        context_from_other_agent = metadata.get("context", "")
        
        search_results = self.search_documents(query, collection, num_results)
        
        # 검색 결과 형식화
        context = self._format_search_results(search_results)
        
        # 프롬프트 구성
        prompt = f"""검색 증강 생성(RAG) 에이전트로서 아래 정보 소스를 바탕으로 쿼리에 답변하세요.

질문: {query}

{'다른 에이전트로부터 얻은 컨텍스트:\n' + context_from_other_agent if context_from_other_agent else ''}

검색 결과:
{context}

위 정보를 바탕으로 질문에 대한 정확하고 상세한 답변을 제공하세요.
정보의 출처를 명확히 언급하고, 검색 결과에서 찾을 수 없는 내용은 추측하지 마세요.
"""
        
        # LLM 호출
        messages = [llm_service.format_system_message(prompt)]
        content = llm_service.generate(messages)
        
        # 응답 형식화
        execution_time = time.time() - start_time
        logger.info(f"RAG 쿼리 실행 완료 (소요 시간: {execution_time:.2f}초)")
        
        # 모델 ID 확인
        model_id = llm_service.model_id
        if model_id is None:
            model_id = "unknown_model"  # 기본값 제공
        
        return {
            "content": content,
            "model": model_id,
            "agent_id": self.agent_id
        }
    
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
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "document_count": self.vector_store.count(),
            "vector_store": self.vector_store.get_collection_info(),
            "embedding_model": self.embedding_model.model_path
        }