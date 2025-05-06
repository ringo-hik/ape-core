"""
APE (Agentic Pipeline Engine) 통합 테스트 스위트

이 모듈은 APE(Agentic Pipeline Engine)의 다양한 기능을 테스트하는 통합 테스트를 제공합니다.
각 테스트 케이스는 서로 독립적으로 실행될 수 있으며, 다양한 환경 설정과 시나리오를 지원합니다.
"""

import os
import sys
import json
import time
import unittest
import warnings
import logging
import requests
from typing import Dict, Any, List, Optional, Union

# 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("test_suite")

# 보안 경고 비활성화
warnings.filterwarnings('ignore', message='Unverified HTTPS request')
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    pass
try:
    import requests.packages.urllib3
    requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
except (ImportError, AttributeError):
    pass

# 설정 로드
def load_config():
    """테스트 설정 로드"""
    config_path = os.path.join(os.path.dirname(__file__), "test_config.json")
    
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # 기본 설정 반환
    return {
        "api_url": "http://localhost:8001",
        "timeout": 30,
        "verify_ssl": False,
        "test_modes": ["local"],
        "enable_external_tests": False,
        "enable_internal_tests": False
    }

# API 클라이언트 클래스
class ApiClient:
    """API 클라이언트 클래스"""
    
    def __init__(self, base_url: str, timeout: int = 30, verify_ssl: bool = False):
        """
        API 클라이언트 초기화
        
        Args:
            base_url: API 기본 URL
            timeout: 요청 타임아웃 (초)
            verify_ssl: SSL 인증서 검증 여부
        """
        self.base_url = base_url
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
    
    def get(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        GET 요청 보내기
        
        Args:
            endpoint: API 엔드포인트
            params: 요청 매개변수
            
        Returns:
            응답 데이터
        """
        url = f"{self.base_url}{endpoint}"
        response = self.session.get(
            url,
            params=params,
            timeout=self.timeout,
            verify=self.verify_ssl
        )
        response.raise_for_status()
        return response.json()
    
    def post(self, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        POST 요청 보내기
        
        Args:
            endpoint: API 엔드포인트
            data: 요청 데이터
            
        Returns:
            응답 데이터
        """
        url = f"{self.base_url}{endpoint}"
        response = self.session.post(
            url,
            json=data,
            timeout=self.timeout,
            verify=self.verify_ssl
        )
        response.raise_for_status()
        return response.json()

# 기본 테스트 케이스
class APETestCase(unittest.TestCase):
    """APE (Agentic Pipeline Engine) 기본 테스트 케이스 클래스"""
    
    @classmethod
    def setUpClass(cls):
        """테스트 클래스 설정"""
        cls.config = load_config()
        cls.api_client = ApiClient(
            base_url=cls.config["api_url"],
            timeout=cls.config["timeout"],
            verify_ssl=cls.config["verify_ssl"]
        )
    
    def setUp(self):
        """각 테스트 설정"""
        pass
    
    def tearDown(self):
        """각 테스트 정리"""
        pass
    
    def skip_if_not_enabled(self, test_mode: str):
        """
        특정 테스트 모드가 활성화되지 않은 경우 테스트 건너뛰기
        
        Args:
            test_mode: 테스트 모드 (local, external, internal)
        """
        if test_mode not in self.config["test_modes"]:
            self.skipTest(f"{test_mode} 테스트 모드가 활성화되지 않았습니다.")

# API 기본 테스트
class ApiBasicTest(APETestCase):
    """API 기본 테스트 케이스"""
    
    def test_health_endpoint(self):
        """건강 상태 엔드포인트 테스트"""
        response = self.api_client.get("/health")
        self.assertEqual(response["status"], "healthy")
        self.assertIn("version", response)
        self.assertIn("timestamp", response)
    
    def test_root_endpoint(self):
        """루트 엔드포인트 테스트"""
        response = self.api_client.get("/")
        self.assertIn("name", response)
        self.assertIn("version", response)
        self.assertIn("description", response)
        self.assertIn("endpoints", response)

# LLM 서비스 테스트
class LlmServiceTest(APETestCase):
    """LLM 서비스 테스트 케이스"""
    
    def test_list_models(self):
        """모델 목록 조회 테스트"""
        response = self.api_client.get("/models")
        self.assertIn("models", response)
        self.assertIn("current", response)
        self.assertIn("default", response)
    
    def test_direct_query(self):
        """직접 쿼리 테스트"""
        self.skip_if_not_enabled("external")
        
        query_data = {
            "query": "안녕하세요, 테스트입니다.",
            "streaming": False
        }
        
        response = self.api_client.post("/query", data=query_data)
        self.assertIn("content", response)
        self.assertIn("model", response)

# RAG 에이전트 테스트
class RagAgentTest(APETestCase):
    """RAG 에이전트 테스트 케이스"""
    
    def test_list_agents(self):
        """에이전트 목록 조회 테스트"""
        response = self.api_client.get("/agents")
        self.assertIn("agents", response)
    
    def test_rag_query(self):
        """RAG 쿼리 테스트"""
        self.skip_if_not_enabled("external")
        
        query_data = {
            "query": "APE (Agentic Pipeline Engine) 아키텍처에 대해 설명해주세요.",
            "streaming": False
        }
        
        response = self.api_client.post("/agents/rag", data=query_data)
        self.assertIn("content", response)
        self.assertIn("model", response)
        self.assertIn("agent_id", response)

# 내부망 연결 테스트
class InternalConnectionTest(APETestCase):
    """내부망 연결 테스트 케이스"""
    
    def test_internal_connection(self):
        """내부망 연결 테스트"""
        self.skip_if_not_enabled("internal")
        
        # 내부망 엔드포인트 설정
        internal_endpoint = self.config.get("internal_endpoint", "")
        if not internal_endpoint:
            self.skipTest("내부망 엔드포인트가 설정되지 않았습니다.")
        
        try:
            response = requests.get(
                internal_endpoint + "/health",
                timeout=2,
                verify=False
            )
            self.assertEqual(response.status_code, 200)
        except requests.exceptions.RequestException as e:
            self.fail(f"내부망 연결 테스트 실패: {e}")

# 외부망 연결 테스트
class ExternalConnectionTest(APETestCase):
    """외부망 연결 테스트 케이스"""
    
    def test_anthropic_connection(self):
        """Anthropic 연결 테스트"""
        self.skip_if_not_enabled("external")
        
        if "ANTHROPIC_API_KEY" not in os.environ:
            self.skipTest("ANTHROPIC_API_KEY 환경 변수가 설정되지 않았습니다.")
        
        try:
            response = requests.get(
                "https://api.anthropic.com/v1/models",
                headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"]},
                timeout=5
            )
            self.assertEqual(response.status_code, 200)
        except requests.exceptions.RequestException as e:
            self.fail(f"Anthropic 연결 테스트 실패: {e}")
    
    def test_openrouter_connection(self):
        """OpenRouter 연결 테스트"""
        self.skip_if_not_enabled("external")
        
        if "OPENROUTER_API_KEY" not in os.environ:
            self.skipTest("OPENROUTER_API_KEY 환경 변수가 설정되지 않았습니다.")
        
        try:
            response = requests.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"},
                timeout=5
            )
            self.assertEqual(response.status_code, 200)
        except requests.exceptions.RequestException as e:
            self.fail(f"OpenRouter 연결 테스트 실패: {e}")

