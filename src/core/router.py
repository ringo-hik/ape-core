"""API 라우터 모듈

이 모듈은 FastAPI 라우터 정의 및 엔드포인트 처리를 담당합니다.
"""

import time
import logging
from typing import Dict, Any, List, Optional, Union
from enum import Enum

from fastapi import FastAPI, HTTPException, BackgroundTasks, status, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.core.config import get_settings
from src.core.llm_service import llm_service
from src.agents.agent_manager import agent_manager
from src.agents.swdp_rpc_api import SWDPRPCAPI

# 로깅 설정
logger = logging.getLogger("api_router")

# SWDP RPC API 인스턴스 초기화
swdp_rpc_api = SWDPRPCAPI()

# ===== API 모델 =====

class AgentType(str, Enum):
    """지원 에이전트 유형"""
    RAG = "rag"
    GRAPH = "graph"
    DOCUMENT = "document"

class QueryRequest(BaseModel):
    """쿼리 요청 모델"""
    query: str = Field(..., description="실행할 자연어 쿼리")
    metadata: Optional[Dict[str, Any]] = Field(None, description="추가 메타데이터")
    streaming: bool = Field(False, description="스트리밍 모드 사용 여부")

class AgentResponse(BaseModel):
    """에이전트 응답 모델"""
    content: str = Field(..., description="응답 내용")
    model: str = Field(..., description="사용된 모델")
    agent_id: str = Field(..., description="에이전트 ID")

class GraphResponse(BaseModel):
    """그래프 응답 모델"""
    content: str = Field(..., description="응답 내용")
    status: str = Field(..., description="실행 상태")
    agent: str = Field(..., description="사용된 에이전트")
    agent_id: str = Field(..., description="에이전트 ID")
    graph_name: str = Field(..., description="그래프 이름")

class AgentConfig(BaseModel):
    """커스텀 에이전트 구성 모델"""
    type: str = Field(..., description="에이전트 유형")
    name: str = Field(..., description="에이전트 이름")
    description: Optional[str] = Field(None, description="설명")
    config: Dict[str, Any] = Field(..., description="추가 구성")

class DocumentUploadRequest(BaseModel):
    """문서 업로드 요청 모델"""
    title: str = Field(..., description="문서 제목")
    content: str = Field(..., description="문서 내용")
    collection: Optional[str] = Field("general", description="문서 컬렉션")
    metadata: Optional[Dict[str, Any]] = Field(None, description="추가 메타데이터")

class DocumentResponse(BaseModel):
    """문서 응답 모델"""
    id: str = Field(..., description="문서 ID")
    title: str = Field(..., description="문서 제목")
    content: Optional[str] = Field(None, description="문서 내용")
    collection: str = Field(..., description="문서 컬렉션")
    created_at: float = Field(..., description="생성 시간")

# SWDP RPC API 모델
class UserRequest(BaseModel):
    """사용자 정보 요청 모델"""
    single_id: str = Field(..., description="사용자 단일 ID (외부 시스템용)")

class BuildInfoRequest(BaseModel):
    """빌드 정보 요청 모델"""
    build_request_id: str = Field(..., description="빌드 요청 고유 ID (외부 참조용)")

class BuildTriggerRequest(BaseModel):
    """빌드 트리거 요청 모델"""
    single_id: str = Field(..., description="사용자 단일 ID (외부 시스템용)")
    project_id: Optional[int] = Field(None, description="프로젝트 ID (내부용, 선택적)")
    project_code: Optional[str] = Field(None, description="프로젝트 코드 (선택적, project_id가 없는 경우 필수)")
    branch: str = Field("main", description="소스 브랜치")
    commit_id: Optional[str] = Field(None, description="커밋 해시 (선택적)")
    environment: str = Field("DEV", description="빌드 환경 (DEV, TEST, STAGE, PROD)")
    title: Optional[str] = Field(None, description="빌드 제목 (선택적)")
    description: Optional[str] = Field(None, description="빌드 설명 (선택적)")

class TRInfoRequest(BaseModel):
    """TR 정보 요청 모델"""
    tr_code: str = Field(..., description="TR 코드 (외부 참조용)")

class TRListRequest(BaseModel):
    """TR 목록 요청 모델"""
    project_id: int = Field(..., description="프로젝트 ID")
    status: Optional[str] = Field(None, description="TR 상태 필터 (선택적)")

class TRCreateRequest(BaseModel):
    """TR 생성 요청 모델"""
    single_id: str = Field(..., description="사용자 단일 ID (외부 시스템용)")
    project_id: int = Field(..., description="프로젝트 ID")
    title: str = Field(..., description="TR 제목")
    description: Optional[str] = Field(None, description="TR 설명 (선택적)")
    type: str = Field("FEATURE", description="TR 유형 (BUG_FIX, FEATURE, ENHANCEMENT, SECURITY)")
    priority: str = Field("MEDIUM", description="우선순위 (HIGH, MEDIUM, LOW)")
    target_release: Optional[str] = Field(None, description="목표 릴리스 버전 (선택적)")

