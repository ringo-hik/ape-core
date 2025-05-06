"""
기본 데이터베이스 에이전트 모듈

이 모듈은 DB 기반 에이전트의 공통 기능을 제공하는 베이스 클래스를 구현합니다.
"""

import json
import logging
import uuid
import re
from typing import Dict, Any, List, Optional, Union

# 코어 모듈 임포트
import config
from src.core.llm_service import llm_service
from src.utils import extract_sql_query, format_query_result, format_agent_response

# 로깅 설정
logger = logging.getLogger("base_db_agent")

class BaseDBAgent:
    """
    기본 데이터베이스 에이전트 클래스
    
    DB 관련 에이전트의 공통 기능을 제공하는 기본 클래스입니다.
    """
    
    def __init__(self, agent_type: str):
        """
        기본 데이터베이스 에이전트 초기화
        
        Args:
            agent_type: 에이전트 유형 이름 (로깅 및 ID 생성에 사용)
        """
        self.agent_type = agent_type
        logger.info(f"{self.agent_type} 에이전트 초기화")

        # 에이전트 ID 접두사 설정
        self.id_prefix = agent_type.lower().replace(' ', '_')
        
        # Mock 모드 설정 (기본값 True)
        self.mock_mode = True
        
        # 데이터베이스 연결 테스트
        try:
            self.connection_ok = self._test_db_connection()
        except Exception as e:
            logger.warning(f"{self.agent_type} 연결 테스트 예외 발생: {e}")
            self.connection_ok = False
            # 연결 실패해도 에이전트는 초기화 완료 처리
            
        logger.info(f"{self.agent_type} 에이전트 초기화 완료")
    
    def _test_db_connection(self):
        """
        데이터베이스 연결 테스트
        
        서브클래스에서 구현해야 함
        """
        raise NotImplementedError("서브클래스에서 구현해야 함")
        
    def _get_schema_info(self) -> str:
        """
        데이터베이스 스키마 정보 조회
        
        Returns:
            스키마 정보 문자열
        """
        logger.info(f"{self.agent_type} 스키마 정보 조회")
        
        try:
            # 테이블 목록 조회
            tables = self._get_tables()
            
            # 스키마 정보 문자열 구성
            schema_info = "데이터베이스 스키마 정보:\n\n"
            
            for table in tables:
                # 테이블 정보 추가
                schema_info += f"테이블: {table}\n"
                
                # 컬럼 정보 조회
                columns = self._get_table_columns(table)
                
                # 컬럼 정보 추가
                schema_info += "컬럼:\n"
                for col in columns:
                    schema_info += f"  - {col['name']} ({col['type']})"
                    
                    # 기본 키 여부
                    if col.get('primary_key'):
                        schema_info += " PRIMARY KEY"
                    
                    # NULL 허용 여부
                    if not col.get('nullable', True):
                        schema_info += " NOT NULL"
                        
                    # 기본값 있는 경우
                    if 'default' in col:
                        schema_info += f" DEFAULT {col['default']}"
                        
                    schema_info += "\n"
                
                # 외래 키 정보 조회
                foreign_keys = self._get_table_foreign_keys(table)
                
                # 외래 키 정보 추가 (있는 경우)
                if foreign_keys:
                    schema_info += "외래 키:\n"
                    for fk in foreign_keys:
                        schema_info += f"  - {fk['column']} -> {fk['referenced_table']}.{fk['referenced_column']}\n"
                
                schema_info += "\n"
            
            logger.info(f"{self.agent_type} 스키마 정보 조회 완료")
            return schema_info
            
        except Exception as e:
            logger.error(f"{self.agent_type} 스키마 정보 조회 오류: {e}")
            return f"스키마 정보를 조회할 수 없습니다: {str(e)}"
    
    def _get_tables(self) -> List[str]:
        """
        테이블 목록 조회
        
        서브클래스에서 구현해야 함
        
        Returns:
            테이블 이름 목록
        """
        raise NotImplementedError("서브클래스에서 구현해야 함")
    
    def _get_table_columns(self, table: str) -> List[Dict[str, Any]]:
        """
        테이블 컬럼 정보 조회
        
        서브클래스에서 구현해야 함
        
        Args:
            table: 테이블 이름
            
        Returns:
            컬럼 정보 목록
        """
        raise NotImplementedError("서브클래스에서 구현해야 함")
    
    def _get_table_foreign_keys(self, table: str) -> List[Dict[str, str]]:
        """
        테이블 외래 키 정보 조회
        
        서브클래스에서 구현해야 함
        
        Args:
            table: 테이블 이름
            
        Returns:
            외래 키 정보 목록
        """
        raise NotImplementedError("서브클래스에서 구현해야 함")
    
    def run(self, query: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        자연어 쿼리를 SQL로 변환하여 실행
        
        Args:
            query: 자연어 쿼리
            metadata: 추가 메타데이터
            
        Returns:
            SQL 쿼리 실행 결과
        """
        metadata = metadata or {}
        agent_id = f"{self.id_prefix}-{uuid.uuid4()}"
        
        logger.info(f"{self.agent_type} 쿼리 실행 - 에이전트 ID: {agent_id}")
        logger.info(f"입력 쿼리: {query}")
        
        # 스키마 정보 조회 (연결 불가능한 경우 메시지 추가)
        if not hasattr(self, 'connection_ok') or self.connection_ok:
            schema_info = self._get_schema_info()
        else:
            schema_info = "내부망 데이터베이스에 연결할 수 없습니다. 현재 테스트 환경에서 실행 중입니다."
        
        # 프롬프트 구성 - 서브클래스에서 구현해야 함
        prompt = self._build_prompt(query, schema_info)
        
        # LLM 요청
        logger.info(f"{self.agent_type} LLM 요청 - 프롬프트 길이: {len(prompt)}")
        messages = [llm_service.format_user_message(prompt)]
        
        # 모델 응답 생성
        response = llm_service.generate(messages)
        logger.info(f"{self.agent_type} LLM 응답 생성 완료 - 길이: {len(response)}")
        
        # SQL 쿼리 추출
        sql_query = extract_sql_query(response)
        
        if not sql_query:
            logger.warning(f"{self.agent_type} SQL 쿼리 추출 실패")
            return format_agent_response(
                f"죄송합니다. 요청에서 유효한 SQL 쿼리를 생성할 수 없습니다. 다음과 같이 질문을 구체적으로 다시 작성해보세요:\n\n"
                f"- 특정 테이블이나 데이터를 명시적으로 언급\n"
                f"- 원하는 정보의 유형을 명확하게 지정\n"
                f"- 조건이나 필터링 요구사항을 자세히 설명",
                agent_id,
                llm_service.model_id
            )
        
        logger.info(f"{self.agent_type} SQL 쿼리 추출: {sql_query}")
        
        # 연결이 불가능한 경우, 쿼리 실행 대신 메시지 반환
        if hasattr(self, 'connection_ok') and not self.connection_ok:
            logger.warning(f"{self.agent_type} 내부망 데이터베이스 연결 불가: 쿼리 실행 스킵")
            message = (f"내부망 데이터베이스에 연결할 수 없어 쿼리를 실행할 수 없습니다. "
                      f"다음 SQL 쿼리가 계획되었습니다:\n\n```sql\n{sql_query}\n```\n\n"
                      f"현재 테스트 환경에서는 실제 데이터를 조회할 수 없습니다.")
            return format_agent_response(message, agent_id, llm_service.model_id)
            
        # SQL 쿼리 실행
        try:
            result = self._execute_query(sql_query)
            
            # 결과 포맷팅
            formatted_result = format_query_result(result, sql_query, response, self.agent_type)
            
            return format_agent_response(formatted_result, agent_id, llm_service.model_id)
            
        except Exception as e:
            logger.error(f"{self.agent_type} 쿼리 실행 오류: {e}")
            error_message = f"SQL 쿼리 실행 중 오류가 발생했습니다:\n\n```sql\n{sql_query}\n```\n\n오류: {str(e)}"
            return format_agent_response(error_message, agent_id, llm_service.model_id)
    
    def _build_prompt(self, query: str, schema_info: str) -> str:
        """
        LLM 프롬프트 구성
        
        서브클래스에서 구현해야 함
        
        Args:
            query: 사용자 쿼리
            schema_info: 스키마 정보
            
        Returns:
            프롬프트 문자열
        """
        raise NotImplementedError("서브클래스에서 구현해야 함")
    
    def _execute_query(self, query: str) -> Any:
        """
        SQL 쿼리 실행
        
        서브클래스에서 구현해야 함
        
        Args:
            query: SQL 쿼리
            
        Returns:
            쿼리 실행 결과
        """
        raise NotImplementedError("서브클래스에서 구현해야 함")