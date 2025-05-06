"""
SWDP DB 에이전트 - SWDP 데이터 쿼리 실행 에이전트

이 모듈은 자연어를 SWDP 데이터베이스 쿼리로 변환하여 SWDP 관련 작업을 수행합니다.
"""

import logging
import json
import os
import re
import random
from typing import Dict, Any, List, Tuple, Optional, Union
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

import config
from src.agents.base_db_agent import BaseDBAgent
from src.core.llm_service import llm_service

# 로깅 설정
logger = logging.getLogger("swdp_db_agent")

class SWDPDBAgent(BaseDBAgent):
    """SWDP 데이터 쿼리 실행 에이전트"""
    
    def __init__(self):
        """SWDP DB 에이전트 초기화"""
        # 부모 클래스 초기화
        super().__init__("SWDP DB")
        
        # 스키마 정보 로드
        self.schema_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                        "src", "schema", "swdp-db.json")
        self.schema_info = self._load_schema()
        
        # Mock 모드 설정
        self.mock_mode = True
        logger.info(f"SWDP DB 에이전트 초기화 완료 (Mock 모드: {self.mock_mode})")
    
    def _load_schema(self) -> Dict[str, Any]:
        """스키마 정보 로드"""
        try:
            if os.path.exists(self.schema_path):
                with open(self.schema_path, 'r', encoding='utf-8') as f:
                    schema_data = json.load(f)
                logger.info(f"스키마 파일 로드 성공: {self.schema_path}")
                return schema_data
            else:
                logger.warning(f"스키마 파일이 존재하지 않음: {self.schema_path}")
                return {}
        except Exception as e:
            logger.error(f"스키마 파일 로드 오류: {e}")
            return {}
        
    def _test_db_connection(self):
        """데이터베이스 연결 테스트"""
        logger.info("SWDP 데이터베이스 연결 테스트")
        
        # Mock 모드인 경우 항상 연결 성공으로 처리
        if self.mock_mode:
            logger.info("Mock 모드로 실행 중: 데이터베이스 연결 테스트 생략")
            self.enabled = True
            return True
        
        # 실제 DB 연결 로직 (원래 코드 유지)
        # 설정 로드
        swdp_config = config.get_swdp_tool_config()
        self.enabled = swdp_config.get("enabled", False)
        self.db_uri = swdp_config.get("db_uri", "")
        self.engine = None
        
        # 데이터베이스 연결 시도
        if self.enabled and self.db_uri:
            try:
                self.engine = create_engine(self.db_uri)
                
                # 연결 테스트
                with self.engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                
                logger.info(f"SWDP 데이터베이스 연결 성공: {self.db_uri}")
                return True
            except Exception as e:
                logger.error(f"SWDP 데이터베이스 연결 오류: {e}")
                self.enabled = False
                self.engine = None
                return False
        
        logger.warning("SWDP 데이터베이스 연결 구성되지 않음")
        return False
    
    def _get_tables(self) -> List[str]:
        """
        SWDP 데이터베이스 테이블 목록 조회
        
        Returns:
            테이블 이름 목록
        """
        # Mock 모드인 경우 스키마 정보에서 테이블 목록 반환
        if self.mock_mode:
            if "tables" in self.schema_info:
                return [table["name"] for table in self.schema_info["tables"]]
            return []
            
        # 원래 DB 연결 로직
        if not self.engine:
            return []
        
        tables = []
        
        try:
            with self.engine.connect() as conn:
                # 데이터베이스 유형에 따른 테이블 목록 쿼리
                if 'sqlite' in self.db_uri:
                    tables_query = text("""
                        SELECT name FROM sqlite_master
                        WHERE type='table' AND name NOT LIKE 'sqlite_%'
                    """)
                elif 'mysql' in self.db_uri:
                    tables_query = text("""
                        SHOW TABLES
                    """)
                elif 'postgresql' in self.db_uri:
                    tables_query = text("""
                        SELECT tablename FROM pg_catalog.pg_tables
                        WHERE schemaname != 'pg_catalog' AND schemaname != 'information_schema'
                    """)
                else:
                    return []
                
                tables_result = conn.execute(tables_query)
                tables = [row[0] for row in tables_result]
        
        except SQLAlchemyError as e:
            logger.error(f"테이블 목록 조회 오류: {e}")
        
        return tables
    
    def _get_table_columns(self, table: str) -> List[Dict[str, Any]]:
        """
        테이블 컬럼 정보 조회
        
        Args:
            table: 테이블 이름
            
        Returns:
            컬럼 정보 목록
        """
        # Mock 모드인 경우 스키마 정보에서 컬럼 정보 반환
        if self.mock_mode:
            if "tables" in self.schema_info:
                for table_info in self.schema_info["tables"]:
                    if table_info["name"] == table:
                        return [
                            {
                                'name': col['name'],
                                'type': col['type'],
                                'nullable': not col.get('nullable', True),
                                'primary_key': col.get('primary_key', False),
                                'default': col.get('default', None)
                            }
                            for col in table_info["columns"]
                        ]
            return []
            
        # 원래 DB 연결 로직
        if not self.engine:
            return []
        
        columns = []
        
        try:
            with self.engine.connect() as conn:
                # 데이터베이스 유형에 따른 컬럼 정보 쿼리
                if 'sqlite' in self.db_uri:
                    columns_query = text(f"PRAGMA table_info('{table}')")
                    columns_result = conn.execute(columns_query)
                    
                    for row in columns_result:
                        columns.append({
                            'name': row.name,
                            'type': row.type,
                            'nullable': not row.notnull,
                            'primary_key': bool(row.pk),
                            'default': row.dflt_value
                        })
                        
                elif 'mysql' in self.db_uri:
                    columns_query = text(f"DESCRIBE `{table}`")
                    columns_result = conn.execute(columns_query)
                    
                    for row in columns_result:
                        columns.append({
                            'name': row.Field,
                            'type': row.Type,
                            'nullable': row.Null == 'YES',
                            'primary_key': row.Key == 'PRI',
                            'default': row.Default
                        })
                        
                elif 'postgresql' in self.db_uri:
                    columns_query = text(f"""
                        SELECT 
                            column_name, 
                            data_type, 
                            is_nullable, 
                            column_default,
                            (SELECT true FROM pg_constraint 
                             WHERE conrelid = '{table}'::regclass AND contype = 'p' 
                             AND array_position(conkey, a.attnum) IS NOT NULL) as is_primary
                        FROM information_schema.columns c
                        JOIN pg_attribute a ON a.attname = c.column_name
                        WHERE c.table_name = '{table}'
                        AND a.attrelid = '{table}'::regclass
                    """)
                    columns_result = conn.execute(columns_query)
                    
                    for row in columns_result:
                        columns.append({
                            'name': row.column_name,
                            'type': row.data_type,
                            'nullable': row.is_nullable == 'YES',
                            'primary_key': bool(row.is_primary),
                            'default': row.column_default
                        })
        
        except SQLAlchemyError as e:
            logger.error(f"컬럼 정보 조회 오류: {e}")
        
        return columns
    
    def _get_table_foreign_keys(self, table: str) -> List[Dict[str, str]]:
        """
        테이블 외래 키 정보 조회
        
        Args:
            table: 테이블 이름
            
        Returns:
            외래 키 정보 목록
        """
        # Mock 모드인 경우 스키마 정보에서 외래 키 정보 반환
        if self.mock_mode:
            if "tables" in self.schema_info:
                for table_info in self.schema_info["tables"]:
                    if table_info["name"] == table and "foreign_keys" in table_info:
                        return [
                            {
                                'column': fk['column'],
                                'referenced_table': fk['referenced_table'],
                                'referenced_column': fk['referenced_column']
                            }
                            for fk in table_info["foreign_keys"]
                        ]
            return []
            
        # 원래 DB 연결 로직
        if not self.engine:
            return []
        
        foreign_keys = []
        
        try:
            with self.engine.connect() as conn:
                if 'sqlite' in self.db_uri:
                    fk_query = text(f"PRAGMA foreign_key_list('{table}')")
                    fk_result = conn.execute(fk_query)
                    
                    for row in fk_result:
                        foreign_keys.append({
                            'column': row.from_,
                            'referenced_table': row.table,
                            'referenced_column': row.to
                        })
                        
                elif 'mysql' in self.db_uri:
                    fk_query = text(f"""
                        SELECT 
                            COLUMN_NAME, 
                            REFERENCED_TABLE_NAME,
                            REFERENCED_COLUMN_NAME
                        FROM information_schema.KEY_COLUMN_USAGE
                        WHERE TABLE_NAME = '{table}'
                        AND REFERENCED_TABLE_NAME IS NOT NULL
                    """)
                    fk_result = conn.execute(fk_query)
                    
                    for row in fk_result:
                        foreign_keys.append({
                            'column': row.COLUMN_NAME,
                            'referenced_table': row.REFERENCED_TABLE_NAME,
                            'referenced_column': row.REFERENCED_COLUMN_NAME
                        })
                        
                elif 'postgresql' in self.db_uri:
                    fk_query = text(f"""
                        SELECT
                            kcu.column_name,
                            ccu.table_name AS referenced_table,
                            ccu.column_name AS referenced_column
                        FROM information_schema.table_constraints AS tc
                        JOIN information_schema.key_column_usage AS kcu
                          ON tc.constraint_name = kcu.constraint_name
                        JOIN information_schema.constraint_column_usage AS ccu
                          ON ccu.constraint_name = tc.constraint_name
                        WHERE tc.constraint_type = 'FOREIGN KEY'
                        AND tc.table_name = '{table}'
                    """)
                    fk_result = conn.execute(fk_query)
                    
                    for row in fk_result:
                        foreign_keys.append({
                            'column': row.column_name,
                            'referenced_table': row.referenced_table,
                            'referenced_column': row.referenced_column
                        })
        
        except SQLAlchemyError as e:
            logger.error(f"외래 키 정보 조회 오류: {e}")
        
        return foreign_keys
    
    def _build_prompt(self, query: str, schema_info: str) -> str:
        """
        LLM 프롬프트 구성
        
        Args:
            query: 사용자 쿼리
            schema_info: 스키마 정보
            
        Returns:
            프롬프트 문자열
        """
        return f"""SWDP 데이터베이스 전문가로서 SWDP 관련 데이터베이스 쿼리를 도와드립니다.

{schema_info}

작업: 다음 질문에 대한 SQL 쿼리 작성 및 설명 또는 함수 호출
질문: {query}

가능한 함수 목록:
- get_user_by_single_id(single_id: str): Single ID로 사용자 정보 조회
- get_user_projects(single_id: str): 사용자가 속한 프로젝트 목록 조회
- get_build_by_id(build_request_id: str): 빌드 요청 ID로 빌드 정보 조회
- get_build_logs(build_request_id: str): 빌드 요청 ID로 빌드 로그 조회
- trigger_build(single_id: str, project_id?: int, project_code?: str, branch?: str, commit_id?: str, environment?: str, title?: str, description?: str): 새 빌드 트리거
- get_tr_by_code(tr_code: str): TR 코드로 TR 정보 조회
- get_tr_by_project(project_id: int, status?: str): 프로젝트 ID로 TR 목록 조회
- create_tr(single_id: str, project_id: int, title: str, description?: str, type?: str, priority?: str, target_release?: str): 새 TR 생성

이 작업에 대해:
1. 질문을 분석하고 SQL 쿼리를 작성하거나 적절한 함수 호출을 선택하세요.
2. 함수 호출이 필요한 경우 JSON 형식으로 함수 이름과 매개변수를 지정하세요: {"function": "함수명", "parameters": {"매개변수1": "값1", ...}}
3. SQL 쿼리가 필요한 경우 ```sql 코드 ``` 형식으로 쿼리를 작성하고 코드의 목적과 로직을 설명하세요.
"""
    
    def _get_schema_info_for_prompt(self) -> str:
        """스키마 정보를 프롬프트용으로 포맷팅"""
        if not self.schema_info:
            return "스키마 정보가 없습니다."
        
        schema_text = "## SWDP 데이터베이스 스키마\n\n"
        
        if "tables" in self.schema_info:
            for table in self.schema_info["tables"]:
                table_name = table["name"]
                table_desc = table.get("description", "")
                
                schema_text += f"### 테이블: {table_name}\n"
                schema_text += f"{table_desc}\n\n"
                
                # 컬럼 정보
                schema_text += "컬럼:\n"
                for column in table.get("columns", []):
                    col_name = column["name"]
                    col_type = column["type"]
                    col_desc = column.get("description", "")
                    primary_key = "PK" if column.get("primary_key", False) else ""
                    nullable = "NULL" if column.get("nullable", True) else "NOT NULL"
                    
                    schema_text += f"- {col_name} ({col_type}) {primary_key} {nullable}: {col_desc}\n"
                
                # 외래 키 정보
                if "foreign_keys" in table and table["foreign_keys"]:
                    schema_text += "\n외래 키:\n"
                    for fk in table["foreign_keys"]:
                        schema_text += f"- {fk['column']} -> {fk['referenced_table']}.{fk['referenced_column']}\n"
                
                # 샘플 데이터
                if "sample_data" in table and table["sample_data"]:
                    schema_text += "\n샘플 데이터:\n"
                    for idx, row in enumerate(table["sample_data"][:3], 1):  # 최대 3개 샘플만 표시
                        schema_text += f"{idx}. "
                        items = []
                        for k, v in row.items():
                            if k != "id":  # ID는 생략
                                items.append(f"{k}: {v}")
                        schema_text += ", ".join(items) + "\n"
                
                schema_text += "\n"
        
        return schema_text
    
    def execute_query(self, query: str) -> Dict[str, Any]:
        """
        자연어 쿼리 실행
        
        Args:
            query: 자연어 쿼리
            
        Returns:
            쿼리 결과
        """
        # 스키마 정보 준비
        schema_info = self._get_schema_info_for_prompt()
        
        # LLM 프롬프트 구성
        prompt = self._build_prompt(query, schema_info)
        
        # LLM 호출
        messages = [llm_service.format_user_message(prompt)]
        response = llm_service.generate(messages)
        
        # 함수 호출 여부 확인
        function_call = self._extract_function_call(response)
        if function_call:
            return self._handle_function_call(function_call)
        
        # SQL 쿼리 추출
        from src.utils.sql_utils import extract_sql_query
        sql_query = extract_sql_query(response)
        
        if not sql_query:
            logger.warning("SQL 쿼리 추출 실패")
            return {
                "result": response,
                "sql": None,
                "data": None,
                "error": "SQL 쿼리를 추출할 수 없습니다."
            }
        
        # Mock 모드일 경우 가상 결과 생성
        if self.mock_mode:
            mock_result = self._execute_mock_query(sql_query)
            return {
                "result": response,
                "sql": sql_query,
                "data": mock_result,
                "error": None
            }
        
        # 실제 DB 쿼리 실행
        try:
            query_result = self._execute_query(sql_query)
            return {
                "result": response,
                "sql": sql_query,
                "data": query_result,
                "error": None
            }
        except Exception as e:
            logger.error(f"쿼리 실행 오류: {e}")
            return {
                "result": response,
                "sql": sql_query,
                "data": None,
                "error": str(e)
            }
    
    def _execute_mock_query(self, query: str) -> List[Dict[str, Any]]:
        """
        Mock 데이터로 SQL 쿼리 실행 시뮬레이션
        
        Args:
            query: SQL 쿼리
            
        Returns:
            모의 결과 데이터
        """
        query = query.lower()
        logger.info(f"Mock 쿼리 실행: {query}")
        
        # 테이블 이름 추출 (FROM 이후의 첫 단어)
        table_name = None
        if "from" in query:
            from_parts = query.split("from")[1].strip().split()
            if from_parts:
                table_name = from_parts[0].strip('`;')
        
        # 테이블이 없으면 빈 결과 반환
        if not table_name or not self.schema_info or "tables" not in self.schema_info:
            return []
        
        # 테이블 정보 찾기
        table_info = None
        for table in self.schema_info["tables"]:
            if table["name"] == table_name:
                table_info = table
                break
        
        # 테이블 정보가 없으면 빈 결과 반환
        if not table_info or "sample_data" not in table_info:
            return []
        
        # 샘플 데이터 반환
        sample_data = table_info["sample_data"]
        
        # SELECT * 쿼리인 경우 모든 샘플 데이터 반환
        if "select *" in query:
            return sample_data
        
        # JOIN 쿼리인 경우 (간단한 구현)
        if "join" in query:
            # 조인 테이블 추출
            join_table_name = None
            if "join" in query:
                join_parts = query.split("join")[1].strip().split()
                if join_parts:
                    join_table_name = join_parts[0].strip('`;')
            
            # 조인 테이블 정보 찾기
            join_table_info = None
            for table in self.schema_info["tables"]:
                if table["name"] == join_table_name:
                    join_table_info = table
                    break
            
            # 조인 결과 시뮬레이션 (간단한 구현)
            if join_table_info and "sample_data" in join_table_info:
                join_data = []
                
                # 외래 키 정보 찾기
                foreign_keys = []
                if "foreign_keys" in table_info:
                    for fk in table_info["foreign_keys"]:
                        if fk["referenced_table"] == join_table_name:
                            foreign_keys.append((fk["column"], fk["referenced_column"]))
                
                # 외래 키가 없으면 빈 결과 반환
                if not foreign_keys:
                    return []
                
                # 외래 키로 조인
                for row in sample_data:
                    for join_row in join_table_info["sample_data"]:
                        for fk_column, ref_column in foreign_keys:
                            if row.get(fk_column) == join_row.get(ref_column):
                                # 조인 결과 생성
                                combined_row = {**row}
                                for k, v in join_row.items():
                                    combined_row[f"{join_table_name}_{k}"] = v
                                join_data.append(combined_row)
                                break
                
                return join_data
        
        # WHERE 조건이 있는 경우 필터링 (간단한 구현)
        if "where" in query:
            where_clause = query.split("where")[1].strip()
            
            # ID로 검색하는 경우
            id_match = re.search(r'id\s*=\s*(\d+)', where_clause)
            if id_match:
                id_value = int(id_match.group(1))
                return [row for row in sample_data if row.get("id") == id_value]
            
            # 상태로 검색하는 경우
            status_match = re.search(r'status\s*=\s*[\'"]([^\'"]+)[\'"]', where_clause)
            if status_match:
                status_value = status_match.group(1)
                return [row for row in sample_data if row.get("status") == status_value]
        
        # 기본적으로 모든 샘플 데이터 반환
        return sample_data
        
    def _execute_query(self, query: str) -> Any:
        """
        SQL 쿼리 실행
        
        Args:
            query: SQL 쿼리
            
        Returns:
            쿼리 실행 결과
        """
        if not self.engine:
            return []
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query))
                
                # SELECT 쿼리인 경우 결과 반환
                if result.returns_rows:
                    column_names = result.keys()
                    data = []
                    for row in result:
                        row_dict = {}
                        for i, column in enumerate(column_names):
                            value = row[i]
                            # 직렬화 가능한 형태로 변환
                            if isinstance(value, (int, float, str, bool, type(None))):
                                row_dict[column] = value
                            else:
                                row_dict[column] = str(value)
                        data.append(row_dict)
                    return data
                else:
                    # INSERT, UPDATE, DELETE 등의 경우 영향 받은 행 수 반환
                    return result.rowcount
                
        except SQLAlchemyError as e:
            logger.error(f"쿼리 실행 오류: {e}")
            raise
    
    def _extract_function_call(self, response: str) -> Optional[Dict[str, Any]]:
        """
        LLM 응답에서 함수 호출 추출
        
        Args:
            response: LLM 응답
            
        Returns:
            함수 호출 정보
        """
        try:
            # JSON 형식의 함수 호출 추출
            function_call_match = re.search(r'\{[\s\S]*?"function"[\s\S]*?\}', response)
            if function_call_match:
                function_call_str = function_call_match.group(0)
                function_call = json.loads(function_call_str)
                
                if "function" in function_call and "parameters" in function_call:
                    return function_call
            
            return None
        except Exception as e:
            logger.error(f"함수 호출 추출 오류: {e}")
            return None
    
    def _handle_function_call(self, function_call: Dict[str, Any]) -> Dict[str, Any]:
        """
        함수 호출 처리
        
        Args:
            function_call: 함수 호출 정보
            
        Returns:
            함수 실행 결과
        """
        function_name = function_call.get("function")
        parameters = function_call.get("parameters", {})
        
        logger.info(f"함수 호출: {function_name}, 매개변수: {parameters}")
        
        if not function_name:
            return {"error": "함수 이름이 지정되지 않았습니다."}
        
        # 사용자 관련 함수
        if function_name == "get_user_by_single_id":
            single_id = parameters.get("single_id")
            if not single_id:
                return {"error": "single_id 매개변수가 필요합니다."}
            
            from src.agents.swdp_rpc_api import SWDPRPCAPI
            swdp_rpc_api = SWDPRPCAPI()
            return swdp_rpc_api.get_user_by_single_id(single_id)
        
        elif function_name == "get_user_projects":
            single_id = parameters.get("single_id")
            if not single_id:
                return {"error": "single_id 매개변수가 필요합니다."}
            
            from src.agents.swdp_rpc_api import SWDPRPCAPI
            swdp_rpc_api = SWDPRPCAPI()
            return swdp_rpc_api.get_user_projects(single_id)
        
        # 빌드 관련 함수
        elif function_name == "get_build_by_id":
            build_request_id = parameters.get("build_request_id")
            if not build_request_id:
                return {"error": "build_request_id 매개변수가 필요합니다."}
            
            from src.agents.swdp_rpc_api import SWDPRPCAPI
            swdp_rpc_api = SWDPRPCAPI()
            return swdp_rpc_api.get_build_by_id(build_request_id)
        
        elif function_name == "get_build_logs":
            build_request_id = parameters.get("build_request_id")
            if not build_request_id:
                return {"error": "build_request_id 매개변수가 필요합니다."}
            
            from src.agents.swdp_rpc_api import SWDPRPCAPI
            swdp_rpc_api = SWDPRPCAPI()
            return swdp_rpc_api.get_build_logs(build_request_id)
        
        elif function_name == "trigger_build":
            single_id = parameters.get("single_id")
            if not single_id:
                return {"error": "single_id 매개변수가 필요합니다."}
            
            project_id = parameters.get("project_id")
            project_code = parameters.get("project_code")
            
            if not project_id and not project_code:
                return {"error": "project_id 또는 project_code 매개변수가 필요합니다."}
            
            from src.agents.swdp_rpc_api import SWDPRPCAPI
            swdp_rpc_api = SWDPRPCAPI()
            return swdp_rpc_api.trigger_build(
                single_id=single_id,
                project_id=project_id,
                project_code=project_code,
                branch=parameters.get("branch"),
                commit_id=parameters.get("commit_id"),
                environment=parameters.get("environment"),
                title=parameters.get("title"),
                description=parameters.get("description")
            )
        
        # TR 관련 함수
        elif function_name == "get_tr_by_code":
            tr_code = parameters.get("tr_code")
            if not tr_code:
                return {"error": "tr_code 매개변수가 필요합니다."}
            
            from src.agents.swdp_rpc_api import SWDPRPCAPI
            swdp_rpc_api = SWDPRPCAPI()
            return swdp_rpc_api.get_tr_by_code(tr_code)
        
        elif function_name == "get_tr_by_project":
            project_id = parameters.get("project_id")
            if not project_id:
                return {"error": "project_id 매개변수가 필요합니다."}
            
            from src.agents.swdp_rpc_api import SWDPRPCAPI
            swdp_rpc_api = SWDPRPCAPI()
            return swdp_rpc_api.get_tr_by_project(project_id, parameters.get("status"))
        
        elif function_name == "create_tr":
            single_id = parameters.get("single_id")
            project_id = parameters.get("project_id")
            title = parameters.get("title")
            
            if not single_id or not project_id or not title:
                return {"error": "single_id, project_id, title 매개변수가 필요합니다."}
            
            from src.agents.swdp_rpc_api import SWDPRPCAPI
            swdp_rpc_api = SWDPRPCAPI()
            return swdp_rpc_api.create_tr(
                single_id=single_id,
                project_id=project_id,
                title=title,
                description=parameters.get("description"),
                type=parameters.get("type"),
                priority=parameters.get("priority"),
                target_release=parameters.get("target_release")
            )
        
        return {"error": f"알 수 없는 함수: {function_name}"}
    
    def _generate_random_string(self, length: int) -> str:
        """랜덤 문자열 생성"""
        import random
        import string
        
        chars = string.ascii_uppercase + string.digits
        return ''.join(random.choice(chars) for _ in range(length))