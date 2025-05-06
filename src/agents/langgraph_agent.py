"""
LangGraph 에이전트 - 고급 에이전트 오케스트레이션

이 모듈은 langgraph를 사용하여 복잡한 에이전트 워크플로우를 구현합니다.
여러 에이전트 간의 연쇄적 호출 및 상태 관리를 지원합니다.
"""

import os
import uuid
import logging
import json
import copy
from typing import Dict, Any, List, Optional, Union, Callable, Type, TypedDict

import config
from src.core.llm_service import llm_service

# 로깅 설정
logger = logging.getLogger("langgraph_agent")

# 상태 타입 정의
class GraphState(TypedDict):
    """그래프 상태 타입"""
    query: str
    context: Dict[str, Any]
    current_agent: str
    agent_outputs: Dict[str, Any]
    next_agent: Optional[str]
    final_output: Optional[str]
    error: Optional[str]

class AgentNode:
    """에이전트 노드"""
    
    def __init__(self, agent_type: str, agent_instance: Any):
        """
        에이전트 노드 초기화
        
        Args:
            agent_type: 에이전트 유형
            agent_instance: 에이전트 인스턴스
        """
        self.agent_type = agent_type
        self.agent = agent_instance
        
    def run(self, state: GraphState) -> GraphState:
        """
        에이전트 노드 실행
        
        Args:
            state: 현재 그래프 상태
            
        Returns:
            업데이트된 그래프 상태
        """
        try:
            # 기존 상태 복사
            new_state = copy.deepcopy(state)
            
            # 쿼리와 컨텍스트 준비
            query = state["query"]
            context = state["context"]
            
            logger.info(f"AgentNode 실행: {self.agent_type}, 쿼리: {query}")
            
            # 에이전트 실행
            metadata = {
                "context": context,
                **context  # 컨텍스트 내용을 메타데이터에 병합
            }
            
            result = self.agent.run(query, metadata)
            
            # 결과 저장
            new_state["agent_outputs"][self.agent_type] = result
            new_state["context"][self.agent_type] = result.get("content", "")
            
            # 다음 에이전트 지정이 없으면 종료
            if new_state["next_agent"] is None:
                new_state["final_output"] = result.get("content", "")
            
            return new_state
            
        except Exception as e:
            logger.error(f"AgentNode 실행 오류: {e}")
            
            # 오류 상태 반환
            state["error"] = f"에이전트 노드 오류: {str(e)}"
            return state

