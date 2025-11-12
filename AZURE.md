# Azure App Service 배포 가이드

## 개요

UiPath MCP Server를 Azure App Service에 배포하는 방법을 설명합니다.

## 사전 요구사항

### 필수 도구
- **Azure CLI**: Azure 리소스 관리
  ```bash
  # macOS
  brew install azure-cli
  
  # Windows
  winget install Microsoft.AzureCLI
  
  # Linux
  curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
  ```

- **Docker**: 컨테이너 배포 시 필요
- **Azure 구독**: 활성화된 Azure 계정

### Azure CLI 로그인
```bash
az login
az account set --subscription "your-subscription-id"
```

## 배포 방법

### 방법 1: Docker Container 배포 (권장) ⭐

#### 장점
- ✅ 로컬 환경과 동일한 실행 환경
- ✅ 의존성 관리 간편
- ✅ 빠른 배포 및 롤백
- ✅ 멀티 아키텍처 지원

#### 1-A. Azure Container Registry 사용 (프라이빗)

```bash
# 1. Azure Container Registry 생성
az acr create \
  --name yourregistry \
  --resource-group your-resource-group \
  --sku Basic \
  --admin-enabled true

# 2. 환경 변수 설정
export AZURE_RESOURCE_GROUP=your-resource-group
export AZURE_APP_NAME=uipath-mcp-server
export AZURE_REGISTRY=yourregistry.azurecr.io

# 3. 자동 배포 실행
./azure-deploy.sh
```

#### 1-B. Docker Hub 사용 (퍼블릭)

```bash
# 1. Docker Hub에 이미지 푸시
export DOCKER_REGISTRY=docker.io/username
./docker-build.sh
# 선택: 2 (멀티 아키텍처 빌드 및 푸시)

# 2. App Service 생성
az webapp create \
  --name uipath-mcp-server \
  --resource-group your-resource-group \
  --plan your-app-service-plan \
  --deployment-container-image-name username/uipath-mcp-server:0.2.0

# 3. 환경 변수 설정
az webapp config appsettings set \
  --name uipath-mcp-server \
  --resource-group your-resource-group \
  --settings \
    API_HOST=0.0.0.0 \
    API_PORT=8000 \
    WEBSITES_PORT=8000 \
    DB_PATH=/home/database/mcp_servers.db \
    LOG_LEVEL=INFO
```

### 방법 2: Python 직접 배포

#### 장점
- ✅ Docker 없이 배포 가능
- ✅ Azure의 관리형 Python 런타임 사용

#### 단계

```bash
# 1. 프론트엔드 빌드
./build.sh

# 2. App Service 생성 (Python 3.11)
az webapp up \
  --name uipath-mcp-server \
  --resource-group your-resource-group \
  --runtime "PYTHON:3.11" \
  --sku B1

# 3. 시작 명령 설정
az webapp config set \
  --name uipath-mcp-server \
  --resource-group your-resource-group \
  --startup-file "startup.sh"

# 4. 환경 변수 설정
az webapp config appsettings set \
  --name uipath-mcp-server \
  --resource-group your-resource-group \
  --settings \
    API_HOST=0.0.0.0 \
    API_PORT=8000 \
    DB_PATH=/home/database/mcp_servers.db \
    LOG_LEVEL=INFO
```

## 데이터베이스 지속성

### Azure Files 마운트 (권장)

```bash
# 1. Storage Account 생성
az storage account create \
  --name yourstorageaccount \
  --resource-group your-resource-group \
  --sku Standard_LRS

# 2. File Share 생성
az storage share create \
  --name uipath-mcp-data \
  --account-name yourstorageaccount

# 3. App Service에 마운트
az webapp config storage-account add \
  --name uipath-mcp-server \
  --resource-group your-resource-group \
  --custom-id database \
  --storage-type AzureFiles \
  --share-name uipath-mcp-data \
  --account-name yourstorageaccount \
  --mount-path /home/database \
  --access-key $(az storage account keys list \
    --account-name yourstorageaccount \
    --query '[0].value' -o tsv)
```

