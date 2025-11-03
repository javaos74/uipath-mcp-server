# Docker 배포 가이드

## 멀티 아키텍처 지원

이 프로젝트는 다음 아키텍처를 지원합니다:
- **linux/amd64** (x86-64) - Intel/AMD 프로세서
- **linux/arm64** (ARM64) - Apple Silicon, AWS Graviton 등

## 빠른 시작

### 사전 준비: 프론트엔드 빌드

Docker 이미지를 빌드하기 전에 **반드시** 프론트엔드를 먼저 빌드해야 합니다:

```bash
# 프론트엔드 빌드 (backend/static/ 디렉토리에 생성됨)
./build.sh
```

### 방법 1: Docker Compose 사용 (권장)

```bash
# 1. 프론트엔드 빌드
./build.sh

# 2. 환경 설정 파일 생성
cp backend/.env.example .env
# .env 파일 편집 (필요시)

# 3. 서비스 시작
docker-compose up -d

# 3. 로그 확인
docker-compose logs -f

# 4. 서비스 중지
docker-compose down
```

### 방법 2: Docker 직접 사용

```bash
# 1. 프론트엔드 빌드
./build.sh

# 2. 이미지 빌드
docker build -t uipath-mcp-server:latest .

# 2. 컨테이너 실행
docker run -d \
  --name uipath-mcp-server \
  -p 8000:8000 \
  -v $(pwd)/data/database:/app/database \
  -v $(pwd)/data/logs:/app/logs \
  uipath-mcp-server:latest

# 3. 로그 확인
docker logs -f uipath-mcp-server

# 4. 컨테이너 중지
docker stop uipath-mcp-server
docker rm uipath-mcp-server
```

## 멀티 아키텍처 빌드

### 사전 요구사항

- Docker Desktop 최신 버전 또는
- Docker Engine + Docker Buildx

### 빌드 스크립트 사용

빌드 스크립트는 자동으로:
- 프론트엔드 빌드 여부 확인 (필요시 빌드 제안)
- `backend/pyproject.toml`에서 버전 자동 추출

```bash
# 1. 로컬 테스트 빌드 (현재 아키텍처만, 자동 버전)
./docker-build.sh
# 프론트엔드 빌드 확인 후 선택: 1
# 결과: uipath-mcp-server:0.1.0 (pyproject.toml 버전 사용)

# 2. 특정 버전으로 빌드
./docker-build.sh v1.0.0
# 결과: uipath-mcp-server:v1.0.0

# 3. 멀티 아키텍처 빌드 및 레지스트리 푸시
export DOCKER_REGISTRY=docker.io/username
./docker-build.sh
# 선택: 2
# 결과: docker.io/username/uipath-mcp-server:0.1.0

# 4. 멀티 아키텍처 빌드 및 로컬 저장
./docker-build.sh
# 선택: 3
```

**버전 관리:**
- 인자 없이 실행: `pyproject.toml`의 버전 사용
- 인자와 함께 실행: 지정된 버전 사용
- 버전 확인: `./get-version.sh`

### 수동 멀티 아키텍처 빌드

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

# 3. 로컬 저장 (tar 파일)
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag uipath-mcp-server:latest \
  --output type=docker,dest=./uipath-mcp-server.tar \
  .
```

## 레지스트리별 푸시 방법

### Docker Hub

```bash
# 1. 로그인
docker login

# 2. 빌드 및 푸시
export DOCKER_REGISTRY=docker.io/username
./docker-build.sh v1.0.0
```

### GitHub Container Registry (GHCR)

```bash
# 1. 로그인
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# 2. 빌드 및 푸시
export DOCKER_REGISTRY=ghcr.io/username
./docker-build.sh v1.0.0
```

### AWS ECR

```bash
# 1. 로그인
aws ecr get-login-password --region region | \
  docker login --username AWS --password-stdin account-id.dkr.ecr.region.amazonaws.com