class RouterNode:
    """라우터 노드"""
    
    def __init__(self, llm_service, agent_types: List[str]):
        """
        라우터 노드 초기화
        
        Args:
            llm_service: LLM 서비스
            agent_types: 사용 가능한 에이전트 유형 목록
        """
        self.llm = llm_service
        self.agent_types = agent_types
    
    def run(self, state: GraphState) -> GraphState:
        """
        라우터 노드 실행
        
        Args:
            state: 현재 그래프 상태
            
        Returns:
            업데이트된 그래프 상태
        """
        try:
            # 기존 상태 복사
            new_state = copy.deepcopy(state)
            
            query = state["query"]
            context = state["context"]
            
            # 컨텍스트 문자열 조합
            context_str = ""
            for agent_type, content in context.items():
                if content:
                    context_str += f"=== {agent_type.upper()} 컨텍스트 ===\n{content}\n\n"
            
            # 라우팅 프롬프트
            prompt = f"""라우터로서 현재 쿼리와 컨텍스트를 분석하여 다음에 실행할 에이전트를 결정해야 합니다.

사용 가능한 에이전트:
{', '.join(self.agent_types)}

각 에이전트 용도:
- sql: 데이터베이스 쿼리, 테이블 정보, 데이터 분석
- jira: 이슈 추적, 티켓 관리, 프로젝트 관리
- bitbucket: 코드 저장소, 버전 관리, PR 관리
- s3: 파일 스토리지, 버킷 관리, 객체 관리
- rag: 문서 검색, 지식 증강, 정보 검색
- swdp: SW개발 포털 정보, TR 정보 확인, 티켓 조회

현재 쿼리:
{query}

{'현재 컨텍스트:\n' + context_str if context_str else '컨텍스트 없음'}

작업:
1) 현재 쿼리를 처리하기 위해 다음에 실행할 최적의 에이전트를 선택하세요.
2) 선택한 에이전트 이름만 반환하세요(다른 설명 없이).
3) 선택할 에이전트가 없으면(최종 응답이 가능하거나 종료 필요) "none"을 반환하세요.

에이전트 이름:"""
            
            # 라우팅 응답 생성
            messages = [self.llm.format_user_message(prompt)]
            routing_result = self.llm.generate(messages)
            
            # 결과 처리
            if isinstance(routing_result, dict) and "error" in routing_result:
                new_state["error"] = f"라우팅 오류: {routing_result['error']}"
                new_state["next_agent"] = None
                return new_state
            
            # 결과에서 에이전트 이름 추출
            next_agent = routing_result.strip().lower()
            
            # 지원되는 에이전트 확인
            if next_agent != "none" and next_agent not in self.agent_types:
                logger.warning(f"알 수 없는 에이전트: {next_agent}, 기본값으로 'none' 사용")
                next_agent = "none"
            
            # 다음 에이전트 설정
            new_state["next_agent"] = None if next_agent == "none" else next_agent
            
            logger.info(f"라우팅 결과: {next_agent}")
            return new_state
            
        except Exception as e:
            logger.error(f"RouterNode 실행 오류: {e}")
            
            # 오류 상태 반환
            state["error"] = f"라우터 노드 오류: {str(e)}"
            state["next_agent"] = None
            return state

class OutputNode:
    """최종 출력 노드"""
    
    def run(self, state: GraphState) -> GraphState:
        """
        출력 노드 실행
        
        Args:
            state: 현재 그래프 상태
            
        Returns:
            업데이트된 그래프 상태
        """
        try:
            # 기존 상태 복사
            new_state = copy.deepcopy(state)
            
            # 에러가 있으면 처리
            if state["error"]:
                new_state["final_output"] = f"오류 발생: {state['error']}"
                return new_state
            
            # 최종 응답 생성에 필요한 컨텍스트 수집
            query = state["query"]
            context_str = ""
            
            for agent_type, content in state["context"].items():
                if content:
                    context_str += f"=== {agent_type.upper()} 결과 ===\n{content}\n\n"
            
            # 응답 생성 프롬프트
            prompt = f"""복합 에이전트 워크플로우의 최종 출력을 생성해야 합니다.

원래 쿼리:
{query}

각 에이전트 결과:
{context_str}

위 정보를 종합하여 사용자에게 명확하고 일관된 최종 응답을 제공하세요.
각 에이전트의 결과를 적절하게 인용하고, 응답이 어떻게 쿼리에 답하는지 설명하세요.
불필요한 기술적 세부 사항은 생략하고 사용자에게 가장 유용한 정보에 집중하세요.
응답 형식은 사용자가 쉽게 이해할 수 있는 명확한 형태로 구성하세요.
"""
            
            # 최종 응답 생성
            messages = [llm_service.format_system_message(prompt)]
            final_output = llm_service.generate(messages)
            
            # 오류 처리
            if isinstance(final_output, dict) and "error" in final_output:
                new_state["final_output"] = f"최종 출력 생성 오류: {final_output['error']}"
                return new_state
            
            # 최종 출력 설정
            new_state["final_output"] = final_output
            
            return new_state
            
        except Exception as e:
            logger.error(f"OutputNode 실행 오류: {e}")
            
            # 오류 상태 반환
            state["final_output"] = f"출력 노드 오류: {str(e)}"
            return state

