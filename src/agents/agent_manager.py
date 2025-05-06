"""에이전트 관리자 모듈

이 모듈은 다양한 에이전트의 생성 및 관리를 담당합니다.
에이전트의 초기화, 실행 및 상태 관리 기능을 제공합니다.
"""

import uuid
import time
import logging
from typing import Dict, List, Any, Optional, Union, Generator

from src.core.config import get_settings
from src.core.llm_service import llm_service
from src.agents.rag_agent import RAGAgent
from src.agents.document_management_agent import DocumentManagementAgent

# 로깅 설정
logger = logging.getLogger("agent_manager")

class AgentManager:
    """에이전트 관리자 클래스"""
    
    def __init__(self):
        """에이전트 관리자 초기화"""
        self.agents: Dict[str, Any] = {}
        self.settings = get_settings()
        
        # 사용 가능한 에이전트 유형
        self.available_agent_types = self.settings.get("agents", {}).get(
            "available", ["rag", "graph", "document"]
        )
        
        logger.info(f"에이전트 관리자 초기화 완료 (사용 가능 에이전트: {', '.join(self.available_agent_types)})")
    
    def create_agent(self, agent_type: str, **kwargs) -> Optional[Any]:
        """
        에이전트 생성
        
        Args:
            agent_type: 생성할 에이전트 유형
            **kwargs: 에이전트 생성에 필요한 추가 인자
            
        Returns:
            생성된 에이전트 또는 None (실패 시)
        """
        if agent_type not in self.available_agent_types:
            logger.error(f"지원되지 않는 에이전트 유형: {agent_type}")
            return None
        
        try:
            # 에이전트 유형에 따른 인스턴스 생성
            if agent_type == "rag":
                logger.info("RAG 에이전트 생성 시작")
                try:
                    agent = RAGAgent()
                    logger.info("RAG 에이전트 객체 생성 성공")
                except Exception as e:
                    import traceback
                    logger.error(f"RAG 에이전트 초기화 중 오류: {e}")
                    logger.error(f"오류 스택 트레이스: {traceback.format_exc()}")
                    return None
            elif agent_type == "document":
                logger.info("문서 관리 에이전트 생성 시작")
                try:
                    agent = DocumentManagementAgent()
                    logger.info("문서 관리 에이전트 객체 생성 성공")
                except Exception as e:
                    import traceback
                    logger.error(f"문서 관리 에이전트 초기화 중 오류: {e}")
                    logger.error(f"오류 스택 트레이스: {traceback.format_exc()}")
                    return None
            elif agent_type == "graph":
                # 그래프 에이전트는 미구현
                logger.warning("그래프 에이전트는 현재 구현되지 않았습니다")
                return None
            else:
                logger.error(f"지원되지 않는 에이전트 유형: {agent_type}")
                return None
            
            # 에이전트 저장
            agent_id = agent.agent_id
            self.agents[agent_id] = agent
            
            logger.info(f"에이전트 생성 완료: {agent_type} (ID: {agent_id})")
            return agent
        
        except Exception as e:
            import traceback
            logger.error(f"에이전트 생성 오류: {e}")
            logger.error(f"오류 스택 트레이스: {traceback.format_exc()}")
            return None
    
    def get_agent(self, agent_id: str) -> Optional[Any]:
        """
        에이전트 인스턴스 조회
        
        Args:
            agent_id: 에이전트 ID
            
        Returns:
            에이전트 인스턴스 또는 None (없을 경우)
        """
        agent = self.agents.get(agent_id)
        if agent is None:
            logger.warning(f"에이전트를 찾을 수 없음: {agent_id}")
        return agent
    
    def get_or_create_agent(self, agent_type: str) -> Optional[Any]:
        """
        에이전트 조회 또는 생성
        
        Args:
            agent_type: 에이전트 유형
            
        Returns:
            에이전트 인스턴스 또는 None (생성 실패 시)
        """
        # 이미 존재하는 에이전트 유형 찾기
        for agent in self.agents.values():
            if agent.get_agent_type() == agent_type:
                return agent
        
        # 없으면 새로 생성
        return self.create_agent(agent_type)
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """
        에이전트 목록 반환
        
        Returns:
            에이전트 정보 목록
        """
        agent_list = []
        for agent_id, agent in self.agents.items():
            agent_list.append({
                "id": agent_id,
                "type": agent.get_agent_type(),
                "status": "active"
            })
        
        return agent_list
    
    def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """
        에이전트 상태 조회
        
        Args:
            agent_id: 에이전트 ID
            
        Returns:
            에이전트 상태 정보
            
        Raises:
            ValueError: 에이전트가 존재하지 않을 경우
        """
        agent = self.get_agent(agent_id)
        if agent is None:
            raise ValueError(f"에이전트를 찾을 수 없음: {agent_id}")
        
        return {
            "id": agent_id,
            "type": agent.get_agent_type(),
            "status": "active",
            "stats": agent.get_stats()
        }
    
    def run_agent(self, agent_type: str, query: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        에이전트 실행
        
        Args:
            agent_type: 실행할 에이전트 유형
            query: 쿼리 문자열
            metadata: 추가 메타데이터
            
        Returns:
            에이전트 응답
            
        Raises:
            Exception: 에이전트 실행 오류 시
        """
        metadata = metadata or {}
        
        # 에이전트 조회 또는 생성
        agent = self.get_or_create_agent(agent_type)
        if agent is None:
            raise Exception(f"에이전트 생성 실패: {agent_type}")
        
        logger.info(f"에이전트 실행: {agent_type}, 쿼리: {query[:50]}...")
        
        # 에이전트 실행
        try:
            start_time = time.time()
            result = agent.run(query, metadata)
            execution_time = time.time() - start_time
            
            logger.info(f"에이전트 실행 완료: {agent_type} (소요 시간: {execution_time:.2f}초)")
            return result
            
        except Exception as e:
            logger.error(f"에이전트 실행 오류: {e}")
            raise
    
    def run_agent_stream(self, agent_type: str, query: str, metadata: Optional[Dict[str, Any]] = None) -> Generator[str, None, None]:
        """
        에이전트 스트리밍 실행
        
        Args:
            agent_type: 실행할 에이전트 유형
            query: 쿼리 문자열
            metadata: 추가 메타데이터
            
        Returns:
            에이전트 응답 스트림
            
        Raises:
            Exception: 에이전트 실행 오류 시
        """
        metadata = metadata or {}
        
        # 에이전트 조회 또는 생성
        agent = self.get_or_create_agent(agent_type)
        if agent is None:
            yield f"data: {{'error': '에이전트 생성 실패: {agent_type}'}}\n\n"
            return
        
        logger.info(f"에이전트 스트리밍 실행: {agent_type}, 쿼리: {query[:50]}...")
        
        # 에이전트 스트리밍 실행
        try:
            # 현재 스트리밍을 지원하지 않는 경우
            if not hasattr(agent, 'run_stream'):
                # 일반 실행 결과를 한 번에 전송
                result = agent.run(query, metadata)
                yield f"data: {result}\n\n"
                yield "data: [DONE]\n\n"
                return
            
            # 스트리밍 실행
            for chunk in agent.run_stream(query, metadata):
                yield f"data: {chunk}\n\n"
            
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"에이전트 스트리밍 실행 오류: {e}")
            yield f"data: {{'error': '에이전트 실행 오류: {str(e)}'}}\n\n"
            yield "data: [DONE]\n\n"

# 싱글톤 인스턴스
agent_manager = AgentManager()