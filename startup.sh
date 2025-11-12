#!/bin/bash
# Azure App Service 시작 스크립트 (Python 직접 배포용)

set -e

echo "🚀 UiPath MCP Server 시작 중..."

# 작업 디렉토리 이동
cd /home/site/wwwroot/backend

# 데이터베이스 디렉토리 생성
mkdir -p /home/database
mkdir -p /home/logs

# Python 의존성 설치 (첫 실행 시)
if [ ! -d ".venv" ]; then
    echo "📦 Python 가상환경 생성 중..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

# 환경 변수 확인
echo "환경 설정:"
echo "  API_HOST: ${API_HOST:-0.0.0.0}"
echo "  API_PORT: ${API_PORT:-8000}"
echo "  WEBSITES_PORT: ${WEBSITES_PORT:-8000}"
echo "  DB_PATH: ${DB_PATH:-database/mcp_servers.db}"

# 서버 시작
echo "✅ 서버 시작..."
exec python -m src.main