# 2. 빌드 및 푸시
export DOCKER_REGISTRY=account-id.dkr.ecr.region.amazonaws.com
./docker-build.sh v1.0.0
```

## 환경 변수 설정

### .env 파일 예시

```bash
# 서버 설정
API_HOST=0.0.0.0
API_PORT=8000

# 보안 (프로덕션에서 반드시 변경)
SECRET_KEY=your-secret-key-here

# 데이터베이스
DB_PATH=database/mcp_servers.db

# 로깅
LOG_LEVEL=INFO

# UiPath 설정
TOOL_CALL_TIMEOUT=600
```

### Docker Compose 환경 변수

```yaml
environment:
  - API_HOST=0.0.0.0
  - API_PORT=8000
  - SECRET_KEY=${SECRET_KEY}
  - DB_PATH=database/mcp_servers.db
  - LOG_LEVEL=INFO
```

## 볼륨 관리

### 데이터 지속성

```bash
# 데이터 디렉토리 생성
mkdir -p data/database data/logs

# 권한 설정
chmod 755 data/database data/logs
```

### 백업

```bash
# 데이터베이스 백업
docker exec uipath-mcp-server \
  cp /app/database/mcp_servers.db /app/database/mcp_servers.db.backup

# 호스트로 복사
docker cp uipath-mcp-server:/app/database/mcp_servers.db.backup \
  ./backup/mcp_servers-$(date +%Y%m%d).db
```

## 프로덕션 배포

### Kubernetes 배포 예시

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: uipath-mcp-server
spec:
  replicas: 2
  selector:
    matchLabels:
      app: uipath-mcp-server
  template:
    metadata:
      labels:
        app: uipath-mcp-server
    spec:
      containers:
      - name: uipath-mcp-server
        image: username/uipath-mcp-server:latest
        ports:
        - containerPort: 8000
        env:
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: uipath-mcp-secrets
              key: secret-key
        volumeMounts:
        - name: database
          mountPath: /app/database
        - name: logs
          mountPath: /app/logs
      volumes:
      - name: database
        persistentVolumeClaim:
          claimName: uipath-mcp-database
      - name: logs
        persistentVolumeClaim:
          claimName: uipath-mcp-logs
---
apiVersion: v1
kind: Service
metadata:
  name: uipath-mcp-server
spec:
  selector:
    app: uipath-mcp-server
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

## 문제 해결

### 컨테이너 로그 확인

```bash
# 실시간 로그
docker logs -f uipath-mcp-server

# 최근 100줄
docker logs --tail 100 uipath-mcp-server
```

### 컨테이너 내부 접근

```bash
docker exec -it uipath-mcp-server /bin/bash
```

### 헬스 체크 확인

```bash
curl http://localhost:8000/health
```

### 이미지 크기 최적화

```bash
# 이미지 크기 확인
docker images uipath-mcp-server

# 불필요한 레이어 제거
docker image prune -a
```

## 보안 고려사항

1. **시크릿 관리**: 환경 변수로 민감한 정보 전달
2. **네트워크 격리**: Docker 네트워크 사용
3. **읽기 전용 파일시스템**: 가능한 경우 적용
4. **최소 권한**: non-root 사용자로 실행 (향후 개선)
5. **정기 업데이트**: 베이스 이미지 및 의존성 업데이트

## 성능 최적화

### 멀티 스테이지 빌드

현재 Dockerfile은 멀티 스테이지 빌드를 사용하여:
- 프론트엔드 빌드 레이어 분리
- 최종 이미지 크기 최소화
- 빌드 캐시 최적화

### 레이어 캐싱

```bash
# 의존성만 변경된 경우 빠른 재빌드
docker build --cache-from uipath-mcp-server:latest -t uipath-mcp-server:latest .
```

## 참고 자료

- [Docker Buildx 문서](https://docs.docker.com/buildx/working-with-buildx/)
- [멀티 아키텍처 이미지](https://docs.docker.com/build/building/multi-platform/)
- [Docker Compose 문서](https://docs.docker.com/compose/)
