# UiPath MCP Server Deployment Guide / 배포 가이드

## System Requirements / 시스템 요구사항

### Required Software / 필수 소프트웨어

- **Python 3.11+** - For backend / 백엔드 실행용
- **Node.js 18+** - For frontend build / 프론트엔드 빌드용 (배포 시에만 필요)
- **Git** - For source code download / 소스 코드 다운로드용

### Supported Operating Systems / 운영체제 지원

- ✅ Linux (Ubuntu 20.04+, CentOS 8+)
- ✅ Windows 10/11
- ✅ macOS 12+

## Deployment Methods / 배포 방법

### Method 1: Automated Deployment Script (Recommended) / 자동 배포 스크립트 (권장)

```bash
# 1. Download source code / 소스 코드 다운로드
git clone <repository-url>
cd uipath-mcp-server

# 2. Run automated deployment / 자동 배포 실행
./deploy.sh
```

### Method 2: Manual Deployment / 수동 배포

```bash
# 1. Backend environment setup / 백엔드 환경 설정
cd backend
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Frontend build / 프론트엔드 빌드
cd ../frontend
npm install
npm run build

# 3. Environment configuration / 환경 설정
cd ../backend
cp .env.example .env
# Edit .env file to change required settings
# .env 파일을 편집하여 필요한 설정 변경

# 4. Create database directory / 데이터베이스 디렉토리 생성
mkdir -p database
```

## Running the Server / 실행 방법

### Development/Test Environment / 개발/테스트 환경

```bash
cd backend
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m src.main
```

### Production Environment (systemd service) / 프로덕션 환경 (systemd 서비스)

1. **Create service file / 서비스 파일 생성** (`/etc/systemd/system/uipath-mcp.service`):

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

2. **Enable service / 서비스 활성화**:

```bash
sudo systemctl daemon-reload
sudo systemctl enable uipath-mcp
sudo systemctl start uipath-mcp
```

## Configuration / 환경 설정

### Required Settings (.env file) / 필수 설정 (.env 파일)

```bash
# Server settings / 서버 설정
API_HOST=0.0.0.0
API_PORT=8000

# Security settings (must change in production)
# 보안 설정 (프로덕션에서 반드시 변경)
SECRET_KEY=your-secret-key-here

# Database / 데이터베이스
DB_PATH=database/mcp_servers.db

# Logging / 로깅
LOG_LEVEL=INFO

# UiPath settings / UiPath 설정
TOOL_CALL_TIMEOUT=600
```

### Optional Settings / 선택적 설정

```bash
# OAuth default settings / OAuth 기본 설정
UIPATH_OAUTH_SCOPE=OR.Folders.Read OR.Releases.Read OR.Jobs.Read
UIPATH_OAUTH_AUDIENCE=https://orchestrator.uipath.com
```

## Network Configuration / 네트워크 설정

### Firewall Port Opening / 방화벽 포트 개방

- **8000/tcp** - For Web UI and API access / 웹 UI 및 API 접근용
- **443/tcp** - For UiPath server connection (outbound) / UiPath 서버 연결용 (아웃바운드)

### Proxy Configuration (Optional) / 프록시 설정 (선택사항)

Nginx configuration example / Nginx 설정 예시:

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

    # Special settings for SSE connections
    # SSE 연결을 위한 특별 설정
    location /mcp/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # SSE support / SSE 지원
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
    }
}
```

## Security Considerations / 보안 고려사항

### 1. Certificate Settings / 인증서 설정

- **Development**: HTTP allowed / HTTP 사용 가능
- **Production**: HTTPS required (Let's Encrypt recommended) / HTTPS 필수 (Let's Encrypt 권장)

### 2. Database Security / 데이터베이스 보안

- SQLite file permissions: `600` (owner read/write only) / 소유자만 읽기/쓰기
- Set up regular backups / 정기 백업 설정

### 3. Log Management / 로그 관리

- Log file location / 로그 파일 위치: `backend/logs/`
- Log rotation recommended / 로그 로테이션 설정 권장

## Troubleshooting / 문제 해결

### Common Issues / 일반적인 문제

1. **Port Conflict / 포트 충돌**

   ```bash
   # Use different port / 다른 포트 사용
   API_PORT=8080 python -m src.main
   ```

2. **Permission Issues / 권한 문제**

   ```bash
   # Check file permissions / 파일 권한 확인
   chmod 600 backend/.env
   chmod 600 backend/database/mcp_servers.db
   ```

3. **UiPath Connection Failure / UiPath 연결 실패**
   - Check UiPath URL format / UiPath URL 형식 확인
   - Check network connection / 네트워크 연결 확인
   - Verify authentication credentials / 인증 정보 확인

### Log Checking / 로그 확인

```bash
# Real-time log monitoring / 실시간 로그 확인
tail -f backend/logs/server.log

# Service log (systemd) / 서비스 로그 확인 (systemd)
sudo journalctl -u uipath-mcp -f
```

## Update Method / 업데이트 방법

```bash
# 1. Stop service / 서비스 중지
sudo systemctl stop uipath-mcp

# 2. Update code / 코드 업데이트
git pull origin main

# 3. Update dependencies / 의존성 업데이트
cd backend
source .venv/bin/activate
pip install -r requirements.txt

# 4. Rebuild frontend / 프론트엔드 재빌드
cd ../frontend
npm install
npm run build

# 5. Restart service / 서비스 재시작
sudo systemctl start uipath-mcp
```

## Support / 지원 및 문의

- **Documentation / 문서**: See README.md / README.md 참고
- **Log location / 로그 위치**: `backend/logs/`
- **Configuration file / 설정 파일**: `backend/.env`