class LangGraphAgent:
    """LangGraph 기반 복합 에이전트"""
    
    def __init__(self, agent_instances: Dict[str, Any]):
        """
        LangGraph 에이전트 초기화
        
        Args:
            agent_instances: 에이전트 인스턴스 맵 (이름 -> 인스턴스)
        """
        self.agent_id = f"langgraph-{uuid.uuid4()}"
        self.agent_instances = agent_instances
        self.agent_types = list(agent_instances.keys())
        
        # 노드 생성
        self.router = RouterNode(llm_service, self.agent_types)
        self.agent_nodes = {
            agent_type: AgentNode(agent_type, agent_instance)
            for agent_type, agent_instance in agent_instances.items()
        }
        self.output_node = OutputNode()
        
        logger.info(f"LangGraph 에이전트 초기화: {self.agent_id}, 에이전트: {', '.join(self.agent_types)}")
    
    def run(self, query: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        복합 에이전트 워크플로우 실행
        
        Args:
            query: 자연어 쿼리
            metadata: 추가 메타데이터
            
        Returns:
            에이전트 응답
        """
        logger.info(f"LangGraph 에이전트 실행: {query}")
        metadata = metadata or {}
        
        # 최대 에이전트 호출 수 (무한 루프 방지)
        max_steps = metadata.get("max_steps", 10)
        
        # 초기 상태 설정
        state: GraphState = {
            "query": query,
            "context": metadata.get("context", {}),
            "current_agent": "",
            "agent_outputs": {},
            "next_agent": "start",  # 시작 상태 표시
            "final_output": None,
            "error": None
        }
        
        # 에이전트 그래프 실행
        step = 0
        
        try:
            # 그래프 실행 (라우터 -> 에이전트 -> ... -> 출력)
            while state["next_agent"] and step < max_steps:
                # 다음 단계 유형에 따라 처리
                if state["next_agent"] == "start":
                    # 초기 라우팅
                    state["current_agent"] = "router"
                    state = self.router.run(state)
                elif state["next_agent"] in self.agent_types:
                    # 에이전트 실행
                    agent_type = state["next_agent"]
                    state["current_agent"] = agent_type
                    state = self.agent_nodes[agent_type].run(state)
                    # 다시 라우터로 이동
                    state["next_agent"] = "router"
                elif state["next_agent"] == "router":
                    # 라우터 실행
                    state["current_agent"] = "router"
                    state = self.router.run(state)
                    
                # 최대 단계 확인
                step += 1
                logger.info(f"LangGraph 단계 {step}: {state['current_agent']} -> {state['next_agent']}")
                
                # 오류 확인
                if state["error"]:
                    logger.error(f"그래프 실행 오류: {state['error']}")
                    break
            
            # 최대 단계 초과 확인
            if step >= max_steps and state["next_agent"]:
                state["error"] = f"최대 단계 수({max_steps})를 초과했습니다. 무한 루프 가능성이 있습니다."
            
            # 최종 출력 생성
            if not state["final_output"]:
                state = self.output_node.run(state)
            
            # 결과 반환
            return self._format_response(state)
            
        except Exception as e:
            logger.error(f"LangGraph 실행 오류: {e}")
            return self._format_error_response(str(e))
    
    def _format_response(self, state: GraphState) -> Dict[str, Any]:
        """응답 형식화"""
        # 그래프 실행 요약
        agent_path = []
        for agent_type, output in state["agent_outputs"].items():
            agent_id = output.get("agent_id", "unknown")
            agent_path.append(f"{agent_type} ({agent_id})")
        
        # 실행 경로
        execution_path = " -> ".join(agent_path) if agent_path else "직접 응답"
        
        return {
            "content": state["final_output"] or "응답을 생성할 수 없습니다.",
            "model": llm_service.model_id,
            "agent_id": self.agent_id,
            "error": state["error"],
            "execution_path": execution_path,
            "agent_outputs": state["agent_outputs"]
        }
    
    def _format_error_response(self, error: str) -> Dict[str, Any]:
        """오류 응답 형식화"""
        return {
            "content": f"오류: {error}",
            "model": llm_service.model_id,
            "agent_id": self.agent_id,
            "error": error,
            "execution_path": "오류 발생",
            "agent_outputs": {}
        }