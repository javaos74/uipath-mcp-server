# MCP Client - Docker 사용 가이드

MCP Client를 Docker 컨테이너로 실행하는 방법을 설명합니다.

## 🐳 빠른 시작

### 1. Docker Compose 사용 (권장)

```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 편집 (OpenAI API Key 필수)
# OPENAI_API_KEY=sk-your-key-here

# 컨테이너 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f
```

브라우저에서 `http://localhost:8000` 접속

### 2. Docker 직접 실행

```bash
docker run -d \
  --name uipath-mcp-client \
  -p 8000:8000 \
  -e OPENAI_API_KEY=sk-your-key-here \
  -e MCP_SERVER_URL=http://host.docker.internal:8000/mcp/tenant/server/sse \
  -e MCP_SERVER_TOKEN=your-token \
  uipath-mcp-client:latest
```

## 🔨 Docker 이미지 빌드

### 로컬 빌드 (테스트용)

```bash
./docker-build.sh
# 옵션 1 선택: 로컬 빌드
```

### 멀티 아키텍처 빌드 및 푸시

```bash
# Docker Registry 설정
export DOCKER_REGISTRY=docker.io/yourusername
# 또는
export DOCKER_REGISTRY=ghcr.io/yourusername

# 빌드 및 푸시
./docker-build.sh 0.1.0
# 옵션 2 선택: 멀티 아키텍처 빌드 및 푸시
```

지원 아키텍처:
- `linux/amd64` (x86-64)
- `linux/arm64` (ARM64, Apple Silicon)

## ⚙️ 환경 변수

### 필수 환경 변수

| 변수 | 설명 | 예시 |
|------|------|------|
| `OPENAI_API_KEY` | OpenAI API 키 | `sk-proj-...` |

### 선택적 환경 변수

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `MCP_SERVER_URL` | MCP 서버 URL | - |
| `MCP_SERVER_TOKEN` | MCP 서버 토큰 | - |
| `CHAINLIT_HOST` | Chainlit 호스트 | `0.0.0.0` |
| `CHAINLIT_PORT` | Chainlit 포트 | `8000` |
| `CHAINLIT_AUTH_SECRET` | 인증 시크릿 키 | - |

## 📦 Docker Compose 설정

### 기본 설정

```yaml
version: '3.8'

services:
  mcpclient:
    image: uipath-mcp-client:latest
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - MCP_SERVER_URL=${MCP_SERVER_URL}
      - MCP_SERVER_TOKEN=${MCP_SERVER_TOKEN}
    volumes:
      - chainlit-data:/app/.chainlit
    restart: unless-stopped

volumes:
  chainlit-data:
```

### MCP Server와 함께 실행

```yaml
version: '3.8'

services:
  # MCP Server
  mcp-server:
    image: uipath-mcp-server:latest
    ports:
      - "8001:8000"
    environment:
      - DB_PATH=/app/database/mcp_servers.db
    volumes:
      - mcp-data:/app/database
    networks:
      - mcp-network

  # MCP Client
  mcp-client:
    image: uipath-mcp-client:latest
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - MCP_SERVER_URL=http://mcp-server:8000/mcp/tenant/server/sse
      - MCP_SERVER_TOKEN=${MCP_SERVER_TOKEN}
    depends_on:
      - mcp-server
    networks:
      - mcp-network

volumes:
  mcp-data:

networks:
  mcp-network:
    driver: bridge
```

## 🔍 문제 해결

### 컨테이너 로그 확인

```bash
# Docker Compose
docker-compose logs -f mcpclient

# Docker 직접 실행
docker logs -f uipath-mcp-client
```

### 컨테이너 내부 접속

```bash
# Docker Compose
docker-compose exec mcpclient /bin/bash

# Docker 직접 실행
docker exec -it uipath-mcp-client /bin/bash
```

### Health Check 확인

```bash
# Docker Compose
docker-compose ps

# Docker 직접 실행
docker inspect --format='{{.State.Health.Status}}' uipath-mcp-client
```

### 일반적인 문제

#### 1. OpenAI API Key 오류

```
Error: OpenAI API key not configured
```

**해결**: `.env` 파일에 `OPENAI_API_KEY` 설정 확인

#### 2. MCP Server 연결 실패

```
Error: Failed to connect to MCP server
```

**해결**:
- MCP Server가 실행 중인지 확인
- `MCP_SERVER_URL`이 올바른지 확인
- Docker 네트워크 설정 확인 (`host.docker.internal` 사용)

#### 3. 포트 충돌

```
Error: Bind for 0.0.0.0:8000 failed: port is already allocated
```

**해결**: 다른 포트 사용
```bash
docker run -p 8080:8000 ...
```

## 🚀 프로덕션 배포

### Azure Container Instances

```bash
az container create \
  --resource-group myResourceGroup \
  --name mcp-client \
  --image yourusername/uipath-mcp-client:latest \
  --dns-name-label mcp-client \
  --ports 8000 \
  --environment-variables \
    OPENAI_API_KEY=sk-your-key \
    MCP_SERVER_URL=https://your-mcp-server.com/sse \
    MCP_SERVER_TOKEN=your-token
```

### AWS ECS / Fargate

```json
{
  "family": "mcp-client",
  "containerDefinitions": [
    {
      "name": "mcp-client",
      "image": "yourusername/uipath-mcp-client:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "OPENAI_API_KEY",
          "value": "sk-your-key"
        },
        {
          "name": "MCP_SERVER_URL",
          "value": "https://your-mcp-server.com/sse"
        }
      ]
    }
  ]
}
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-client
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mcp-client
  template:
    metadata:
      labels:
        app: mcp-client
    spec:
      containers:
      - name: mcp-client
        image: yourusername/uipath-mcp-client:latest
        ports:
        - containerPort: 8000
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: mcp-secrets
              key: openai-api-key
        - name: MCP_SERVER_URL
          value: "http://mcp-server:8000/mcp/tenant/server/sse"
---
apiVersion: v1
kind: Service
metadata:
  name: mcp-client
spec:
  selector:
    app: mcp-client
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

## 📝 참고 자료

- [Chainlit Documentation](https://docs.chainlit.io/)
- [Docker Documentation](https://docs.docker.com/)
- [MCP Protocol](https://modelcontextprotocol.io/)
