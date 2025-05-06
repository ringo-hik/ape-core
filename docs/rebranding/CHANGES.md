# APE (Agentic Pipeline Engine) 변경 사항 상세 내역

이 문서는 Axiom Core에서 APE(Agentic Pipeline Engine)로 리브랜딩하는 과정에서 변경된 모든 세부 사항을 기록합니다.

## 파일별 변경 내역

### 1. config/settings.json
```diff
{
  "version": "0.5.0",
  "app": {
-    "name": "AI Agent Core",
-    "description": "온프레미스 AI Agent 시스템"
+    "name": "APE (Agentic Pipeline Engine)",
+    "description": "온프레미스 Agentic Pipeline Engine 시스템"
  },
```

### 2. run.py
```diff
#!/usr/bin/env python3
"""
-Axiom Core 실행 스크립트
+APE (Agentic Pipeline Engine) 실행 스크립트

-이 스크립트는 Axiom Core API 서버를 시작합니다.
+이 스크립트는 APE (Agentic Pipeline Engine) API 서버를 시작합니다.
보안 경고 비활성화 및 환경 설정을 처리합니다.
"""
```

### 3. src/core/llm_service.py
```diff
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {openrouter_key}",
-            "HTTP-Referer": "Axiom-Core-API",
-            "X-Title": "Axiom Core"
+            "HTTP-Referer": "APE-Core-API",
+            "X-Title": "APE (Agentic Pipeline Engine)"
        }
```

### 4. src/core/config_manager.py
```diff
        self._config: Dict[str, Any] = {}
        self._default_config: Dict[str, Any] = {}
-        self._env_prefix = "AXIOM_"
+        self._env_prefix = "APE_"
        
        # 기본 설정 파일 경로
        self._config_paths = config_paths or [
```

```diff
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
-                "file": "./logs/axiom.log"
+                "file": "./logs/ape.log"
            }
```

```diff
        for env_name, env_value in os.environ.items():
-            # AXIOM_ 접두사로 시작하는 환경 변수만 처리
+            # APE_ 접두사로 시작하는 환경 변수만 처리
            if env_name.startswith(self._env_prefix):
```

```diff
                # 환경 변수 이름에서 접두사 제거
                config_key = env_name[len(self._env_prefix):].lower()
                
-                # 중첩된 키는 '__'로 구분 (예: AXIOM_SERVER__PORT -> server.port)
+                # 중첩된 키는 '__'로 구분 (예: APE_SERVER__PORT -> server.port)
                if '__' in config_key:
```

### 5. config.py
```diff
"""
-Axiom Core 시스템 설정
+APE (Agentic Pipeline Engine) 시스템 설정

-이 파일은 Axiom Core 시스템의 주요 설정을 포함합니다.
+이 파일은 APE (Agentic Pipeline Engine) 시스템의 주요 설정을 포함합니다.
로컬 호스트 LLM API 설정, 기본 모델 구성 등을 포함합니다.
.env 파일에서 환경 변수를 로드합니다.
"""
```

### 6. src/agents/rag_agent.py
```diff
                "filename": "getting_started.md",
                "title": "시작하기",
-                "content": """# Axiom Core: 시작하기
+                "content": """# APE (Agentic Pipeline Engine): 시작하기

## 개요

-Axiom Core는 온프레미스 환경에서 동작하는 AI Agent 시스템입니다. 각 Agent는 독립적인 원자적 동작을 보장하며, 복잡한 워크플로우를 구성할 수 있습니다.
+APE(Agentic Pipeline Engine)는 온프레미스 환경에서 동작하는 AI Agent 시스템입니다. 각 Agent는 독립적인 원자적 동작을 보장하며, 복잡한 워크플로우를 구성할 수 있습니다.
```

```diff
1. 저장소 클론:
   ```
-   git clone https://github.com/example/axiom-core.git
-   cd axiom-core
+   git clone https://github.com/example/ape-core.git
+   cd ape-core
   ```
```

```diff
예제 요청:
```
POST /agents/rag
{
-  "query": "Axiom Core 시스템에 대해 설명해주세요",
+  "query": "APE(Agentic Pipeline Engine) 시스템에 대해 설명해주세요",
  "streaming": false
}
```
```

```diff
                "filename": "architecture.md",
                "title": "아키텍처",
-                "content": """# Axiom Core: 아키텍처
+                "content": """# APE (Agentic Pipeline Engine): 아키텍처

## 구성 요소

-Axiom Core는 다음 구성 요소로 이루어져 있습니다:
+APE(Agentic Pipeline Engine)는 다음 구성 요소로 이루어져 있습니다:
```

```diff
## 시스템 구조

```
-axiom-core/
+ape-core/
├── main.py         - 메인 진입점
├── src/
```

```diff
                "id": "sim1",
-                "title": "Axiom Core 소개",
-                "content": f"Axiom Core는 {query}와 관련된 기능을 제공하는 온프레미스 AI Agent 시스템입니다. 각 Agent는 독립적인 원자적 동작을 보장합니다.",
+                "title": "APE (Agentic Pipeline Engine) 소개",
+                "content": f"APE(Agentic Pipeline Engine)는 {query}와 관련된 기능을 제공하는 온프레미스 AI Agent 시스템입니다. 각 Agent는 독립적인 원자적 동작을 보장합니다.",
                "metadata": {
-                    "title": "Axiom Core 소개",
+                    "title": "APE (Agentic Pipeline Engine) 소개",
```

### 7. README.md
```diff
-# AI Agent Core
+# APE (Agentic Pipeline Engine)

온프레미스 환경에서 동작하는 AI Agent 시스템

## 개요

-AI Agent Core는 온프레미스 환경에서 동작하는 AI Agent 시스템입니다. 각 Agent는 독립적인 원자적 동작을 보장하며, 복잡한 워크플로우를 구성할 수 있습니다.
+APE(Agentic Pipeline Engine)는 온프레미스 환경에서 동작하는 AI Agent 시스템입니다. 각 Agent는 독립적인 원자적 동작을 보장하며, 복잡한 워크플로우를 구성할 수 있습니다.
```

```diff
1. 저장소 클론 및 디렉토리 이동:
    ```
-    git clone https://github.com/example/axiom-core.git
-    cd axiom-core
+    git clone https://github.com/example/ape-core.git
+    cd ape-core
    ```
```

```diff
curl -X POST http://localhost:8001/agents/rag \
  -H "Content-Type: application/json" \
  -d '{
-    "query": "Axiom Core 시스템에 대해 설명해주세요",
+    "query": "APE(Agentic Pipeline Engine) 시스템에 대해 설명해주세요",
    "streaming": false
  }'
```

```diff
## 내부망/외부망 연결

-Axiom Core는 내부망/외부망 LLM 서비스를 자동으로 선택하여 사용합니다:
+APE는 내부망/외부망 LLM 서비스를 자동으로 선택하여 사용합니다:
```

```diff
## 파일 구조

```
-axiom-core/
+ape-core/
├── main.py           # 메인 진입점
```

## 추가된 파일
- `/home/hik90/ape/ape-core/APE_CHECKLIST.md`: CORE_CHECKLIST.md를 기반으로 생성되었으며 모든 Axiom 참조를 APE로 변경
- `/home/hik90/ape/ape-core/docs/rebranding/README.md`: 리브랜딩 개요와 변경사항 요약
- `/home/hik90/ape/ape-core/docs/rebranding/CHANGES.md`: 이 파일로, 상세 변경 내역 기록