#!/bin/bash
# Docker 멀티 아키텍처 빌드 스크립트
# x86-64 (amd64) 및 ARM64 (arm64) 지원

set -e

# 설정
IMAGE_NAME="uipath-mcp-server"
PROJECT_VERSION=$(./get-version.sh)
VERSION="${1:-$PROJECT_VERSION}"
REGISTRY="${DOCKER_REGISTRY:-}"  # 예: docker.io/username 또는 ghcr.io/username

# 색상 출력
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🐳 UiPath MCP Server - 멀티 아키텍처 Docker 빌드${NC}"
echo "=================================================="

# 프론트엔드 빌드 확인
if [ ! -d "backend/static" ] || [ -z "$(ls -A backend/static 2>/dev/null)" ]; then
    echo -e "${YELLOW}⚠️  프론트엔드가 빌드되지 않았습니다.${NC}"
    echo ""
    read -p "지금 프론트엔드를 빌드하시겠습니까? (y/n): " build_frontend
    
    if [ "$build_frontend" = "y" ] || [ "$build_frontend" = "Y" ]; then
        echo -e "${YELLOW}🔨 프론트엔드 빌드 중...${NC}"
        ./build.sh
        echo ""
    else
        echo -e "${RED}❌ 프론트엔드 빌드가 필요합니다.${NC}"
        echo "다음 명령어를 먼저 실행하세요:"
        echo "  ./build.sh"
        exit 1
    fi
fi

echo -e "${GREEN}✅ 프론트엔드 빌드 확인 완료${NC}"
echo ""

# Docker Buildx 확인
if ! docker buildx version &> /dev/null; then
    echo -e "${RED}❌ Docker Buildx가 설치되어 있지 않습니다.${NC}"
    echo "Docker Desktop을 최신 버전으로 업데이트하거나 다음 명령어로 설치하세요:"
    echo "  docker buildx install"
    exit 1
fi

# Buildx 빌더 확인 및 사용
if docker buildx inspect multiarch-builder &> /dev/null; then
    echo -e "${GREEN}✅ 기존 멀티 아키텍처 빌더 사용${NC}"
    docker buildx use multiarch-builder
else
    echo -e "${YELLOW}📦 멀티 아키텍처 빌더 생성 중...${NC}"
    # 권한 문제 방지를 위해 기본 드라이버 사용
    if docker buildx create --name multiarch-builder --driver docker-container --use 2>/dev/null; then
        docker buildx inspect --bootstrap
        echo -e "${GREEN}✅ 빌더 생성 완료${NC}"
    else
        echo -e "${YELLOW}⚠️  빌더 생성 실패, 기본 빌더 사용${NC}"
        docker buildx use default
    fi
fi

# 이미지 태그 설정
if [ -n "$REGISTRY" ]; then
    FULL_IMAGE_NAME="${REGISTRY}/${IMAGE_NAME}"
else
    FULL_IMAGE_NAME="${IMAGE_NAME}"
fi

echo ""
echo "빌드 설정:"
echo "  이미지 이름: ${FULL_IMAGE_NAME}"
echo "  프로젝트 버전: ${PROJECT_VERSION}"
echo "  Docker 태그: ${VERSION}"
echo "  아키텍처: linux/amd64, linux/arm64"
echo ""

# 빌드 옵션 선택
echo "빌드 옵션을 선택하세요:"
echo "  1) 로컬 빌드 (테스트용, 현재 아키텍처만)"
echo "  2) 멀티 아키텍처 빌드 및 레지스트리 푸시"
echo "  3) 멀티 아키텍처 빌드 및 로컬 저장 (tar 파일)"
read -p "선택 (1-3): " choice

case $choice in
    1)
        echo -e "${YELLOW}🔨 로컬 빌드 시작...${NC}"
        docker buildx build \
            --platform linux/$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/') \
            --tag ${FULL_IMAGE_NAME}:${VERSION} \
            --tag ${FULL_IMAGE_NAME}:latest \
            --load \
            .
        echo -e "${GREEN}✅ 로컬 빌드 완료!${NC}"
        echo ""
        echo "실행 방법:"
        echo "  docker run -p 8000:8000 ${FULL_IMAGE_NAME}:${VERSION}"
        ;;
    
    2)
        if [ -z "$REGISTRY" ]; then
            echo -e "${RED}❌ 레지스트리가 설정되지 않았습니다.${NC}"
            echo "환경 변수를 설정하세요:"
            echo "  export DOCKER_REGISTRY=docker.io/username"
            echo "또는:"
            echo "  export DOCKER_REGISTRY=ghcr.io/username"
            exit 1
        fi
        
        echo -e "${YELLOW}🔨 멀티 아키텍처 빌드 및 푸시 시작...${NC}"
        docker buildx build \
            --platform linux/amd64,linux/arm64 \
            --tag ${FULL_IMAGE_NAME}:${VERSION} \
            --tag ${FULL_IMAGE_NAME}:latest \
            --push \
            .
        echo -e "${GREEN}✅ 빌드 및 푸시 완료!${NC}"
        echo ""
        echo "이미지 Pull 방법:"
        echo "  docker pull ${FULL_IMAGE_NAME}:${VERSION}"
        ;;
    
    3)
        echo -e "${YELLOW}🔨 멀티 아키텍처 빌드 및 로컬 저장 시작...${NC}"
        OUTPUT_DIR="./docker-images"
        mkdir -p ${OUTPUT_DIR}
        
        docker buildx build \
            --platform linux/amd64,linux/arm64 \
            --tag ${FULL_IMAGE_NAME}:${VERSION} \
            --output type=docker,dest=${OUTPUT_DIR}/${IMAGE_NAME}-${VERSION}.tar \
            .
        
        echo -e "${GREEN}✅ 빌드 완료!${NC}"
        echo ""
        echo "이미지 파일 위치: ${OUTPUT_DIR}/${IMAGE_NAME}-${VERSION}.tar"
        echo ""
        echo "이미지 로드 방법:"
        echo "  docker load < ${OUTPUT_DIR}/${IMAGE_NAME}-${VERSION}.tar"
        ;;
    
    *)
        echo -e "${RED}❌ 잘못된 선택입니다.${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}🎉 완료!${NC}"
