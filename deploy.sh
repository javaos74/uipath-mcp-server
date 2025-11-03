#!/bin/bash
# 고객사 배포용 스크립트

set -e

echo "🚀 UiPath MCP Server 배포 스크립트"
echo "=================================="

# 시스템 요구사항 확인
echo "📋 시스템 요구사항 확인 중..."

# Python 버전 확인
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3.11+ 가 필요합니다."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.11"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "❌ Python $REQUIRED_VERSION 이상이 필요합니다. 현재 버전: $PYTHON_VERSION"
    exit 1
fi

# Node.js 확인 (빌드용)
if ! command -v node &> /dev/null; then
    echo "❌ Node.js 18+ 가 필요합니다."
    exit 1
fi

echo "✅ 시스템 요구사항 충족"

# 가상환경 생성
echo "🐍 Python 가상환경 설정 중..."
cd backend
python3 -m venv .venv
source .venv/bin/activate

# Python 의존성 설치
echo "📦 Python 의존성 설치 중..."
pip install --upgrade pip
pip install -r requirements.txt

cd ..

# 프론트엔드 빌드
echo "🔨 프론트엔드 빌드 중..."
cd frontend
npm install
npm run build
cd ..

# 환경 설정 파일 생성
echo "⚙️  환경 설정 파일 생성 중..."
if [ ! -f backend/.env ]; then
    cp backend/.env.example backend/.env
    echo "📝 backend/.env 파일이 생성되었습니다. 필요에 따라 수정해주세요."
fi

# 데이터베이스 디렉토리 생성
mkdir -p backend/database

echo ""
echo "✅ 배포 완료!"
echo ""
echo "🚀 서버 실행 방법:"
echo "  cd backend"
echo "  source .venv/bin/activate"
echo "  python -m src.main"
echo ""
echo "🌐 접속 URL: http://localhost:8000"
echo ""
echo "📖 자세한 사용법은 README.md를 참고하세요."