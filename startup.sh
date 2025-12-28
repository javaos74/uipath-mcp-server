#!/bin/bash
# =============================================================================
# UiPath MCP Server Startup Script / 시작 스크립트
# =============================================================================
# This script assumes the source code was cloned using git clone.
# 이 스크립트는 git clone으로 소스 코드를 내려받았다고 가정합니다.
#
# Usage / 사용법:
#   ./startup.sh
#
# Prerequisites / 사전 요구사항:
#   - Python 3.11+
#   - Git
# =============================================================================

set -e

echo "🚀 Starting UiPath MCP Server... / UiPath MCP Server 시작 중..."

# Get the script directory (project root)
# 스크립트 디렉토리 (프로젝트 루트) 가져오기
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

echo "📁 Project root / 프로젝트 루트: $PROJECT_ROOT"

# Change to project root directory
# 프로젝트 루트 디렉토리로 이동
cd "$PROJECT_ROOT"

# Create required directories
# 필요한 디렉토리 생성
echo "📂 Creating directories... / 디렉토리 생성 중..."
mkdir -p "$PROJECT_ROOT/backend/database"
mkdir -p "$PROJECT_ROOT/backend/logs"

# Change to backend directory
# backend 디렉토리로 이동
cd "$PROJECT_ROOT/backend"

# Setup Python virtual environment
# Python 가상환경 설정
if [ ! -d ".venv" ]; then
    echo "📦 Creating Python virtual environment... / Python 가상환경 생성 중..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
    echo "📦 Installing dependencies... / 의존성 설치 중..."
    pip install -r requirements.txt
else
    echo "✅ Using existing virtual environment / 기존 가상환경 사용"
    source .venv/bin/activate
    echo "📦 Checking dependencies... / 의존성 확인 중..."
    pip install -r requirements.txt --quiet
fi

# Display environment configuration
# 환경 설정 표시
echo ""
echo "⚙️  Environment Configuration / 환경 설정:"
echo "   API_HOST: ${API_HOST:-0.0.0.0}"
echo "   API_PORT: ${API_PORT:-8000}"
echo "   DB_PATH: ${DB_PATH:-database/mcp_servers.db}"
echo "   LOG_LEVEL: ${LOG_LEVEL:-INFO}"
echo ""

# Start the server
# 서버 시작
echo "✅ Starting server... / 서버 시작..."
exec python -m src.main
