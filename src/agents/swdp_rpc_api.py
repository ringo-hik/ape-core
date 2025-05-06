"""
SWDP RPC API - 직접 쿼리 실행을 위한 API 모듈

이 모듈은 SWDP에 대한 직접적인 쿼리 실행 API를 제공합니다.
자연어 에이전트를 통한 처리보다 정확성이 요구되는 작업을 위한 RPC 스타일 API입니다.
"""

import logging
import json
import re
import os
from typing import Dict, Any, List, Tuple, Optional, Union
from datetime import datetime

from src.agents.swdp_db_agent import SWDPDBAgent

# 로깅 설정
logger = logging.getLogger("swdp_rpc_api")

class SWDPRPCAPI:
    """SWDP RPC API 클래스"""
    
    def __init__(self):
        """SWDP RPC API 초기화"""
        self.db_agent = SWDPDBAgent()
        self.schema_info = self.db_agent.schema_info
        self.mock_mode = True
        logger.info(f"SWDP RPC API 초기화 완료 (Mock 모드: {self.mock_mode})")
    
    # 사용자 관련 메서드
    def get_user_by_single_id(self, single_id: str) -> Dict[str, Any]:
        """
        Single ID로 사용자 정보 조회
        
        Args:
            single_id: 사용자 단일 ID (외부 시스템용)
            
        Returns:
            사용자 정보
        """
        if not single_id:
            return {"error": "Single ID는 필수 파라미터입니다."}
        
        # SQL 쿼리 구성
        query = f"SELECT * FROM users WHERE single_id = '{single_id}'"
        
        # Mock 모드인 경우
        if self.mock_mode:
            users_table = None
            for table in self.schema_info["tables"]:
                if table["name"] == "users":
                    users_table = table
                    break
            
            if not users_table or "sample_data" not in users_table:
                return {"error": "사용자 데이터를 찾을 수 없습니다."}
            
            user_data = None
            for user in users_table["sample_data"]:
                if user.get("single_id") == single_id:
                    user_data = user
                    break
            
            if not user_data:
                return {"error": f"Single ID '{single_id}'를 가진 사용자를 찾을 수 없습니다."}
            
            # 비밀번호 정보 제거
            user_data_clean = {k: v for k, v in user_data.items() if k != "password_hash"}
            
            return {
                "success": True,
                "data": user_data_clean
            }
        
        # 실제 DB 쿼리 실행
        try:
            result = self.db_agent._execute_query(query)
            
            if not result or len(result) == 0:
                return {"error": f"Single ID '{single_id}'를 가진 사용자를 찾을 수 없습니다."}
            
            # 비밀번호 정보 제거
            user_data = result[0]
            user_data_clean = {k: v for k, v in user_data.items() if k != "password_hash"}
            
            return {
                "success": True,
                "data": user_data_clean
            }
        except Exception as e:
            logger.error(f"사용자 정보 조회 오류: {e}")
            return {"error": f"사용자 정보 조회 오류: {str(e)}"}
    
    def get_user_projects(self, single_id: str) -> Dict[str, Any]:
        """
        사용자가 속한 프로젝트 목록 조회
        
        Args:
            single_id: 사용자 단일 ID (외부 시스템용)
            
        Returns:
            프로젝트 목록
        """
        if not single_id:
            return {"error": "Single ID는 필수 파라미터입니다."}
        
        # 사용자 정보 조회
        user_info = self.get_user_by_single_id(single_id)
        if "error" in user_info:
            return user_info
        
        user_id = user_info["data"]["id"]
        
        # SQL 쿼리 구성
        query = f"""
        SELECT p.*, upr.role as user_role
        FROM projects p
        JOIN user_project_roles upr ON p.id = upr.project_id
        WHERE upr.user_id = {user_id}
        """
        
        # Mock 모드인 경우
        if self.mock_mode:
            # 프로젝트 테이블 정보
            projects_table = None
            for table in self.schema_info["tables"]:
                if table["name"] == "projects":
                    projects_table = table
                    break
            
            # 사용자 프로젝트 역할 테이블 정보
            user_project_roles_table = None
            for table in self.schema_info["tables"]:
                if table["name"] == "user_project_roles":
                    user_project_roles_table = table
                    break
            
            if (not projects_table or "sample_data" not in projects_table or
                not user_project_roles_table or "sample_data" not in user_project_roles_table):
                return {"error": "프로젝트 또는 사용자 역할 데이터를 찾을 수 없습니다."}
            
            # 사용자의 프로젝트 역할 조회
            user_project_roles = []
            for role in user_project_roles_table["sample_data"]:
                if role.get("user_id") == user_id:
                    user_project_roles.append(role)
            
            # 사용자의 프로젝트 조회
            projects = []
            for role in user_project_roles:
                project_id = role.get("project_id")
                project_role = role.get("role")
                
                for project in projects_table["sample_data"]:
                    if project.get("id") == project_id:
                        project_data = project.copy()
                        project_data["user_role"] = project_role
                        projects.append(project_data)
                        break
            
            return {
                "success": True,
                "data": projects
            }
        
        # 실제 DB 쿼리 실행
        try:
            result = self.db_agent._execute_query(query)
            
            return {
                "success": True,
                "data": result
            }
        except Exception as e:
            logger.error(f"사용자 프로젝트 조회 오류: {e}")
            return {"error": f"사용자 프로젝트 조회 오류: {str(e)}"}
    
    # 빌드 관련 메서드
    def get_build_by_id(self, build_request_id: str) -> Dict[str, Any]:
        """
        빌드 요청 ID로 빌드 정보 조회
        
        Args:
            build_request_id: 빌드 요청 고유 ID (외부 참조용)
            
        Returns:
            빌드 정보
        """
        if not build_request_id:
            return {"error": "빌드 요청 ID는 필수 파라미터입니다."}
        
        # SQL 쿼리 구성
        query = f"SELECT * FROM build_requests WHERE build_request_id = '{build_request_id}'"
        
        # Mock 모드인 경우
        if self.mock_mode:
            builds_table = None
            for table in self.schema_info["tables"]:
                if table["name"] == "build_requests":
                    builds_table = table
                    break
            
            if not builds_table or "sample_data" not in builds_table:
                return {"error": "빌드 데이터를 찾을 수 없습니다."}
            
            build_data = None
            for build in builds_table["sample_data"]:
                if build.get("build_request_id") == build_request_id:
                    build_data = build
                    break
            
            if not build_data:
                return {"error": f"빌드 요청 ID '{build_request_id}'를 가진 빌드를 찾을 수 없습니다."}
            
            return {
                "success": True,
                "data": build_data
            }
        
        # 실제 DB 쿼리 실행
        try:
            result = self.db_agent._execute_query(query)
            
            if not result or len(result) == 0:
                return {"error": f"빌드 요청 ID '{build_request_id}'를 가진 빌드를 찾을 수 없습니다."}
            
            return {
                "success": True,
                "data": result[0]
            }
        except Exception as e:
            logger.error(f"빌드 정보 조회 오류: {e}")
            return {"error": f"빌드 정보 조회 오류: {str(e)}"}
    
    def get_build_logs(self, build_request_id: str) -> Dict[str, Any]:
        """
        빌드 요청 ID로 빌드 로그 조회
        
        Args:
            build_request_id: 빌드 요청 고유 ID (외부 참조용)
            
        Returns:
            빌드 로그 목록
        """
        if not build_request_id:
            return {"error": "빌드 요청 ID는 필수 파라미터입니다."}
        
        # 빌드 정보 조회
        build_info = self.get_build_by_id(build_request_id)
        if "error" in build_info:
            return build_info
        
        build_id = build_info["data"]["id"]
        
        # SQL 쿼리 구성
        query = f"""
        SELECT * FROM build_logs 
        WHERE build_id = {build_id}
        ORDER BY timestamp ASC
        """
        
        # Mock 모드인 경우
        if self.mock_mode:
            build_logs_table = None
            for table in self.schema_info["tables"]:
                if table["name"] == "build_logs":
                    build_logs_table = table
                    break
            
            if not build_logs_table or "sample_data" not in build_logs_table:
                return {"error": "빌드 로그 데이터를 찾을 수 없습니다."}
            
            logs = []
            for log in build_logs_table["sample_data"]:
                if log.get("build_id") == build_id:
                    logs.append(log)
            
            # 타임스탬프로 정렬
            logs.sort(key=lambda x: x.get("timestamp", ""))
            
            return {
                "success": True,
                "data": logs
            }
        
        # 실제 DB 쿼리 실행
        try:
            result = self.db_agent._execute_query(query)
            
            return {
                "success": True,
                "data": result
            }
        except Exception as e:
            logger.error(f"빌드 로그 조회 오류: {e}")
            return {"error": f"빌드 로그 조회 오류: {str(e)}"}
    
    def trigger_build(self, single_id: str, project_id: Optional[int] = None, 
                      project_code: Optional[str] = None, 
                      branch: str = "main", 
                      commit_id: Optional[str] = None, 
                      environment: str = "DEV",
                      title: Optional[str] = None,
                      description: Optional[str] = None) -> Dict[str, Any]:
        """
        새 빌드 트리거
        
        Args:
            single_id: 사용자 단일 ID (외부 시스템용)
            project_id: 프로젝트 ID (내부용, 선택적)
            project_code: 프로젝트 코드 (선택적, project_id가 없는 경우 필수)
            branch: 소스 브랜치 (기본값: main)
            commit_id: 커밋 해시 (선택적, 최신 커밋 사용)
            environment: 빌드 환경 (기본값: DEV)
            title: 빌드 제목 (선택적)
            description: 빌드 설명 (선택적)
            
        Returns:
            생성된 빌드 정보
        """
        if not single_id:
            return {"error": "사용자 ID는 필수 파라미터입니다."}
        
        if not project_id and not project_code:
            return {"error": "프로젝트 ID 또는 프로젝트 코드는 필수 파라미터입니다."}
        
        if not environment:
            environment = "DEV"
        
        if environment not in ["DEV", "TEST", "STAGE", "PROD"]:
            return {"error": "유효하지 않은 환경입니다. DEV, TEST, STAGE, PROD 중 하나여야 합니다."}
        
        # 사용자 정보 조회
        user_info = self.get_user_by_single_id(single_id)
        if "error" in user_info:
            return user_info
        
        user_id = user_info["data"]["id"]
        
        # 프로젝트 정보 조회
        if not project_id and project_code:
            # 프로젝트 코드로 프로젝트 ID 조회
            if self.mock_mode:
                projects_table = None
                for table in self.schema_info["tables"]:
                    if table["name"] == "projects":
                        projects_table = table
                        break
                
                if not projects_table or "sample_data" not in projects_table:
                    return {"error": "프로젝트 데이터를 찾을 수 없습니다."}
                
                project_data = None
                for project in projects_table["sample_data"]:
                    if project.get("code") == project_code:
                        project_data = project
                        break
                
                if not project_data:
                    return {"error": f"프로젝트 코드 '{project_code}'를 가진 프로젝트를 찾을 수 없습니다."}
                
                project_id = project_data["id"]
            else:
                query = f"SELECT id FROM projects WHERE code = '{project_code}'"
                try:
                    result = self.db_agent._execute_query(query)
                    
                    if not result or len(result) == 0:
                        return {"error": f"프로젝트 코드 '{project_code}'를 가진 프로젝트를 찾을 수 없습니다."}
                    
                    project_id = result[0]["id"]
                except Exception as e:
                    logger.error(f"프로젝트 정보 조회 오류: {e}")
                    return {"error": f"프로젝트 정보 조회 오류: {str(e)}"}
        
        # 사용자가 프로젝트에 접근 권한이 있는지 확인
        if self.mock_mode:
            user_project_roles_table = None
            for table in self.schema_info["tables"]:
                if table["name"] == "user_project_roles":
                    user_project_roles_table = table
                    break
            
            if not user_project_roles_table or "sample_data" not in user_project_roles_table:
                return {"error": "사용자 프로젝트 역할 데이터를 찾을 수 없습니다."}
            
            has_access = False
            for role in user_project_roles_table["sample_data"]:
                if role.get("user_id") == user_id and role.get("project_id") == project_id:
                    # OWNER, ADMIN, DEVELOPER 역할만 빌드 가능
                    if role.get("role") in ["OWNER", "ADMIN", "DEVELOPER"]:
                        has_access = True
                        break
            
            if not has_access:
                return {"error": "해당 프로젝트에 대한 빌드 권한이 없습니다."}
        else:
            query = f"""
            SELECT role FROM user_project_roles 
            WHERE user_id = {user_id} AND project_id = {project_id}
            """
            try:
                result = self.db_agent._execute_query(query)
                
                if not result or len(result) == 0:
                    return {"error": "해당 프로젝트에 대한 접근 권한이 없습니다."}
                
                role = result[0]["role"]
                if role not in ["OWNER", "ADMIN", "DEVELOPER"]:
                    return {"error": "해당 프로젝트에 대한 빌드 권한이 없습니다."}
            except Exception as e:
                logger.error(f"사용자 프로젝트 역할 조회 오류: {e}")
                return {"error": f"사용자 프로젝트 역할 조회 오류: {str(e)}"}
        
        # 빌드 요청 ID 생성
        build_request_id = f"BR-{datetime.now().strftime('%Y%m%d')}-{self._generate_random_string(6)}"
        
        # 커밋 ID가 없는 경우 랜덤 생성
        if not commit_id:
            commit_id = self._generate_random_string(10)
        
        # 빌드 제목이 없는 경우 기본값 설정
        if not title:
            # 프로젝트 정보 조회
            if self.mock_mode:
                projects_table = None
                for table in self.schema_info["tables"]:
                    if table["name"] == "projects":
                        projects_table = table
                        break
                
                project_name = "Unknown Project"
                for project in projects_table["sample_data"]:
                    if project.get("id") == project_id:
                        project_name = project.get("name")
                        break
                
                title = f"{project_name} - {branch} 브랜치 빌드"
            else:
                query = f"SELECT name FROM projects WHERE id = {project_id}"
                try:
                    result = self.db_agent._execute_query(query)
                    
                    if result and len(result) > 0:
                        project_name = result[0]["name"]
                        title = f"{project_name} - {branch} 브랜치 빌드"
                    else:
                        title = f"프로젝트 {project_id} - {branch} 브랜치 빌드"
                except Exception as e:
                    logger.error(f"프로젝트 정보 조회 오류: {e}")
                    title = f"프로젝트 {project_id} - {branch} 브랜치 빌드"
        
        # 빌드 설명이 없는 경우 기본값 설정
        if not description:
            description = f"{branch} 브랜치의 {commit_id} 커밋에 대한 {environment} 환경 빌드"
        
        # Mock 모드인 경우 모의 데이터 생성
        if self.mock_mode:
            builds_table = None
            for table in self.schema_info["tables"]:
                if table["name"] == "build_requests":
                    builds_table = table
                    break
            
            if not builds_table or "sample_data" not in builds_table:
                return {"error": "빌드 요청 테이블을 찾을 수 없습니다."}
            
            # 새 빌드 ID 계산
            max_id = 0
            for build in builds_table["sample_data"]:
                if build.get("id", 0) > max_id:
                    max_id = build.get("id", 0)
            
            new_build_id = max_id + 1
            
            # 새 빌드 데이터 생성
            new_build = {
                "id": new_build_id,
                "build_request_id": build_request_id,
                "project_id": project_id,
                "title": title,
                "description": description,
                "branch": branch,
                "commit_id": commit_id,
                "status": "PENDING",
                "environment": environment,
                "requested_by": user_id,
                "approved_by": None,
                "started_at": None,
                "finished_at": None,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # 빌드 데이터 추가
            builds_table["sample_data"].append(new_build)
            
            return {
                "success": True,
                "message": "빌드가 성공적으로 트리거되었습니다.",
                "data": new_build
            }
        else:
            # SQL 쿼리 구성
            query = f"""
            INSERT INTO build_requests 
            (build_request_id, project_id, title, description, branch, commit_id, 
            status, environment, requested_by, created_at, updated_at)
            VALUES 
            ('{build_request_id}', {project_id}, '{title}', '{description}', '{branch}', '{commit_id}',
            'PENDING', '{environment}', {user_id}, NOW(), NOW())
            """
            
            try:
                self.db_agent._execute_query(query)
                
                # 생성된 빌드 정보 조회
                query = f"SELECT * FROM build_requests WHERE build_request_id = '{build_request_id}'"
                result = self.db_agent._execute_query(query)
                
                if not result or len(result) == 0:
                    return {"error": "빌드 생성 후 조회 오류가 발생했습니다."}
                
                return {
                    "success": True,
                    "message": "빌드가 성공적으로 트리거되었습니다.",
                    "data": result[0]
                }
            except Exception as e:
                logger.error(f"빌드 트리거 오류: {e}")
                return {"error": f"빌드 트리거 오류: {str(e)}"}
    
    # TR 관련 메서드
    def get_tr_by_code(self, tr_code: str) -> Dict[str, Any]:
        """
        TR 코드로 TR 정보 조회
        
        Args:
            tr_code: TR 코드 (외부 참조용)
            
        Returns:
            TR 정보
        """
        if not tr_code:
            return {"error": "TR 코드는 필수 파라미터입니다."}
        
        # SQL 쿼리 구성
        query = f"SELECT * FROM tr_data WHERE tr_code = '{tr_code}'"
        
        # Mock 모드인 경우
        if self.mock_mode:
            tr_table = None
            for table in self.schema_info["tables"]:
                if table["name"] == "tr_data":
                    tr_table = table
                    break
            
            if not tr_table or "sample_data" not in tr_table:
                return {"error": "TR 데이터를 찾을 수 없습니다."}
            
            tr_data = None
            for tr in tr_table["sample_data"]:
                if tr.get("tr_code") == tr_code:
                    tr_data = tr
                    break
            
            if not tr_data:
                return {"error": f"TR 코드 '{tr_code}'를 가진 TR을 찾을 수 없습니다."}
            
            return {
                "success": True,
                "data": tr_data
            }
        
        # 실제 DB 쿼리 실행
        try:
            result = self.db_agent._execute_query(query)
            
            if not result or len(result) == 0:
                return {"error": f"TR 코드 '{tr_code}'를 가진 TR을 찾을 수 없습니다."}
            
            return {
                "success": True,
                "data": result[0]
            }
        except Exception as e:
            logger.error(f"TR 정보 조회 오류: {e}")
            return {"error": f"TR 정보 조회 오류: {str(e)}"}
    
    def get_tr_by_project(self, project_id: int, status: Optional[str] = None) -> Dict[str, Any]:
        """
        프로젝트 ID로 TR 목록 조회
        
        Args:
            project_id: 프로젝트 ID
            status: TR 상태 필터 (선택적)
            
        Returns:
            TR 목록
        """
        if not project_id:
            return {"error": "프로젝트 ID는 필수 파라미터입니다."}
        
        # SQL 쿼리 구성
        query = f"SELECT * FROM tr_data WHERE project_id = {project_id}"
        
        if status:
            valid_statuses = ["DRAFT", "SUBMITTED", "REVIEW", "APPROVED", "REJECTED"]
            if status not in valid_statuses:
                return {"error": f"유효하지 않은 상태입니다. {', '.join(valid_statuses)} 중 하나여야 합니다."}
            
            query += f" AND status = '{status}'"
        
        # Mock 모드인 경우
        if self.mock_mode:
            tr_table = None
            for table in self.schema_info["tables"]:
                if table["name"] == "tr_data":
                    tr_table = table
                    break
            
            if not tr_table or "sample_data" not in tr_table:
                return {"error": "TR 데이터를 찾을 수 없습니다."}
            
            trs = []
            for tr in tr_table["sample_data"]:
                if tr.get("project_id") == project_id:
                    if status and tr.get("status") != status:
                        continue
                    trs.append(tr)
            
            return {
                "success": True,
                "data": trs
            }
        
        # 실제 DB 쿼리 실행
        try:
            result = self.db_agent._execute_query(query)
            
            return {
                "success": True,
                "data": result
            }
        except Exception as e:
            logger.error(f"TR 목록 조회 오류: {e}")
            return {"error": f"TR 목록 조회 오류: {str(e)}"}
    
    def create_tr(self, single_id: str, project_id: int, title: str, description: Optional[str] = None,
                  type: str = "FEATURE", priority: str = "MEDIUM", 
                  target_release: Optional[str] = None) -> Dict[str, Any]:
        """
        새 TR 생성
        
        Args:
            single_id: 사용자 단일 ID (외부 시스템용)
            project_id: 프로젝트 ID
            title: TR 제목
            description: TR 설명 (선택적)
            type: TR 유형 (기본값: FEATURE)
            priority: 우선순위 (기본값: MEDIUM)
            target_release: 목표 릴리스 버전 (선택적)
            
        Returns:
            생성된 TR 정보
        """
        if not single_id:
            return {"error": "사용자 ID는 필수 파라미터입니다."}
        
        if not project_id:
            return {"error": "프로젝트 ID는 필수 파라미터입니다."}
        
        if not title:
            return {"error": "TR 제목은 필수 파라미터입니다."}
        
        # 유형 검증
        valid_types = ["BUG_FIX", "FEATURE", "ENHANCEMENT", "SECURITY"]
        if type not in valid_types:
            return {"error": f"유효하지 않은 유형입니다. {', '.join(valid_types)} 중 하나여야 합니다."}
        
        # 우선순위 검증
        valid_priorities = ["HIGH", "MEDIUM", "LOW"]
        if priority not in valid_priorities:
            return {"error": f"유효하지 않은 우선순위입니다. {', '.join(valid_priorities)} 중 하나여야 합니다."}
        
        # 사용자 정보 조회
        user_info = self.get_user_by_single_id(single_id)
        if "error" in user_info:
            return user_info
        
        user_id = user_info["data"]["id"]
        
        # 사용자가 프로젝트에 접근 권한이 있는지 확인
        if self.mock_mode:
            user_project_roles_table = None
            for table in self.schema_info["tables"]:
                if table["name"] == "user_project_roles":
                    user_project_roles_table = table
                    break
            
            if not user_project_roles_table or "sample_data" not in user_project_roles_table:
                return {"error": "사용자 프로젝트 역할 데이터를 찾을 수 없습니다."}
            
            has_access = False
            for role in user_project_roles_table["sample_data"]:
                if role.get("user_id") == user_id and role.get("project_id") == project_id:
                    has_access = True
                    break
            
            if not has_access:
                return {"error": "해당 프로젝트에 대한 접근 권한이 없습니다."}
        else:
            query = f"""
            SELECT * FROM user_project_roles 
            WHERE user_id = {user_id} AND project_id = {project_id}
            """
            try:
                result = self.db_agent._execute_query(query)
                
                if not result or len(result) == 0:
                    return {"error": "해당 프로젝트에 대한 접근 권한이 없습니다."}
            except Exception as e:
                logger.error(f"사용자 프로젝트 역할 조회 오류: {e}")
                return {"error": f"사용자 프로젝트 역할 조회 오류: {str(e)}"}
        
        # TR 코드 생성
        tr_code = f"TR-{datetime.now().strftime('%Y')}-{self._generate_random_string(3)}"
        
        # Mock 모드인 경우 모의 데이터 생성
        if self.mock_mode:
            tr_table = None
            for table in self.schema_info["tables"]:
                if table["name"] == "tr_data":
                    tr_table = table
                    break
            
            if not tr_table or "sample_data" not in tr_table:
                return {"error": "TR 테이블을 찾을 수 없습니다."}
            
            # 새 TR ID 계산
            max_id = 0
            for tr in tr_table["sample_data"]:
                if tr.get("id", 0) > max_id:
                    max_id = tr.get("id", 0)
            
            new_tr_id = max_id + 1
            
            # 새 TR 데이터 생성
            new_tr = {
                "id": new_tr_id,
                "tr_code": tr_code,
                "project_id": project_id,
                "title": title,
                "description": description or "",
                "status": "DRAFT",
                "priority": priority,
                "type": type,
                "target_release": target_release or "",
                "requested_by": user_id,
                "assigned_to": None,
                "approved_by": None,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # TR 데이터 추가
            tr_table["sample_data"].append(new_tr)
            
            return {
                "success": True,
                "message": "TR이 성공적으로 생성되었습니다.",
                "data": new_tr
            }
        else:
            # SQL 쿼리 구성
            query = f"""
            INSERT INTO tr_data 
            (tr_code, project_id, title, description, status, priority, type, 
            target_release, requested_by, created_at, updated_at)
            VALUES 
            ('{tr_code}', {project_id}, '{title}', '{description or ""}', 'DRAFT', '{priority}', '{type}',
            '{target_release or ""}', {user_id}, NOW(), NOW())
            """
            
            try:
                self.db_agent._execute_query(query)
                
                # 생성된 TR 정보 조회
                query = f"SELECT * FROM tr_data WHERE tr_code = '{tr_code}'"
                result = self.db_agent._execute_query(query)
                
                if not result or len(result) == 0:
                    return {"error": "TR 생성 후 조회 오류가 발생했습니다."}
                
                return {
                    "success": True,
                    "message": "TR이 성공적으로 생성되었습니다.",
                    "data": result[0]
                }
            except Exception as e:
                logger.error(f"TR 생성 오류: {e}")
                return {"error": f"TR 생성 오류: {str(e)}"}
    
    # 유틸리티 메서드
    def _generate_random_string(self, length: int) -> str:
        """랜덤 문자열 생성"""
        import random
        import string
        
        chars = string.ascii_uppercase + string.digits
        return ''.join(random.choice(chars) for _ in range(length))