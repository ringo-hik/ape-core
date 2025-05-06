@echo off
echo APE Core 내부망 빌드 실행

REM 환경 변수 파일 확인
set ENV_FILE=.env
if not exist %ENV_FILE% (
    echo 환경 변수 파일 생성
    copy .env.example %ENV_FILE%
    echo NETWORK_MODE=internal>> %ENV_FILE%
)

REM 필요한 패키지 설치
echo 필요한 패키지 설치 중...
pip install -r requirements.txt

REM 내부망 모드 설정
echo 내부망 모드로 설정
powershell -Command "(Get-Content %ENV_FILE%) -replace '^NETWORK_MODE=.*', 'NETWORK_MODE=internal' | Set-Content %ENV_FILE%"

REM 실행
echo APE Core 서비스 실행
python run.py --mode internal

echo 내부망 빌드 완료