"""
SQL 관련 유틸리티 함수

SQL 쿼리 추출, 포맷팅, 결과 처리 등을 위한 공통 함수 제공
"""

import re
from typing import Optional, Dict, Any, List

def extract_sql_query(text: str, check_sql_keywords: bool = True) -> Optional[str]:
    """
    텍스트에서 SQL 쿼리 추출
    
    Args:
        text: SQL 쿼리를 포함한 텍스트
        check_sql_keywords: SQL 키워드로 시작하는 라인 검색 여부
            
    Returns:
        추출된 SQL 쿼리 (없으면 None)
    """
    # SQL 코드 블록 찾기 (sql 태그 포함)
    sql_pattern = re.compile(r"```sql\s*(.*?)\s*```", re.DOTALL)
    match = sql_pattern.search(text)
    
    if match:
        return match.group(1).strip()
    
    # 일반 코드 블록 찾기
    code_pattern = re.compile(r"```\s*(.*?)\s*```", re.DOTALL)
    match = code_pattern.search(text)
    
    if match:
        return match.group(1).strip()
    
    # SQL 키워드로 시작하는 라인 찾기
    if check_sql_keywords:
        sql_keywords = ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP"]
        
        for line in text.split('\n'):
            for keyword in sql_keywords:
                if line.strip().upper().startswith(keyword):
                    return line.strip()
    
    return None

def format_query_result(result: Any, sql_query: str, llm_response: str, agent_type: str) -> str:
    """
    쿼리 결과 포맷팅
    
    Args:
        result: 쿼리 실행 결과
        sql_query: 실행된 SQL 쿼리
        llm_response: LLM 응답 전체
        agent_type: 에이전트 유형
            
    Returns:
        포맷팅된 결과 문자열
    """
    response = f"## 실행된 쿼리\n```sql\n{sql_query}\n```\n\n"
    
    # 결과가 리스트 또는 딕셔너리인 경우 (SELECT 쿼리)
    if isinstance(result, (list, dict)) and result:
        # 데이터가 있는 경우
        if isinstance(result, list) and len(result) > 0:
            # 컬럼 이름 추출
            columns = result[0].keys() if result and isinstance(result[0], dict) else []
            
            # 마크다운 테이블 헤더
            response += "## 쿼리 결과\n\n"
            response += "| " + " | ".join(columns) + " |\n"
            response += "| " + " | ".join(["---"] * len(columns)) + " |\n"
            
            # 각 행을 마크다운 테이블 형식으로 추가
            for row in result:
                values = []
                for col in columns:
                    value = row.get(col, "")
                    # 문자열이 아닌 경우 변환
                    if not isinstance(value, str):
                        if value is None:
                            value = "NULL"
                        else:
                            value = str(value)
                    # 파이프 문자 이스케이프
                    value = value.replace("|", "\\|")
                    values.append(value)
                
                response += "| " + " | ".join(values) + " |\n"
            
            # 결과 요약 추가
            response += f"\n총 {len(result)}개의 행이 반환되었습니다.\n\n"
            
        # 결과가 없는 경우
        else:
            response += "## 쿼리 결과\n\n결과가 없습니다.\n\n"
    
    # DML 쿼리 결과 (영향 받은 행 수)
    elif isinstance(result, int):
        response += f"## 쿼리 결과\n\n{result}개의 행이 영향을 받았습니다.\n\n"
        
    # 기타 결과
    else:
        response += f"## 쿼리 결과\n\n{str(result)}\n\n"
    
    # 쿼리와 결과 분석 추가 (LLM 응답에서 SQL 코드 블록 이후 부분 추출)
    analysis = ""
    sql_blocks = re.findall(r"```sql.*?```", llm_response, re.DOTALL)
    
    if sql_blocks:
        # 마지막 SQL 블록 이후의 텍스트 추출
        last_sql_block_end = llm_response.rfind(sql_blocks[-1]) + len(sql_blocks[-1])
        if last_sql_block_end < len(llm_response):
            analysis = llm_response[last_sql_block_end:].strip()
    
    if analysis:
        response += "## 분석\n\n" + analysis
        
    return response