# 성능 테스트
class PerformanceTest(APETestCase):
    """성능 테스트 케이스"""
    
    def test_response_time(self):
        """응답 시간 테스트"""
        start_time = time.time()
        self.api_client.get("/health")
        end_time = time.time()
        
        response_time = end_time - start_time
        logger.info(f"응답 시간: {response_time:.2f}초")
        
        # 응답 시간이 1초 이내여야 함
        self.assertLess(response_time, 1.0)
    
    def test_concurrent_requests(self):
        """동시 요청 테스트"""
        import concurrent.futures
        
        # 동시 요청 수
        num_requests = 10
        
        def make_request():
            try:
                start_time = time.time()
                self.api_client.get("/health")
                end_time = time.time()
                return end_time - start_time
            except Exception as e:
                return str(e)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_requests) as executor:
            results = list(executor.map(lambda _: make_request(), range(num_requests)))
        
        # 모든 요청이 성공해야 함
        for result in results:
            self.assertIsInstance(result, float)
        
        # 평균 응답 시간 계산
        avg_response_time = sum(results) / len(results)
        logger.info(f"평균 응답 시간: {avg_response_time:.2f}초")
        
        # 평균 응답 시간이 2초 이내여야 함
        self.assertLess(avg_response_time, 2.0)

# 오류 처리 테스트
class ErrorHandlingTest(APETestCase):
    """오류 처리 테스트 케이스"""
    
    def test_not_found(self):
        """존재하지 않는 엔드포인트 테스트"""
        with self.assertRaises(requests.exceptions.HTTPError) as context:
            self.api_client.get("/not_exists")
        
        self.assertEqual(context.exception.response.status_code, 404)
    
    def test_invalid_agent(self):
        """존재하지 않는 에이전트 테스트"""
        with self.assertRaises(requests.exceptions.HTTPError) as context:
            self.api_client.post("/agents/invalid", data={"query": "테스트"})
        
        self.assertEqual(context.exception.response.status_code, 422)  # FastAPI validation error

# 통합 테스트 스위트
def create_test_suite():
    """테스트 스위트 생성"""
    test_suite = unittest.TestSuite()
    
    # 기본 테스트
    test_suite.addTest(unittest.makeSuite(ApiBasicTest))
    
    # LLM 서비스 테스트
    test_suite.addTest(unittest.makeSuite(LlmServiceTest))
    
    # RAG 에이전트 테스트
    test_suite.addTest(unittest.makeSuite(RagAgentTest))
    
    # 내부망 연결 테스트 (설정에 따라 활성화)
    config = load_config()
    if config.get("enable_internal_tests"):
        test_suite.addTest(unittest.makeSuite(InternalConnectionTest))
    
    # 외부망 연결 테스트 (설정에 따라 활성화)
    if config.get("enable_external_tests"):
        test_suite.addTest(unittest.makeSuite(ExternalConnectionTest))
    
    # 성능 테스트
    test_suite.addTest(unittest.makeSuite(PerformanceTest))
    
    # 오류 처리 테스트
    test_suite.addTest(unittest.makeSuite(ErrorHandlingTest))
    
    return test_suite

# 테스트 실행
if __name__ == '__main__':
    # 테스트 모드 로드
    config = load_config()
    test_modes = config.get("test_modes", ["local"])
    
    # 테스트 모드 로깅
    logger.info(f"테스트 모드: {', '.join(test_modes)}")
    
    # 서버 실행 중인지 확인
    try:
        requests.get(config["api_url"] + "/health", timeout=2, verify=False)
    except requests.exceptions.RequestException:
        logger.error(f"서버가 실행 중이지 않습니다: {config['api_url']}")
        logger.info("먼저 서버를 실행한 후 테스트를 실행하세요.")
        sys.exit(1)
    
    # 테스트 실행
    test_suite = create_test_suite()
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(test_suite)