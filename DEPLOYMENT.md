# UiPath MCP Server 배포 가이드

## 시스템 요구사항

### 필수 소프트웨어
- **Python 3.11+** - 백엔드 실행용
- **Node.js 18+** - 프론트엔드 빌드용 (배포 시에만 필요)
- **Git** - 소스 코드 다운로드용

### 운영체제 지원
- ✅ Linux (Ubuntu 20.04+, CentOS 8+)
- ✅ Windows 10/11
- ✅ macOS 12+

## 배포 방법

### 방법 1: 자동 배포 스크립트 (권장)

```bash
# 1. 소스 코드 다운로드
git clone <repository-url>
cd uipath-mcp-server

# 2. 자동 배포 실행
./deploy.sh
```

### 방법 2: 수동 배포

```bash
# 1. 백엔드 환경 설정
cd backend
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. 프론트엔드 빌드
cd ../frontend
npm install
npm run build

# 3. 환경 설정
cd ../backend
cp .env.example .env
# .env 파일을 편집하여 필요한 설정 변경

# 4. 데이터베이스 디렉토리 생성
mkdir -p database
```

## 실행 방법

### 개발/테스트 환경
```bash
cd backend
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m src.main
```

### 프로덕션 환경 (systemd 서비스)

1. **서비스 파일 생성** (`/etc/systemd/system/uipath-mcp.service`):
```ini
[Unit]
Description=UiPath MCP Server
After=network.target

[Service]
Type=simple
User=uipath-mcp
WorkingDirectory=/opt/uipath-mcp-server/backend
Environment=PATH=/opt/uipath-mcp-server/backend/.venv/bin
ExecStart=/opt/uipath-mcp-server/backend/.venv/bin/python -m src.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

2. **서비스 활성화**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable uipath-mcp
sudo systemctl start uipath-mcp
```

## 환경 설정

### 필수 설정 (.env 파일)

```bash
# 서버 설정
API_HOST=0.0.0.0
API_PORT=8000

# 보안 설정 (프로덕션에서 반드시 변경)
SECRET_KEY=your-secret-key-here

# 데이터베이스
DB_PATH=database/mcp_servers.db

# 로깅
LOG_LEVEL=INFO

# UiPath 설정
TOOL_CALL_TIMEOUT=600
```

### 선택적 설정

```bash
# OAuth 기본 설정
UIPATH_OAUTH_SCOPE=OR.Folders.Read OR.Releases.Read OR.Jobs.Read
UIPATH_OAUTH_AUDIENCE=https://orchestrator.uipath.com
```

## 네트워크 설정

### 방화벽 포트 개방
- **8000/tcp** - 웹 UI 및 API 접근용
- **443/tcp** - UiPath 서버 연결용 (아웃바운드)

### 프록시 설정 (선택사항)

Nginx 설정 예시:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # SSE 연결을 위한 특별 설정
    location /mcp/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # SSE 지원
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
    }
}
```

## 보안 고려사항

### 1. 인증서 설정
- **개발환경**: HTTP 사용 가능
- **프로덕션**: HTTPS 필수 (Let's Encrypt 권장)

### 2. 데이터베이스 보안
- SQLite 파일 권한: `600` (소유자만 읽기/쓰기)
- 정기 백업 설정

### 3. 로그 관리
- 로그 파일 위치: `backend/logs/`
- 로그 로테이션 설정 권장

## 문제 해결

### 일반적인 문제

1. **포트 충돌**
   ```bash
   # 다른 포트 사용
   API_PORT=8080 python -m src.main
   ```

2. **권한 문제**
   ```bash
   # 파일 권한 확인
   chmod 600 backend/.env
   chmod 600 backend/database/mcp_servers.db
   ```

3. **UiPath 연결 실패**
   - UiPath URL 형식 확인
   - 네트워크 연결 확인
   - 인증 정보 확인

### 로그 확인
```bash
# 실시간 로그 확인
tail -f backend/logs/server.log

# 서비스 로그 확인 (systemd)
sudo journalctl -u uipath-mcp -f
```

## 업데이트 방법

```bash
# 1. 서비스 중지
sudo systemctl stop uipath-mcp

# 2. 코드 업데이트
git pull origin main

# 3. 의존성 업데이트
cd backend
source .venv/bin/activate
pip install -r requirements.txt

# 4. 프론트엔드 재빌드
cd ../frontend
npm install
npm run build

# 5. 서비스 재시작
sudo systemctl start uipath-mcp
```

## 지원 및 문의

- **문서**: README.md 참고
- **로그 위치**: `backend/logs/`
- **설정 파일**: `backend/.env`