### Azure SQL Database (선택사항)

SQLite 대신 Azure SQL을 사용하려면 코드 수정이 필요합니다.

## 환경 변수 설정

### 필수 환경 변수

```bash
az webapp config appsettings set \
  --name uipath-mcp-server \
  --resource-group your-resource-group \
  --settings \
    API_HOST=0.0.0.0 \
    API_PORT=8000 \
    WEBSITES_PORT=8000 \
    DB_PATH=/app/database/mcp_servers.db \
    LOG_LEVEL=INFO \
    SECRET_KEY="your-secret-key-here"
```

**환경 변수 설명:**

- **API_HOST**: 애플리케이션이 바인딩할 호스트 (0.0.0.0 = 모든 인터페이스)
- **API_PORT**: 애플리케이션이 리스닝할 포트 번호
- **WEBSITES_PORT**: Azure가 컨테이너에 연결할 포트 (Docker 배포 시 필수)
  - Azure의 로드 밸런서가 이 포트로 트래픽 전달
  - API_PORT와 동일한 값으로 설정
- **DB_PATH**: SQLite 데이터베이스 파일 경로
  - Docker 배포: `/app/database/mcp_servers.db`
  - Python 직접 배포: `/home/site/wwwroot/backend/database/mcp_servers.db`
- **LOG_LEVEL**: 로깅 레벨 (DEBUG, INFO, WARNING, ERROR)
- **SECRET_KEY**: JWT 토큰 서명용 시크릿 키 (프로덕션에서 반드시 변경)

### 선택적 환경 변수

```bash
az webapp config appsettings set \
  --name uipath-mcp-server \
  --resource-group your-resource-group \
  --settings \
    TOOL_CALL_TIMEOUT=600 \
    UIPATH_OAUTH_SCOPE="OR.Folders.Read OR.Releases.Read OR.Jobs.Read" \
    UIPATH_OAUTH_AUDIENCE="https://orchestrator.uipath.com"
```

## 스케일링

### 수직 스케일링 (Scale Up)

```bash
# App Service Plan 업그레이드
az appservice plan update \
  --name your-app-service-plan \
  --resource-group your-resource-group \
  --sku P1V2
```

### 수평 스케일링 (Scale Out)

```bash
# 인스턴스 수 증가
az appservice plan update \
  --name your-app-service-plan \
  --resource-group your-resource-group \
  --number-of-workers 3
```

### 자동 스케일링

```bash
# 자동 스케일 규칙 생성
az monitor autoscale create \
  --name uipath-mcp-autoscale \
  --resource-group your-resource-group \
  --resource /subscriptions/{subscription-id}/resourceGroups/{resource-group}/providers/Microsoft.Web/serverfarms/{plan-name} \
  --min-count 1 \
  --max-count 5 \
  --count 2

# CPU 기반 스케일 아웃
az monitor autoscale rule create \
  --autoscale-name uipath-mcp-autoscale \
  --resource-group your-resource-group \
  --condition "Percentage CPU > 70 avg 5m" \
  --scale out 1
```

## 모니터링 및 로깅

### 로그 스트리밍

```bash
# 실시간 로그 확인
az webapp log tail \
  --name uipath-mcp-server \
  --resource-group your-resource-group
```

### Application Insights 연동

```bash
# Application Insights 생성
az monitor app-insights component create \
  --app uipath-mcp-insights \
  --location eastus \
  --resource-group your-resource-group

# App Service에 연결
INSTRUMENTATION_KEY=$(az monitor app-insights component show \
  --app uipath-mcp-insights \
  --resource-group your-resource-group \
  --query instrumentationKey -o tsv)

az webapp config appsettings set \
  --name uipath-mcp-server \
  --resource-group your-resource-group \
  --settings \
    APPINSIGHTS_INSTRUMENTATIONKEY=$INSTRUMENTATION_KEY
```

### 헬스 체크 설정

