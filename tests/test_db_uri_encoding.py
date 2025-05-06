"""
데이터베이스 URI 인코딩 테스트

이 모듈은 데이터베이스 URI에서 사용자 이름과 비밀번호의 특수 문자 인코딩 기능을 테스트합니다.
"""

import os
import unittest
from src.core.env_loader import get_db_uri_env

class TestDBUriEncoding(unittest.TestCase):
    """데이터베이스 URI 인코딩 테스트 클래스"""
    
    def setUp(self):
        """테스트 설정"""
        # 테스트용 환경 변수 저장
        self.original_env = os.environ.copy()
        
    def tearDown(self):
        """테스트 후 정리"""
        # 테스트 중 변경된 환경 변수 복원
        os.environ.clear()
        os.environ.update(self.original_env)
        
    def test_normal_uri(self):
        """일반 URI 테스트"""
        # 테스트 데이터 설정
        test_uri = "postgresql://user:password@localhost:5432/database"
        os.environ["TEST_DB_URI"] = test_uri
        
        # 함수 실행
        result = get_db_uri_env("TEST_DB_URI")
        
        # 특수 문자가 없는 경우 원래 URI와 같아야 함
        self.assertEqual(result, test_uri)
        
    def test_special_chars_in_password(self):
        """비밀번호에 특수 문자가 포함된 URI 테스트"""
        # 테스트 데이터 설정 - @ 문자 포함
        test_uri = "postgresql://user:p@ssw0rd@localhost:5432/database"
        os.environ["TEST_DB_URI"] = test_uri
        
        # 함수 실행
        result = get_db_uri_env("TEST_DB_URI")
        
        # 예상 결과: 비밀번호에서 @ 문자가 %40으로 인코딩됨
        expected = "postgresql://user:p%40ssw0rd@localhost:5432/database"
        self.assertEqual(result, expected)
        
    def test_special_chars_in_username(self):
        """사용자 이름에 특수 문자가 포함된 URI 테스트"""
        # 테스트 데이터 설정 - @ 문자 포함
        test_uri = "postgresql://user@name:password@localhost:5432/database"
        os.environ["TEST_DB_URI"] = test_uri
        
        # 함수 실행
        result = get_db_uri_env("TEST_DB_URI")
        
        # 예상 결과: 사용자 이름에서 @ 문자가 %40으로 인코딩됨
        expected = "postgresql://user%40name:password@localhost:5432/database"
        self.assertEqual(result, expected)
        
    def test_special_chars_in_both(self):
        """사용자 이름과 비밀번호 모두에 특수 문자가 포함된 URI 테스트"""
        # 테스트 데이터 설정 - 여러 특수 문자 포함
        test_uri = "postgresql://user@name:p@ss/w:rd@localhost:5432/database"
        os.environ["TEST_DB_URI"] = test_uri
        
        # 함수 실행
        result = get_db_uri_env("TEST_DB_URI")
        
        # 예상 결과: 모든 특수 문자가 인코딩됨
        expected = "postgresql://user%40name:p%40ss%2Fw%3Ard@localhost:5432/database"
        self.assertEqual(result, expected)
        
    def test_no_auth_uri(self):
        """인증 정보가 없는 URI 테스트"""
        # 테스트 데이터 설정
        test_uri = "postgresql://localhost:5432/database"
        os.environ["TEST_DB_URI"] = test_uri
        
        # 함수 실행
        result = get_db_uri_env("TEST_DB_URI")
        
        # 인증 정보가 없는 경우 원래 URI와 같아야 함
        self.assertEqual(result, test_uri)

if __name__ == "__main__":
    unittest.main()