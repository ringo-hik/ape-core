# APE(Agentic Pipeline Engine) 마이그레이션 가이드

이 문서는 Axiom Core에서 APE(Agentic Pipeline Engine)로 마이그레이션하는 사용자와 개발자를 위한 가이드를 제공합니다.

## 개요

Axiom Core가 APE(Agentic Pipeline Engine)로 리브랜딩되었습니다. 이 변경은 네이밍과 환경 변수에 영향을 미치지만 기본적인 기능은 그대로 유지됩니다.

## 변경 사항 요약

1. 프로젝트 이름: `Axiom Core` → `APE (Agentic Pipeline Engine)`
2. 환경 변수 접두사: `AXIOM_` → `APE_`
3. 로그 파일: `./logs/axiom.log` → `./logs/ape.log`
4. 리포지토리 경로: `axiom-core` → `ape-core`

## 환경 변수 마이그레이션

### 기존 .env 파일

Axiom Core에서는 다음과 같은 환경 변수를 사용했습니다:

```
AXIOM_SERVER__HOST=0.0.0.0
AXIOM_SERVER__PORT=8001
AXIOM_LLM__MODEL=claude3-opus
AXIOM_LOGGING__LEVEL=INFO
AXIOM_LOGGING__FILE=./logs/axiom.log
```

### 새로운 .env 파일

APE(Agentic Pipeline Engine)로 마이그레이션 후:

```
APE_SERVER__HOST=0.0.0.0
APE_SERVER__PORT=8001
APE_LLM__MODEL=claude3-opus
APE_LOGGING__LEVEL=INFO
APE_LOGGING__FILE=./logs/ape.log
```

## API 호출 변경 사항

API 호출 자체는 변경되지 않았지만, 일부 예제와 요청 내용이 업데이트되었습니다:

```bash
# 기존 요청
curl -X POST http://localhost:8001/agents/rag \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Axiom Core 시스템에 대해 설명해주세요",
    "streaming": false
  }'

# 새로운 요청
curl -X POST http://localhost:8001/agents/rag \
  -H "Content-Type: application/json" \
  -d '{
    "query": "APE (Agentic Pipeline Engine) 시스템에 대해 설명해주세요",
    "streaming": false
  }'
```

## 코드 마이그레이션 체크리스트

기존 코드를 APE(Agentic Pipeline Engine)로 마이그레이션할 때 다음 사항을 확인하세요:

1. 모든 "Axiom" 문자열을 "APE"로 변경
2. 모든 "Axiom Core"를 "APE" 또는 "APE (Agentic Pipeline Engine)"로 변경
3. 환경 변수 접두사 "AXIOM_"을 "APE_"로 변경
4. 로그 파일 경로 업데이트
5. 저장소 경로 및 설명 업데이트

## 설정 파일 업데이트

`config/settings.json` 파일이 다음과 같이 업데이트되어야 합니다:

```json
{
  "version": "0.5.0",
  "app": {
    "name": "APE (Agentic Pipeline Engine)",
    "description": "온프레미스 Agentic Pipeline Engine 시스템"
  },
  ...
}
```

## 내부망 환경에서의 마이그레이션

내부망 환경에서 마이그레이션할 때 다음 단계를 따르세요:

1. 기존 Axiom Core 코드 백업
2. 새로운 APE 코드 다운로드 또는 리브랜딩 적용
3. `.env` 파일의 모든 `AXIOM_` 접두사를 `APE_`로 변경
4. 설정 파일 업데이트
5. 시스템 재시작

## 추가 지원

마이그레이션과 관련된 질문이 있으면 개발팀에 문의하세요. 이 리브랜딩은 코드 기능이 아닌 네이밍과 브랜딩에만 영향을 미치므로 기존 기능은 정상적으로 계속 작동합니다.