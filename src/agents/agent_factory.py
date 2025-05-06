"""에이전트 팩토리 모듈

이 모듈은 다양한 유형의 에이전트를 생성하는 팩토리 함수를 제공합니다.
"""

import logging
import traceback
from typing import Optional, Dict, Any

# 로거 설정
logger = logging.getLogger("agent_factory")

# 지원되는 에이전트 유형
AGENT_TYPES = ["rag", "document"]

def create_agent(agent_type: str, **kwargs) -> Optional[Any]:
    """
    에이전트 생성
    
    Args:
        agent_type: 에이전트 유형
        **kwargs: 추가 매개변수
        
    Returns:
        생성된 에이전트 또는 None (실패 시)
    """
    agent_type = agent_type.lower()
    
    if agent_type not in AGENT_TYPES:
        logger.error(f"지원되지 않는 에이전트 유형: {agent_type}")
        return None
    
    try:
        if agent_type == "rag":
            logger.info("RAG 에이전트 생성 시작")
            from src.agents.rag_agent import RAGAgent
            
            # 상세 에러 로깅을 위해 각 단계 분리
            try:
                agent = RAGAgent()
                logger.info("RAG 에이전트 생성 성공")
                return agent
            except Exception as e:
                logger.error(f"RAG 에이전트 초기화 중 오류: {e}")
                logger.error(f"오류 세부 정보: {traceback.format_exc()}")
                raise  # 상세 오류 메시지를 위해 다시 발생
        
        elif agent_type == "document":
            logger.info("문서 관리 에이전트 생성 시작")
            from src.agents.document_management_agent import DocumentManagementAgent
            
            try:
                agent = DocumentManagementAgent()
                logger.info("문서 관리 에이전트 생성 성공")
                return agent
            except Exception as e:
                logger.error(f"문서 관리 에이전트 초기화 중 오류: {e}")
                logger.error(f"오류 세부 정보: {traceback.format_exc()}")
                raise  # 상세 오류 메시지를 위해 다시 발생
        
        return None
    
    except Exception as e:
        logger.error(f"에이전트 생성 오류 ({agent_type}): {e}")
        logger.error(f"오류 세부 정보: {traceback.format_exc()}")
        return None