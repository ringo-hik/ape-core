"""
에이전트 오케스트레이터 모듈

이 모듈은 여러 에이전트 간의 조정과 통신을 관리합니다.
langgraph를 사용하여 복잡한 에이전트 워크플로우를 구성합니다.
"""

import os
import uuid
import logging
import threading
from typing import Dict, Any, List, Optional, Union, Generator, Type

# 설정 임포트
import config
from src.core.llm_service import llm_service

# 에이전트 임포트
from src.agents.swdp_db_agent import SWDPDBAgent
from src.agents.jira_agent import JiraAgent
from src.agents.bitbucket_agent import BitbucketAgent
from src.agents.pocket_agent import PocketAgent
from src.agents.rag_agent import RAGAgent
from src.agents.swdp_agent import SWDPAgent
from src.agents.langgraph_agent import LangGraphAgent

# 로깅 설정
logger = logging.getLogger("agent_orchestrator")

# 단순화된 락 메커니즘 - 스레드 락 사용
agent_lock = threading.Lock()

class AgentOrchestrator:
    """
    에이전트 오케스트레이터
    
    여러 에이전트 간의 조정 및 워크플로우 관리를 담당합니다.
    """
    
    def __init__(self):
        """에이전트 오케스트레이터 초기화"""
        logger.info("에이전트 오케스트레이터 초기화")
        
        # 에이전트 매핑
        self.agent_types = {
            "swdp_db": SWDPDBAgent,
            "jira": JiraAgent,
            "bitbucket": BitbucketAgent,
            "pocket": PocketAgent,
            "rag": RAGAgent,
            "swdp": SWDPAgent
        }
        
        # 고급 에이전트 타입
        self.complex_agent_types = {
            "langgraph": self._create_langgraph_agent
        }
        
        # 에이전트 캐시
        self.agent_cache = {}
        
        # 임시 체크포인트 디렉토리
        self.checkpoint_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "tmp", "checkpoints")
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        
        logger.info("에이전트 오케스트레이터 초기화 완료")
    
    def run_agent(self, agent_type: str, query: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        에이전트 실행
        
        Args:
            agent_type: 에이전트 유형 (swdp_db, jira, bitbucket, s3, graph, langgraph)
            query: 자연어 쿼리
            metadata: 추가 메타데이터
            
        Returns:
            에이전트 응답
        """
        logger.info(f"에이전트 실행: {agent_type}, 쿼리: {query}")
        metadata = metadata or {}
        
        if agent_type == "graph":
            # 그래프 에이전트 (기본 복합 에이전트)
            return self._run_graph_agent(query, metadata)
        elif agent_type == "langgraph":
            # 고급 langgraph 기반 복합 에이전트
            return self._run_langgraph_agent(query, metadata)
        elif agent_type in self.complex_agent_types:
            # 기타 복합 에이전트
            return self._run_complex_agent(agent_type, query, metadata)
        else:
            # 개별 에이전트
            return self._run_single_agent(agent_type, query, metadata)
    
    def _get_agent(self, agent_type: str):
        """에이전트 인스턴스 가져오기 (캐싱)"""
        if agent_type not in self.agent_cache:
            if agent_type in self.agent_types:
                self.agent_cache[agent_type] = self.agent_types[agent_type]()
            elif agent_type in self.complex_agent_types:
                # 복합 에이전트 생성은 별도 함수에서 처리
                pass  
            else:
                raise ValueError(f"알 수 없는 에이전트 유형: {agent_type}")
        
        return self.agent_cache[agent_type]
    
    def _run_single_agent(self, agent_type: str, query: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """단일 에이전트 실행"""
        try:
            # 에이전트 가져오기
            agent = self._get_agent(agent_type)
            
            # 에이전트 실행
            with agent_lock:
                result = agent.run(query, metadata)
            
            return result
            
        except Exception as e:
            logger.error(f"에이전트 실행 오류: {e}")
            
            # 에이전트 ID 생성
            agent_id = f"{agent_type}-{uuid.uuid4()}"
            
            # 오류 응답
            return {
                "content": f"에이전트 실행 오류: {str(e)}",
                "model": llm_service.model_id,
                "agent_id": agent_id
            }
    
    def _run_complex_agent(self, agent_type: str, query: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """복합 에이전트 실행"""
        try:
            # 복합 에이전트 생성 함수 가져오기
            create_func = self.complex_agent_types.get(agent_type)
            if not create_func:
                raise ValueError(f"알 수 없는 복합 에이전트 유형: {agent_type}")
            
            # 에이전트 생성 및 실행
            agent = create_func()
            
            # 에이전트 실행
            with agent_lock:
                result = agent.run(query, metadata)
            
            return result
            
        except Exception as e:
            logger.error(f"복합 에이전트 실행 오류: {e}")
            
            # 에이전트 ID 생성
            agent_id = f"{agent_type}-{uuid.uuid4()}"
            
            # 오류 응답
            return {
                "content": f"복합 에이전트 실행 오류: {str(e)}",
                "model": llm_service.model_id,
                "agent_id": agent_id
            }
    
    def _create_langgraph_agent(self):
        """LangGraph 에이전트 생성"""
        # 필요한 모든 에이전트 인스턴스 생성
        agent_instances = {}
        
        for agent_type in self.agent_types:
            try:
                if agent_type not in self.agent_cache:
                    self.agent_cache[agent_type] = self.agent_types[agent_type]()
                agent_instances[agent_type] = self.agent_cache[agent_type]
            except Exception as e:
                logger.warning(f"에이전트 {agent_type} 초기화 실패: {e}")
        
        # LangGraph 에이전트 생성
        return LangGraphAgent(agent_instances)
    
    def _run_langgraph_agent(self, query: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """LangGraph 에이전트 실행"""
        # 에이전트 캐시에서 확인
        if "langgraph" not in self.agent_cache:
            self.agent_cache["langgraph"] = self._create_langgraph_agent()
        
        # 에이전트 가져오기
        agent = self.agent_cache["langgraph"]
        
        # 에이전트 실행
        with agent_lock:
            result = agent.run(query, metadata)
        
        return result
    
    def _run_graph_agent(self, query: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """그래프 에이전트 실행 (복합 에이전트)"""
        # 임시 그래프 에이전트 구현
        agent_id = f"graph-{uuid.uuid4()}"
        graph_name = "multi_agent_graph"
        
        # 라우팅 프롬프트
        prompt = """에이전트 라우터로서 쿼리를 분석하여 적절한 에이전트를 선택합니다.
사용 가능한 에이전트: swdp_db, jira, bitbucket, s3, rag, swdp

각 에이전트 용도:
- swdp_db: 데이터베이스 쿼리, 테이블 정보, 데이터 분석
- jira: 이슈 추적, 티켓 관리, 프로젝트 관리
- bitbucket: 코드 저장소, 버전 관리, PR 관리
- s3: 파일 스토리지, 버킷 관리, 객체 관리
- rag: 문서 검색, 지식 증강, 정보 검색
- swdp: SW 개발 포털, TR 정보, 티켓 관리

쿼리를 분석하세요:
{query}

어떤 에이전트가 이 쿼리를 처리하는 데 가장 적합한가요?"""
        
        # 라우팅 수행
        messages = [llm_service.format_user_message(prompt)]
        agent_choice = llm_service.generate(messages)
        
        # 라우팅 결과 처리
        selected_agent = "none"
        for agent_name in self.agent_types.keys():
            if agent_name.lower() in agent_choice.lower():
                selected_agent = agent_name
                break
        
        # 선택된 에이전트 실행
        if selected_agent != "none":
            result = self._run_single_agent(selected_agent, query, metadata)
            content = result.get("content", "응답 없음")
        else:
            content = "적합한 에이전트를 찾을 수 없습니다. 더 구체적인 쿼리를 입력해주세요."
        
        # 그래프 형식 응답 반환
        return {
            "content": content,
            "status": "success" if selected_agent != "none" else "error",
            "agent": selected_agent,
            "agent_id": agent_id,
            "graph_name": graph_name
        }
    
    def run_agent_stream(self, agent_type: str, query: str, metadata: Optional[Dict[str, Any]] = None) -> Generator[str, None, None]:
        """
        스트리밍 에이전트 실행
        
        Args:
            agent_type: 에이전트 유형
            query: 자연어 쿼리
            metadata: 추가 메타데이터
            
        Yields:
            스트리밍 응답 조각
        """
        logger.info(f"스트리밍 에이전트 실행: {agent_type}, 쿼리: {query}")
        metadata = metadata or {}
        
        # 복합 에이전트는 스트리밍 지원하지 않음
        if agent_type in ["graph", "langgraph"] or agent_type in self.complex_agent_types:
            # 단일 청크로 전체 응답 반환
            response = self.run_agent(agent_type, query, metadata)
            yield response.get("content", "스트리밍이 지원되지 않는 에이전트입니다.")
            return
            
        # 에이전트 ID 생성
        agent_id = f"{agent_type}-{uuid.uuid4()}"
        
        # 간단한 프롬프트 생성
        prompt = f"""에이전트 유형: {agent_type}
작업: {query}

유용하고 정확한 응답을 제공하세요.
"""
        
        # 메시지 구성
        messages = [llm_service.format_system_message(prompt)]
        
        # LLM 스트리밍 호출
        with agent_lock:
            response = llm_service.generate(messages, stream=True)
        
        # 스트리밍 처리
        for chunk in llm_service.process_stream(response):
            yield chunk