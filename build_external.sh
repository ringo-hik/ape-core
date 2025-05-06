#!/bin/bash

echo "APE Core 외부망 빌드 실행"

# 환경 변수 파일 확인
ENV_FILE=".env"
if [ ! -f "$ENV_FILE" ]; then
    echo "환경 변수 파일 생성"
    cp .env.example $ENV_FILE
    echo "NETWORK_MODE=external" >> $ENV_FILE
fi

# 필요한 패키지 설치
echo "필요한 패키지 설치 중..."
pip install -r requirements.txt

# 외부망 모드 설정
echo "외부망 모드로 설정"
sed -i 's/^NETWORK_MODE=.*/NETWORK_MODE=external/' $ENV_FILE

# 실행
echo "APE Core 서비스 실행"
python run.py --mode external

echo "외부망 빌드 완료"