# APE (Agentic Pipeline Engine) 배포 가이드

이 문서는 APE Core 시스템을 내부망/외부망 환경에서 배포하기 위한 단계별 가이드를 제공합니다.

## 배포 전 준비 사항

### 필수 요구사항

- Python 3.9 이상
- pip 패키지 관리자
- 내부망 배포 시: 내부 LLM 서비스 접근 정보
- 외부망 배포 시: OpenRouter API 키

### 환경 설정 파일 준비

배포 환경에 맞게 다음 파일을 구성해야 합니다:

1. `.env` 파일: 환경 변수 설정
   - 내부망/외부망 연결 정보
   - API 키 및 엔드포인트
   - 서버 설정

## 배포 단계

### 1. 코드 복제 및 디렉토리 설정

```bash
# 저장소 복제
git clone <repository-url> ape-core
cd ape-core

# 필요한 디렉토리 생성
mkdir -p data/docs data/chroma_db
```

### 2. 환경 설정

#### 외부망 전용 환경

```bash
# 외부망 설정 스크립트 실행
./setup.sh

# 환경 변수 설정
# .env 파일에서 다음 항목 설정:
# - NETWORK_MODE=external
# - OPENROUTER_API_KEY=<your-api-key>
```

#### 내부망 전용 환경

```bash
# 내부망 설정 스크립트 실행
./setup_internal.sh

# 환경 변수 설정
# .env 파일에서 다음 항목 설정:
# - NETWORK_MODE=internal
# - INTERNAL_LLM_ENDPOINT=<internal-endpoint>
# - INTERNAL_LLM_API_KEY=<internal-api-key>
```

#### 하이브리드 환경 (내부망 + 외부망)

```bash
# 기본 설정 스크립트 실행
./setup.sh

# 환경 변수 설정
# .env 파일에서 다음 항목 설정:
# - NETWORK_MODE=hybrid
# - INTERNAL_LLM_ENDPOINT=<internal-endpoint>
# - INTERNAL_LLM_API_KEY=<internal-api-key>
# - OPENROUTER_API_KEY=<your-api-key>
```

### 3. 운영 환경 설정

운영 환경에서는 보안 및 성능을 위해 추가 설정이 필요합니다:

#### SSL 설정 (권장)

```bash
# .env 파일에서 SSL 설정
USE_SSL=true
SSL_CERT=/path/to/cert.pem
SSL_KEY=/path/to/key.pem
```

#### 서버 설정

```bash
# .env 파일에서 서버 설정
API_HOST=0.0.0.0  # 모든 인터페이스에서 접근 허용
API_PORT=8001     # 필요시 포트 변경
API_TIMEOUT=120   # 요청 타임아웃 (초)
```

### 4. 외부 서비스 연동 설정

시스템에서 사용하는 외부 서비스 연동 설정:

#### SWDP 연동

```bash
# .env 파일에서 SWDP 설정
SWDP_ENABLED=true
SWDP_API_URL=<swdp-api-url>
SWDP_USERNAME=<username>
SWDP_PASSWORD=<password>
SWDP_API_KEY=<api-key>
```

#### Jira 연동

```bash
# .env 파일에서 Jira 설정
JIRA_ENABLED=true
JIRA_API_URL=<jira-api-url>
JIRA_USERNAME=<username>
JIRA_PASSWORD=<password>
JIRA_API_KEY=<api-key>
```

#### Pocket 연동

```bash
# .env 파일에서 Pocket 설정
POCKET_ENABLED=true
POCKET_API_URL=<pocket-api-url>
POCKET_API_KEY=<api-key>
POCKET_ACCESS_KEY=<access-key>
```

### 5. 서버 실행

```bash
# 기본 실행
python run.py

# 네트워크 모드 지정 실행
python run.py --mode internal  # 내부망 모드
python run.py --mode external  # 외부망 모드

# 디버그 모드 실행
python run.py --debug
```

### 6. 배포 검증

다음 테스트를 통해 배포가 성공적으로 완료되었는지 확인합니다:

#### 상태 확인

```bash
curl http://<server-ip>:8001/health
```

#### API 테스트

```bash
# 직접 쿼리 테스트
curl -X POST http://<server-ip>:8001/query \
  -H "Content-Type: application/json" \
  -d '{"query": "테스트 메시지입니다.", "streaming": false}'

# RAG 에이전트 테스트
curl -X POST http://<server-ip>:8001/agents/rag \
  -H "Content-Type: application/json" \
  -d '{"query": "APE 시스템에 대해 설명해주세요.", "streaming": false}'
```

## 주의사항 및 문제 해결

### 네트워크 모드 전환

시스템은 네트워크 모드에 따라 LLM 서비스 연결을 관리합니다:

- `internal`: 내부망 LLM 서비스만 사용
- `external`: 외부망 OpenRouter 서비스만 사용
- `hybrid`: 두 서비스 모두 사용 가능, 장애 시 자동 전환

### 자동 전환 로직

하이브리드 모드에서는 다음과 같은 자동 전환 로직이 적용됩니다:

- 내부망 LLM 서비스 실패 시 → 외부망 서비스로 자동 전환
- 외부망 서비스 실패 시 → 내부망 LLM 서비스로 자동 전환

### 일반적인 문제 해결

1. **API 키 오류**
   - `.env` 파일에서 API 키가 올바르게 설정되었는지 확인

2. **연결 오류**
   - 내부망 LLM 서비스 엔드포인트 접근 가능 여부 확인
   - OpenRouter API 키 유효성 및 인터넷 연결 확인

3. **의존성 오류**
   - `pip install -r requirements.txt` 재실행
   - 내부망에서 패키지 다운로드 제한 시 `setup_internal.sh` 스크립트 사용

4. **서버 시작 오류**
   - 로그 확인: `python run.py --debug`
   - 포트 충돌 시 `.env` 파일에서 `API_PORT` 변경

## 운영 관리

### 로깅

로그는 콘솔에 출력되며, 필요시 로그 파일로 리다이렉션할 수 있습니다:

```bash
python run.py > server.log 2>&1
```

### 백업 및 복구

주요 데이터 디렉토리를 정기적으로 백업하세요:

```bash
# 데이터 디렉토리 백업
tar -czf ape-data-backup.tar.gz data/

# 환경 설정 백업
cp .env .env.backup
```

### 재시작 프로세스

시스템 업데이트 후 재시작 프로세스:

```bash
# 코드 업데이트
git pull

# 의존성 업데이트
pip install -r requirements.txt

# 서버 재시작
python run.py
```

## 문의 및 지원

추가 지원이 필요한 경우 다음으로 문의하세요:

- 기술 지원: [support@example.com]
- 문서: [docs/README.md]