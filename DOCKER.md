# Docker 빌드 및 배포 가이드

## 개요

이 프로젝트는 멀티 아키텍처 Docker 이미지를 지원합니다:
- **linux/amd64** (x86-64) - Intel/AMD 프로세서
- **linux/arm64** (ARM64) - Apple Silicon, AWS Graviton 등

## 빠른 시작

### 1. 프론트엔드 빌드

Docker 이미지 빌드 전에 프론트엔드를 먼저 빌드해야 합니다:

```bash
./build.sh
```

### 2. Docker 이미지 빌드

```bash
./docker-build.sh
```

빌드 스크립트가 자동으로:
- 프론트엔드 빌드 여부 확인
- `backend/pyproject.toml`에서 버전 추출
- 빌드 옵션 선택 메뉴 제공

## 빌드 옵션

### 옵션 1: 로컬 테스트 빌드

현재 아키텍처만 빌드하여 로컬에서 테스트:

```bash
./docker-build.sh
# 선택: 1
```

결과: `uipath-mcp-server:0.2.7` (로컬 Docker에 로드됨)

### 옵션 2: 멀티 아키텍처 빌드 + 레지스트리 푸시

```bash
export DOCKER_REGISTRY=docker.io/username
./docker-build.sh
# 선택: 2
```

결과: `docker.io/username/uipath-mcp-server:0.2.7` (amd64 + arm64)

### 옵션 3: 멀티 아키텍처 빌드 + 로컬 저장

```bash
./docker-build.sh
# 선택: 3
```

결과: `./docker-images/uipath-mcp-server-0.2.7.tar`

## 레지스트리별 푸시 방법

### Docker Hub

```bash
# 로그인
docker login

# 빌드 및 푸시
export DOCKER_REGISTRY=docker.io/username
./docker-build.sh
# 선택: 2
```

### GitHub Container Registry (GHCR)

```bash
# 로그인
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# 빌드 및 푸시
export DOCKER_REGISTRY=ghcr.io/username
./docker-build.sh
# 선택: 2
```

### AWS ECR

```bash
# 로그인
aws ecr get-login-password --region ap-northeast-2 | \
  docker login --username AWS --password-stdin ACCOUNT_ID.dkr.ecr.ap-northeast-2.amazonaws.com

# 빌드 및 푸시
export DOCKER_REGISTRY=ACCOUNT_ID.dkr.ecr.ap-northeast-2.amazonaws.com
./docker-build.sh
# 선택: 2
```

### Azure Container Registry (ACR)

```bash
# 로그인
az acr login --name myregistry

# 빌드 및 푸시
export DOCKER_REGISTRY=myregistry.azurecr.io
./docker-build.sh
# 선택: 2
```

## 특정 버전으로 빌드

```bash
# pyproject.toml 버전 대신 지정된 버전 사용
./docker-build.sh v1.0.0
```

## 수동 멀티 아키텍처 빌드

스크립트 없이 직접 빌드하려면:

```bash
# 1. Buildx 빌더 생성
docker buildx create --name multiarch-builder --use
docker buildx inspect --bootstrap

# 2. 멀티 아키텍처 빌드 및 푸시
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag username/uipath-mcp-server:latest \
  --push \
  .
```

## 이미지 실행

### Docker 직접 실행

```bash
docker run -d \
  --name uipath-mcp-server \
  -p 8000:8000 \
  -v $(pwd)/data/database:/app/database \
  -v $(pwd)/data/logs:/app/logs \
  uipath-mcp-server:latest
```

### Docker Compose 사용

```bash
docker-compose up -d
```

## 문제 해결

### Buildx 빌더 문제

```bash
# 빌더 재생성
docker buildx rm multiarch-builder
docker buildx create --name multiarch-builder --driver docker-container --use
docker buildx inspect --bootstrap
```

### 이미지 확인

```bash
# 이미지 아키텍처 확인
docker manifest inspect username/uipath-mcp-server:latest
```

### 로그 확인

```bash
docker logs -f uipath-mcp-server
```