```bash
az webapp config set \
  --name uipath-mcp-server \
  --resource-group your-resource-group \
  --health-check-path "/health"
```

## 보안 설정

### HTTPS 강제

```bash
az webapp update \
  --name uipath-mcp-server \
  --resource-group your-resource-group \
  --https-only true
```

### 커스텀 도메인 및 SSL

```bash
# 커스텀 도메인 추가
az webapp config hostname add \
  --webapp-name uipath-mcp-server \
  --resource-group your-resource-group \
  --hostname yourdomain.com

# 관리형 SSL 인증서 생성
az webapp config ssl create \
  --name uipath-mcp-server \
  --resource-group your-resource-group \
  --hostname yourdomain.com
```

### IP 제한

```bash
# 특정 IP만 허용
az webapp config access-restriction add \
  --name uipath-mcp-server \
  --resource-group your-resource-group \
  --rule-name "Office IP" \
  --action Allow \
  --ip-address 203.0.113.0/24 \
  --priority 100
```

## CI/CD 설정

### GitHub Actions

`.github/workflows/azure-deploy.yml` 파일 생성:

```yaml
name: Deploy to Azure App Service

on:
  push:
    branches: [ main ]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Build frontend
      run: ./build.sh
    
    - name: Log in to Azure
      uses: azure/login@v1
      with:
        creds: ${{ secrets.AZURE_CREDENTIALS }}
    
    - name: Build and push Docker image
      run: |
        az acr build \
          --registry ${{ secrets.AZURE_REGISTRY }} \
          --image uipath-mcp-server:${{ github.sha }} \
          --image uipath-mcp-server:latest \
          .
    
    - name: Deploy to App Service
      run: |
        az webapp config container set \
          --name ${{ secrets.AZURE_APP_NAME }} \
          --resource-group ${{ secrets.AZURE_RESOURCE_GROUP }} \
          --docker-custom-image-name ${{ secrets.AZURE_REGISTRY }}/uipath-mcp-server:${{ github.sha }}
```

## 비용 최적화

### 개발/테스트 환경

```bash
# Free 또는 Basic 티어 사용
az appservice plan create \
  --name dev-plan \
  --resource-group your-resource-group \
  --sku B1 \
  --is-linux
```

### 프로덕션 환경

```bash
# Premium V2 티어 (더 나은 성능)
az appservice plan create \
  --name prod-plan \
  --resource-group your-resource-group \
  --sku P1V2 \
  --is-linux
```

### 예약 인스턴스

장기 사용 시 예약 인스턴스로 최대 72% 절감 가능

## 문제 해결

### 일반적인 문제

#### 1. 컨테이너 시작 실패
```bash
# 로그 확인
az webapp log tail --name uipath-mcp-server --resource-group your-resource-group

# 컨테이너 설정 확인
az webapp config show --name uipath-mcp-server --resource-group your-resource-group
```

#### 2. 데이터베이스 권한 오류
```bash
# 파일 시스템 권한 확인
az webapp ssh --name uipath-mcp-server --resource-group your-resource-group
ls -la /home/database
```

#### 3. 포트 바인딩 오류
```bash
# WEBSITES_PORT 환경 변수 확인
az webapp config appsettings list \
  --name uipath-mcp-server \
  --resource-group your-resource-group \
  --query "[?name=='WEBSITES_PORT']"
```

## 백업 및 복구

### 자동 백업 설정

```bash
# 백업 설정
az webapp config backup create \
  --resource-group your-resource-group \
  --webapp-name uipath-mcp-server \
  --backup-name initial-backup \
  --container-url "https://yourstorageaccount.blob.core.windows.net/backups?{SAS-token}"
```

## 참고 자료

- [Azure App Service 문서](https://docs.microsoft.com/azure/app-service/)
- [Azure Container Registry](https://docs.microsoft.com/azure/container-registry/)
- [Azure CLI 참조](https://docs.microsoft.com/cli/azure/)
- [App Service 가격](https://azure.microsoft.com/pricing/details/app-service/)
