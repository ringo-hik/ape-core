#!/bin/bash
# APE (Agentic Pipeline Engine) 실행 스크립트

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# 가상 환경 활성화
if [ -d "ape_venv" ]; then
    echo "가상 환경 활성화: ape_venv"
    source ape_venv/bin/activate
else
    echo "경고: 가상 환경(ape_venv)을 찾을 수 없습니다."
    exit 1
fi

# 인자 파싱
MODE="external"  # 기본값: 외부망 모드
DEBUG=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --internal)
            MODE="internal"
            shift
            ;;
        --external)
            MODE="external"
            shift
            ;;
        --debug)
            DEBUG=true
            shift
            ;;
        *)
            echo "알 수 없는 옵션: $1"
            echo "사용법: $0 [--internal|--external] [--debug]"
            exit 1
            ;;
    esac
done

# 모드 표시
echo "실행 모드: ${MODE^^}"

# Python 스크립트 실행
if [ "$DEBUG" = true ]; then
    echo "디버그 모드 활성화"
    python run.py --mode "$MODE" --debug
else
    python run.py --mode "$MODE"
fi

# 가상 환경 비활성화
deactivate