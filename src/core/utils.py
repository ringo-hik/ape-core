"""
유틸리티 함수 모듈

이 모듈은 여러 에이전트에서 공통으로 사용되는 유틸리티 함수들을 제공합니다.
"""

import re
from typing import Dict, Any, Optional

def extract_sql_query(text: str) -> Optional[str]:
    """
    텍스트에서 SQL 쿼리 추출
    
    Args:
        text: SQL 쿼리를 포함한 텍스트
        
    Returns:
        추출된 SQL 쿼리 (없으면 None)
    """
    # SQL 코드 블록 찾기 (```sql ... ```)
    sql_matches = re.findall(r"```(?:sql)?\s*(.*?)```", text, re.DOTALL)
    
    if sql_matches:
        sql_query = sql_matches[0].strip()
        return sql_query
    
    # 코드 블록이 없는 경우 전체 텍스트에서 SQL처럼 보이는 부분 추출
    sql_keywords = ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP"]
    
    for line in text.split('\n'):
        for keyword in sql_keywords:
            if line.strip().upper().startswith(keyword):
                return line.strip()
    
    return None

def format_response(agent_id: str, content: str, model_id: str) -> Dict[str, Any]:
    """
    최종 응답 포맷팅
    
    Args:
        agent_id: 에이전트 ID
        content: 응답 내용
        model_id: 사용된 모델 ID
        
    Returns:
        포맷팅된 응답 객체
    """
    return {
        "content": content,
        "model": model_id,
        "agent_id": agent_id
    }