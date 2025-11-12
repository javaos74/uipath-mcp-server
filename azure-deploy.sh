#!/bin/bash
# Azure App Service 배포 스크립트 (Docker Container)

set -e

# 색상 출력
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🚀 Azure App Service 배포 (Docker Container)${NC}"
echo "=================================================="

# 설정 확인
if [ -z "$AZURE_RESOURCE_GROUP" ]; then
    echo -e "${RED}❌ AZURE_RESOURCE_GROUP 환경 변수가 설정되지 않았습니다.${NC}"
    echo "다음 명령어로 설정하세요:"
    echo "  export AZURE_RESOURCE_GROUP=presales-apac-k"
    exit 1
fi

if [ -z "$AZURE_APP_NAME" ]; then
    echo -e "${RED}❌ AZURE_APP_NAME 환경 변수가 설정되지 않았습니다.${NC}"
    echo "다음 명령어로 설정하세요:"
    echo "  export AZURE_APP_NAME=uipath-mcp"
    exit 1
fi

if [ -z "$AZURE_REGISTRY" ]; then
    echo -e "${YELLOW}⚠️  AZURE_REGISTRY가 설정되지 않았습니다. Azure Container Registry를 사용하려면 설정하세요.${NC}"
    echo "예: export AZURE_REGISTRY=charlescr.azurecr.io"
fi

# 버전 가져오기
VERSION=$(./get-version.sh)
IMAGE_NAME="uipath-mcp-server"

echo ""
echo "배포 설정:"
echo "  Resource Group: ${AZURE_RESOURCE_GROUP}"
echo "  App Name: ${AZURE_APP_NAME}"
echo "  Image: ${IMAGE_NAME}:${VERSION}"
echo "  Registry: ${AZURE_REGISTRY:-Docker Hub}"
echo ""

# 1. 프론트엔드 빌드
echo -e "${YELLOW}📦 프론트엔드 빌드 중...${NC}"
./build.sh

# 2. Docker 이미지 빌드
echo -e "${YELLOW}🔨 Docker 이미지 빌드 중...${NC}"
docker build -t ${IMAGE_NAME}:${VERSION} .

# 3. Azure Container Registry에 푸시 (선택사항)
if [ -n "$AZURE_REGISTRY" ]; then
    echo -e "${YELLOW}📤 Azure Container Registry에 푸시 중...${NC}"
    
    # ACR 로그인
    az acr login --name $(echo $AZURE_REGISTRY | cut -d'.' -f1)
    
    # 이미지 태그
    docker tag ${IMAGE_NAME}:${VERSION} ${AZURE_REGISTRY}/${IMAGE_NAME}:${VERSION}
    docker tag ${IMAGE_NAME}:${VERSION} ${AZURE_REGISTRY}/${IMAGE_NAME}:latest
    
    # 푸시
    docker push ${AZURE_REGISTRY}/${IMAGE_NAME}:${VERSION}
    docker push ${AZURE_REGISTRY}/${IMAGE_NAME}:latest
    
    FULL_IMAGE="${AZURE_REGISTRY}/${IMAGE_NAME}:${VERSION}"
else
    echo -e "${YELLOW}⚠️  Docker Hub 사용 (공개 이미지)${NC}"
    FULL_IMAGE="${IMAGE_NAME}:${VERSION}"
fi

# 4. App Service 생성 또는 업데이트
echo -e "${YELLOW}🌐 App Service 배포 중...${NC}"

# App Service Plan 확인
PLAN_NAME="${AZURE_APP_NAME}-plan"
if ! az appservice plan show --name $PLAN_NAME --resource-group $AZURE_RESOURCE_GROUP &> /dev/null; then
    echo "App Service Plan 생성 중..."
    az appservice plan create \
        --name $PLAN_NAME \
        --resource-group $AZURE_RESOURCE_GROUP \
        --is-linux \
        --sku B1
fi

# ACR 자격 증명 가져오기 (ACR 사용 시)
if [ -n "$AZURE_REGISTRY" ]; then
    echo -e "${YELLOW}🔐 ACR 자격 증명 가져오는 중...${NC}"
    ACR_NAME=$(echo $AZURE_REGISTRY | cut -d'.' -f1)
    ACR_USERNAME=$(az acr credential show --name $ACR_NAME --query username -o tsv)
    ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query passwords[0].value -o tsv)
fi

# Web App 생성 또는 업데이트
if ! az webapp show --name $AZURE_APP_NAME --resource-group $AZURE_RESOURCE_GROUP &> /dev/null; then
    echo "Web App 생성 중..."
    az webapp create \
        --name $AZURE_APP_NAME \
        --resource-group $AZURE_RESOURCE_GROUP \
        --plan $PLAN_NAME \
        --deployment-container-image-name $FULL_IMAGE
else
    echo "Web App 업데이트 중..."
    az webapp config container set \
        --name $AZURE_APP_NAME \
        --resource-group $AZURE_RESOURCE_GROUP \
        --docker-custom-image-name $FULL_IMAGE
fi

# ACR 자격 증명 설정 (ACR 사용 시)
if [ -n "$AZURE_REGISTRY" ]; then
    echo -e "${YELLOW}🔑 ACR 자격 증명 설정 중...${NC}"
    az webapp config container set \
        --name $AZURE_APP_NAME \
        --resource-group $AZURE_RESOURCE_GROUP \
        --docker-registry-server-url https://${AZURE_REGISTRY} \
        --docker-registry-server-user $ACR_USERNAME \
        --docker-registry-server-password $ACR_PASSWORD
fi

# 5. 환경 변수 설정
echo -e "${YELLOW}⚙️  환경 변수 설정 중...${NC}"
az webapp config appsettings set \
    --name $AZURE_APP_NAME \
    --resource-group $AZURE_RESOURCE_GROUP \
    --settings \
        API_HOST=0.0.0.0 \
        API_PORT=8000 \
        WEBSITES_PORT=8000 \
        DB_PATH=/app/database/mcp_servers.db \
        LOG_LEVEL=INFO

# 6. 지속적 배포 활성화 (ACR 사용 시)
if [ -n "$AZURE_REGISTRY" ]; then
    echo -e "${YELLOW}🔄 지속적 배포 활성화 중...${NC}"
    az webapp deployment container config \
        --name $AZURE_APP_NAME \
        --resource-group $AZURE_RESOURCE_GROUP \
        --enable-cd true
fi

echo ""
echo -e "${GREEN}✅ 배포 완료!${NC}"
echo ""
echo "앱 URL: https://${AZURE_APP_NAME}.azurewebsites.net"
echo ""
echo "로그 확인:"
echo "  az webapp log tail --name $AZURE_APP_NAME --resource-group $AZURE_RESOURCE_GROUP"