# ===== FastAPI 애플리케이션 =====

app = FastAPI(
    title="AI Agent Core API",
    description="온프레미스 AI Agent 시스템 API",
    version="0.5.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """API 루트"""
    settings = get_settings()
    return {
        "name": settings["app"]["name"],
        "version": settings["version"],
        "description": settings["app"]["description"],
        "endpoints": {
            "에이전트": "/agents/{agent_type}",
            "에이전트 목록": "/agents",
            "에이전트 상태": "/agents/status/{agent_id}",
            "직접 쿼리": "/query",
            "문서 목록": "/documents",
            "문서 조회": "/documents/{doc_id}",
            "문서 업로드": "/documents",
            "문서 삭제": "/documents/{doc_id}",
            "문서 검색": "/documents/search",
            "SWDP API": "/api/swdp",
            "상태 확인": "/health"
        }
    }

@app.get("/agents")
async def list_agents():
    """에이전트 목록 조회"""
    try:
        agents = agent_manager.list_agents()
        return {"agents": agents}
    except Exception as e:
        logger.error(f"에이전트 목록 조회 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"에이전트 목록 조회 오류: {str(e)}"
        )

@app.post("/agents/{agent_type}")
async def run_agent(
    agent_type: AgentType,
    request: QueryRequest,
    background_tasks: BackgroundTasks
):
    """에이전트 실행 엔드포인트"""
    try:
        if request.streaming:
            # 스트리밍 응답
            return StreamingResponse(
                agent_manager.run_agent_stream(agent_type.value, request.query, request.metadata),
                media_type="text/event-stream"
            )
        else:
            # 일반 응답
            result = agent_manager.run_agent(agent_type.value, request.query, request.metadata)
            
            # 딕셔너리 형태로 반환
            if isinstance(result, dict) and "error" in result:
                # 에러 발생 시 에러 반환
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(result["error"])
                )
            
            # 결과가 딕셔너리가 아닌 경우 처리
            if not isinstance(result, dict):
                result = {"content": str(result), "model": llm_service.model_id, "agent_id": f"{agent_type.value}-unknown"}
                
            # 필수 필드 확인 및 추가
            if "content" not in result:
                result["content"] = "응답 내용 없음"
            if "model" not in result:
                result["model"] = llm_service.model_id
            if "agent_id" not in result:
                result["agent_id"] = f"{agent_type.value}-unknown"
                
            return result
    
    except Exception as e:
        logger.error(f"에이전트 실행 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"에이전트 실행 오류: {str(e)}"
        )

@app.get("/agents/status/{agent_id}")
async def get_agent_status(agent_id: str):
    """에이전트 상태 조회"""
    try:
        status = agent_manager.get_agent_status(agent_id)
        return status
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"에이전트 상태 조회 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"에이전트 상태 조회 오류: {str(e)}"
        )

@app.post("/query")
async def direct_query(request: QueryRequest):
    """직접 LLM 쿼리 엔드포인트"""
    try:
        if request.streaming:
            # 스트리밍 응답
            async def stream_generator():
                for chunk in llm_service.generate([llm_service.format_user_message(request.query)], stream=True):
                    yield f"data: {chunk}\n\n"
                yield "data: [DONE]\n\n"
                
            return StreamingResponse(
                stream_generator(),
                media_type="text/event-stream"
            )
        else:
            # 일반 응답
            result = llm_service.generate([llm_service.format_user_message(request.query)], stream=False)
            
            if isinstance(result, dict) and "error" in result:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result["error"]
                )
                
            # 모델 ID 확인
            model_id = llm_service.model_id
            if model_id is None:
                model_id = "unknown_model"  # 기본값 제공
                
            return {"content": result, "model": model_id}
            
    except Exception as e:
        logger.error(f"쿼리 실행 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"쿼리 실행 오류: {str(e)}"
        )

@app.get("/models")
async def list_models():
    """사용 가능한 모델 목록 조회"""
    try:
        models = llm_service.list_available_models()
        
        # 모델 정보 목록으로 변환
        models_info = []
        for model in models:
            models_info.append({
                "key": model.get("key", ""),
                "name": model.get("name", ""),
                "provider": model.get("provider", ""),
                "description": model.get("description", ""),
                "id": model.get("id", "")
            })
        
        return {
            "models": models_info,
            "current_model": llm_service.current_model,
            "model_id": llm_service.model_id
        }
    except Exception as e:
        logger.error(f"모델 목록 조회 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"모델 목록 조회 오류: {str(e)}"
        )

@app.post("/models/{model_name}")
async def change_model(model_name: str):
    """모델 변경"""
    try:
        # 모델 이름 검증
        available_models = llm_service.list_available_models()
        available_model_keys = [model.get("key") for model in available_models]
        
        if model_name not in available_model_keys:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"알 수 없는 모델: {model_name}. 사용 가능한 모델: {', '.join(available_model_keys)}"
            )
        
        # 이전 모델 저장
        previous_model = llm_service.current_model
        previous_model_id = llm_service.model_id
        
        # 모델 변경
        llm_service.change_model(model_name)
        
        return {
            "status": "success",
            "previous_model": previous_model,
            "previous_model_id": previous_model_id,
            "current_model": llm_service.current_model,
            "current_model_id": llm_service.model_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"모델 변경 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"모델 변경 오류: {str(e)}"
        )

@app.post("/documents")
async def upload_document(request: DocumentUploadRequest):
    """문서 업로드 엔드포인트"""
    try:
        # 문서 관리 에이전트 초기화
        document_agent = agent_manager.get_or_create_agent("document")
        if not document_agent:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="문서 관리 에이전트 초기화 실패"
            )
        
        # 요청 메타데이터 설정
        metadata = {
            "command": "upload",
            "title": request.title,
            "content": request.content,
            "collection": request.collection
        }
        
        if request.metadata:
            metadata.update(request.metadata)
        
        # 에이전트 실행
        result = document_agent.run("문서 업로드", metadata)
        
        # 문서 ID 추출
        doc_id = None
        content = result.get("content", "")
        
        # ID 추출 시도
        import re
        id_match = re.search(r"ID: ([\w-]+)", content)
        if id_match:
            doc_id = id_match.group(1)
        
        return {
            "status": "success",
            "message": content,
            "document_id": doc_id
        }
        
    except Exception as e:
        logger.error(f"문서 업로드 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"문서 업로드 오류: {str(e)}"
        )

@app.get("/documents")
async def list_documents(collection: Optional[str] = None):
    """문서 목록 조회 엔드포인트"""
    try:
        # 문서 관리 에이전트 초기화
        document_agent = agent_manager.get_or_create_agent("document")
        if not document_agent:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="문서 관리 에이전트 초기화 실패"
            )
        
        # 요청 메타데이터 설정
        metadata = {
            "command": "list",
            "collection": collection
        }
        
        # 에이전트 실행
        result = document_agent.run("문서 목록 조회", metadata)
        
        return {
            "status": "success",
            "content": result.get("content", ""),
            "collection": collection
        }
        
    except Exception as e:
        logger.error(f"문서 목록 조회 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"문서 목록 조회 오류: {str(e)}"
        )

@app.get("/documents/{doc_id}")
async def get_document(doc_id: str):
    """문서 조회 엔드포인트"""
    try:
        # 문서 관리 에이전트 초기화
        document_agent = agent_manager.get_or_create_agent("document")
        if not document_agent:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="문서 관리 에이전트 초기화 실패"
            )
        
        # 요청 메타데이터 설정
        metadata = {
            "command": "get",
            "doc_id": doc_id
        }
        
        # 에이전트 실행
        result = document_agent.run(f"문서 조회 (ID: {doc_id})", metadata)
        
        return {
            "status": "success",
            "content": result.get("content", ""),
            "document_id": doc_id
        }
        
    except Exception as e:
        logger.error(f"문서 조회 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"문서 조회 오류: {str(e)}"
        )

@app.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """문서 삭제 엔드포인트"""
    try:
        # 문서 관리 에이전트 초기화
        document_agent = agent_manager.get_or_create_agent("document")
        if not document_agent:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="문서 관리 에이전트 초기화 실패"
            )
        
        # 요청 메타데이터 설정
        metadata = {
            "command": "delete",
            "doc_id": doc_id
        }
        
        # 에이전트 실행
        result = document_agent.run(f"문서 삭제 (ID: {doc_id})", metadata)
        
        return {
            "status": "success",
            "message": result.get("content", ""),
            "document_id": doc_id
        }
        
    except Exception as e:
        logger.error(f"문서 삭제 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"문서 삭제 오류: {str(e)}"
        )

@app.post("/documents/search")
async def search_documents(request: QueryRequest):
    """문서 검색 엔드포인트"""
    try:
        # 문서 관리 에이전트 초기화
        document_agent = agent_manager.get_or_create_agent("document")
        if not document_agent:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="문서 관리 에이전트 초기화 실패"
            )
        
        # 요청 메타데이터 설정
        metadata = {
            "command": "search",
            "collection": request.metadata.get("collection") if request.metadata else None,
            "num_results": request.metadata.get("num_results", 5) if request.metadata else 5
        }
        
        # 에이전트 실행
        if request.streaming:
            # 스트리밍 응답
            return StreamingResponse(
                agent_manager.run_agent_stream("document", request.query, metadata),
                media_type="text/event-stream"
            )
        else:
            # 일반 응답
            result = document_agent.run(request.query, metadata)
            
            return {
                "status": "success",
                "content": result.get("content", ""),
                "model": result.get("model", "unknown_model"),
                "agent_id": result.get("agent_id", "")
            }
        
    except Exception as e:
        logger.error(f"문서 검색 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"문서 검색 오류: {str(e)}"
        )

# SWDP RPC API 엔드포인트
@app.post("/api/swdp/user")
async def get_user_info(request: UserRequest):
    """사용자 정보 조회 엔드포인트"""
    try:
        result = swdp_rpc_api.get_user_by_single_id(request.single_id)
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"사용자 정보 조회 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"사용자 정보 조회 오류: {str(e)}"
        )

@app.post("/api/swdp/user/projects")
async def get_user_projects(request: UserRequest):
    """사용자 프로젝트 목록 조회 엔드포인트"""
    try:
        result = swdp_rpc_api.get_user_projects(request.single_id)
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"사용자 프로젝트 목록 조회 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"사용자 프로젝트 목록 조회 오류: {str(e)}"
        )

@app.post("/api/swdp/build")
async def get_build_info(request: BuildInfoRequest):
    """빌드 정보 조회 엔드포인트"""
    try:
        result = swdp_rpc_api.get_build_by_id(request.build_request_id)
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"빌드 정보 조회 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"빌드 정보 조회 오류: {str(e)}"
        )

@app.post("/api/swdp/build/logs")
async def get_build_logs(request: BuildInfoRequest):
    """빌드 로그 조회 엔드포인트"""
    try:
        result = swdp_rpc_api.get_build_logs(request.build_request_id)
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"빌드 로그 조회 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"빌드 로그 조회 오류: {str(e)}"
        )

@app.post("/api/swdp/build/trigger")
async def trigger_build(request: BuildTriggerRequest):
    """빌드 트리거 엔드포인트"""
    try:
        # 프로젝트 ID 또는 코드 필수 검증
        if not request.project_id and not request.project_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="프로젝트 ID 또는 프로젝트 코드는 필수 파라미터입니다."
            )
        
        result = swdp_rpc_api.trigger_build(
            single_id=request.single_id,
            project_id=request.project_id,
            project_code=request.project_code,
            branch=request.branch,
            commit_id=request.commit_id,
            environment=request.environment,
            title=request.title,
            description=request.description
        )
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"빌드 트리거 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"빌드 트리거 오류: {str(e)}"
        )

@app.post("/api/swdp/tr")
async def get_tr_info(request: TRInfoRequest):
    """TR 정보 조회 엔드포인트"""
    try:
        result = swdp_rpc_api.get_tr_by_code(request.tr_code)
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TR 정보 조회 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"TR 정보 조회 오류: {str(e)}"
        )

@app.post("/api/swdp/tr/list")
async def get_tr_list(request: TRListRequest):
    """TR 목록 조회 엔드포인트"""
    try:
        result = swdp_rpc_api.get_tr_by_project(request.project_id, request.status)
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TR 목록 조회 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"TR 목록 조회 오류: {str(e)}"
        )

@app.post("/api/swdp/tr/create")
async def create_tr(request: TRCreateRequest):
    """TR 생성 엔드포인트"""
    try:
        result = swdp_rpc_api.create_tr(
            single_id=request.single_id,
            project_id=request.project_id,
            title=request.title,
            description=request.description,
            type=request.type,
            priority=request.priority,
            target_release=request.target_release
        )
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TR 생성 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"TR 생성 오류: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """서비스 상태 확인"""
    settings = get_settings()
    
    # 모델 정보 가져오기
    models_info = []
    models = llm_service.list_available_models()
    for model in models:
        models_info.append({
            "key": model.get("key", ""),
            "name": model.get("name", ""),
            "provider": model.get("provider", ""),
            "description": model.get("description", ""),
            "id": model.get("id", "")
        })
    
    return {
        "status": "healthy",
        "version": settings.get("version", "0.5.0"),
        "timestamp": time.time(),
        "model": llm_service.model_id,
        "api_host": f"{settings.get('api', {}).get('host', 'localhost')}:{settings.get('api', {}).get('port', '8001')}",
        "agents": agent_manager.list_agents(),
        "available_models": models_info,
        "default_model": llm_service.current_model
    }