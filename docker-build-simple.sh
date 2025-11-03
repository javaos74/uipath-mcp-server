#!/bin/bash
# 간단한 Docker 빌드 스크립트 (권한 문제 회피)

set -e

IMAGE_NAME="uipath-mcp-server"
PROJECT_VERSION=$(./get-version.sh)
VERSION="${1:-$PROJECT_VERSION}"

echo "🐳 Docker 이미지 빌드"
echo "===================="
echo "이미지: ${IMAGE_NAME}:${VERSION}"
echo "프로젝트 버전: ${PROJECT_VERSION}"
echo ""

# 프론트엔드 빌드 확인
if [ ! -d "backend/static" ] || [ -z "$(ls -A backend/static 2>/dev/null)" ]; then
    echo "⚠️  프론트엔드가 빌드되지 않았습니다."
    echo "먼저 다음 명령어를 실행하세요:"
    echo "  ./build.sh"
    exit 1
fi

echo "✅ 프론트엔드 빌드 확인 완료"
echo ""

# 현재 아키텍처만 빌드 (빠르고 안전)
echo "🔨 빌드 시작..."
docker build -t ${IMAGE_NAME}:${VERSION} -t ${IMAGE_NAME}:latest .

echo ""
echo "✅ 빌드 완료!"
echo ""
echo "실행 방법:"
echo "  docker run -p 8000:8000 ${IMAGE_NAME}:${VERSION}"
echo ""
echo "또는 Docker Compose 사용:"
echo "  docker-compose up -d"
