#!/bin/bash

# APE (Agentic Pipeline Engine) 테스트 실행 스크립트

echo "=== APE (Agentic Pipeline Engine) 테스트 스위트 ==="

# 현재 디렉토리
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BASE_DIR="$( dirname "$DIR" )"

# 가상환경 활성화
if [ -d "$BASE_DIR/axiom_venv" ]; then
    echo "가상환경을 활성화합니다..."
    source "$BASE_DIR/axiom_venv/bin/activate"
elif [ -d "$BASE_DIR/venv" ]; then
    echo "가상환경을 활성화합니다..."
    source "$BASE_DIR/venv/bin/activate"
else
    echo "경고: 가상환경을 찾을 수 없습니다. 시스템 Python을 사용합니다."
fi

# 테스트 모드 옵션
function usage {
    echo "사용법: $0 [옵션]"
    echo "옵션:"
    echo "  --local       로컬 테스트 실행 (기본)"
    echo "  --external    외부망 연결 테스트 실행"
    echo "  --internal    내부망 연결 테스트 실행"
    echo "  --mock        목 테스트 실행 (외부 의존성 없음)"
    echo "  --all         모든 테스트 실행"
    echo "  --help        도움말 표시"
    exit 1
}

# 인자 파싱
LOCAL=false
EXTERNAL=false
INTERNAL=false
MOCK=false

# 인자가 없으면 로컬 테스트로 설정
if [ "$#" -eq 0 ]; then
    LOCAL=true
fi

for arg in "$@"
do
    case $arg in
        --local)
            LOCAL=true
            shift
            ;;
        --external)
            EXTERNAL=true
            shift
            ;;
        --internal)
            INTERNAL=true
            shift
            ;;
        --mock)
            MOCK=true
            shift
            ;;
        --all)
            LOCAL=true
            EXTERNAL=true
            INTERNAL=true
            MOCK=true
            shift
            ;;
        --help)
            usage
            ;;
        *)
            echo "알 수 없는 인자: $arg"
            usage
            ;;
    esac
done

# 테스트 결과 변수 초기화
TEST_RESULT=0

# 목 테스트 실행
if [ "$MOCK" = true ]; then
    echo "===== 목 테스트 실행 ====="
    bash "$DIR/mock_tests/run_mock_tests.sh"
    MOCK_RESULT=$?
    
    if [ $MOCK_RESULT -ne 0 ]; then
        TEST_RESULT=1
        echo "일부 목 테스트가 실패했습니다."
    else
        echo "모든 목 테스트가 성공적으로 완료되었습니다."
    fi
fi

# 테스트 모드 설정
if [ "$LOCAL" = true ] || [ "$EXTERNAL" = true ] || [ "$INTERNAL" = true ]; then
    echo "테스트 모드 설정:"
    echo "- 로컬 테스트: $LOCAL"
    echo "- 외부망 테스트: $EXTERNAL"
    echo "- 내부망 테스트: $INTERNAL"
    
    # 임시 설정 파일 생성
    TEST_CONFIG="$DIR/test_config.json"
    TMP_CONFIG="$DIR/test_config.tmp.json"
    
    cp "$TEST_CONFIG" "$TMP_CONFIG"
    
    # 테스트 모드 업데이트
    TEST_MODES="["
    if [ "$LOCAL" = true ]; then
        TEST_MODES="$TEST_MODES\"local\""
    fi
    if [ "$EXTERNAL" = true ]; then
        if [ "$TEST_MODES" != "[" ]; then
            TEST_MODES="$TEST_MODES, "
        fi
        TEST_MODES="$TEST_MODES\"external\""
    fi
    if [ "$INTERNAL" = true ]; then
        if [ "$TEST_MODES" != "[" ]; then
            TEST_MODES="$TEST_MODES, "
        fi
        TEST_MODES="$TEST_MODES\"internal\""
    fi
    TEST_MODES="$TEST_MODES]"
    
    # 설정 파일 업데이트
    sed -i "s/\"test_modes\": \[.*\]/\"test_modes\": $TEST_MODES/" "$TEST_CONFIG"
    sed -i "s/\"enable_external_tests\": .*/\"enable_external_tests\": $EXTERNAL,/" "$TEST_CONFIG"
    sed -i "s/\"enable_internal_tests\": .*/\"enable_internal_tests\": $INTERNAL,/" "$TEST_CONFIG"
    
    # 서버 실행 확인
    SERVER_RUNNING=false
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/health 2>/dev/null | grep -q "200"; then
        SERVER_RUNNING=true
    fi
    
    # 서버가 실행 중이 아니면 경고
    if [ "$SERVER_RUNNING" = false ]; then
        echo "경고: 서버가 실행 중이지 않습니다. 통합 테스트를 건너뜁니다."
        echo "서버를 실행한 후 통합 테스트를 실행하려면 --local 옵션을 사용하세요."
    else
        # 테스트 실행
        echo "===== 통합 테스트 실행 ====="
        python "$DIR/test_suite.py"
        SUITE_RESULT=$?
        
        if [ $SUITE_RESULT -ne 0 ]; then
            TEST_RESULT=1
            echo "일부 통합 테스트가 실패했습니다."
        else
            echo "모든 통합 테스트가 성공적으로 완료되었습니다."
        fi
    fi
    
    # 설정 파일 복원
    mv "$TMP_CONFIG" "$TEST_CONFIG"
fi

# 종료
if [ $TEST_RESULT -eq 0 ]; then
    echo "===== 모든 테스트가 성공적으로 완료되었습니다 ====="
else
    echo "===== 일부 테스트가 실패했습니다 ====="
fi

exit $TEST_RESULT