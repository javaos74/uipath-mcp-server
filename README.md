# UiPath Dynamic MCP Server

HTTP Streamable MCP 서버로 여러 MCP 엔드포인트를 동적으로 생성하고, 각 엔드포인트에 MCP Tool을 등록하여 UiPath RPA 프로세스를 실행할 수 있습니다.

## 프로젝트 구조

```
.
├── backend/              # Python/FastAPI 백엔드
│   ├── src/             # 소스 코드
│   ├── tests/           # 테스트
│   └── pyproject.toml   # Python 프로젝트 설정
├── frontend/            # React/TypeScript 프론트엔드 (예정)
├── docs/                # 문서
└── README.md
```

## 특징

- **동적 MCP 엔드포인트 생성**: `/mcp/{tenant_name}/{server_name}` 형식의 엔드포인트를 동적으로 생성
- **MCP Tool 명세 준수**: MCP 표준 Tool 스펙에 맞는 도구 등록
- **HTTP Streamable (SSE)**: 표준 MCP 프로토콜을 HTTP/SSE로 노출
- **사용자 인증**: JWT 토큰 기반 인증 시스템
- **역할 기반 접근 제어**: User/Admin 역할 구분
- **UiPath 통합**: 각 Tool을 UiPath RPA 프로세스와 연결
- **개인 PAT 관리**: 사용자별 UiPath Personal Access Token 저장

## 빠른 시작

### 백엔드 실행

```bash
# 백엔드 디렉토리로 이동
cd backend

# 가상환경 생성 및 활성화
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 의존성 설치
uv pip install -e .

# 환경 변수 설정
cp .env.example .env
# .env 파일을 편집하여 필요한 값 설정

# 서버 실행
python -m src.main
```

서버가 http://localhost:8000 에서 실행됩니다.

### 프론트엔드 실행 (예정)

```bash
cd frontend
npm install
npm run dev
```

## API 사용 예시

### 1. 사용자 등록 및 로그인

```bash
# 사용자 등록
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john",
    "email": "john@example.com",
    "password": "password123",
    "role": "user"
  }'

# 로그인
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john",
    "password": "password123"
  }'
```

### 2. UiPath 설정

```bash
# UiPath PAT 저장
curl -X PUT http://localhost:8000/auth/uipath-config \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "uipath_url": "https://cloud.uipath.com/account/tenant",
    "uipath_access_token": "YOUR_UIPATH_PAT",
    "uipath_folder_path": "/Production/Finance"
  }'
```

### 3. MCP 서버 생성

```bash
# MCP 서버 엔드포인트 생성
curl -X POST http://localhost:8000/api/servers \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "tenant_name": "production",
    "server_name": "finance-automation",
    "description": "Finance automation MCP server"
  }'
```

### 4. Tool 등록

```bash
# Tool 등록 (MCP Tool 명세 준수)
curl -X POST http://localhost:8000/api/servers/production/finance-automation/tools \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "name": "process_invoice",
    "description": "Process invoice and extract data",
    "input_schema": {
      "type": "object",
      "properties": {
        "invoice_path": {
          "type": "string",
          "description": "Path to invoice file"
        },
        "auto_approve": {
          "type": "boolean",
          "description": "Auto-approve processed invoices"
        }
      },
      "required": ["invoice_path"]
    },
    "uipath_process_name": "InvoiceProcessing",
    "uipath_folder_path": "/Production/Finance"
  }'
```

### 5. MCP 클라이언트 연결

```python
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

async with sse_client(
    "http://localhost:8000/mcp/production/finance-automation",
    headers={"Authorization": "Bearer YOUR_TOKEN"}
) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        
        # 사용 가능한 도구 목록
        tools = await session.list_tools()
        print(tools)
        
        # Tool 실행
        result = await session.call_tool(
            "process_invoice",
            {"invoice_path": "/data/invoice.pdf", "auto_approve": True}
        )
        print(result)
```

## 데이터베이스 스키마

### users
사용자 정보 및 UiPath 설정

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    is_active BOOLEAN DEFAULT 1,
    uipath_url TEXT,
    uipath_access_token TEXT,
    uipath_folder_path TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### mcp_servers
MCP 서버 엔드포인트

```sql
CREATE TABLE mcp_servers (
    id INTEGER PRIMARY KEY,
    tenant_name TEXT NOT NULL,
    server_name TEXT NOT NULL,
    description TEXT,
    user_id INTEGER NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(tenant_name, server_name)
);
```

### mcp_tools
MCP Tool 정의

```sql
CREATE TABLE mcp_tools (
    id INTEGER PRIMARY KEY,
    server_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    input_schema TEXT NOT NULL,
    uipath_process_name TEXT,
    uipath_folder_path TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (server_id) REFERENCES mcp_servers(id),
    UNIQUE(server_id, name)
);
```

## API 엔드포인트

### 인증
- `POST /auth/register` - 사용자 등록
- `POST /auth/login` - 로그인 (JWT 토큰 발급)
- `GET /auth/me` - 현재 사용자 정보
- `PUT /auth/uipath-config` - UiPath 설정 업데이트

### MCP 서버 관리
- `GET /api/servers` - 서버 목록
- `POST /api/servers` - 서버 생성
- `GET /api/servers/{tenant}/{server}` - 서버 조회
- `PUT /api/servers/{tenant}/{server}` - 서버 수정
- `DELETE /api/servers/{tenant}/{server}` - 서버 삭제

### MCP Tool 관리
- `GET /api/servers/{tenant}/{server}/tools` - Tool 목록
- `POST /api/servers/{tenant}/{server}/tools` - Tool 생성
- `GET /api/servers/{tenant}/{server}/tools/{tool}` - Tool 조회
- `PUT /api/servers/{tenant}/{server}/tools/{tool}` - Tool 수정
- `DELETE /api/servers/{tenant}/{server}/tools/{tool}` - Tool 삭제

### MCP 프로토콜
- `GET /mcp/{tenant}/{server}` - MCP SSE 연결 (인증 필요)

### Health Check
- `GET /health` - 서버 상태 확인

## 권한 관리

### User 역할
- 자신이 생성한 서버만 조회/수정/삭제 가능
- 자신의 서버에만 Tool 추가/수정/삭제 가능
- 자신의 서버에만 MCP 연결 가능

### Admin 역할
- 모든 서버 조회/수정/삭제 가능
- 모든 서버의 Tool 관리 가능
- 모든 서버에 MCP 연결 가능

## 문서

- [토큰 인증 가이드](docs/TOKEN_AUTHENTICATION.md)
- [백엔드 README](backend/README.md)

## 개발

### 테스트

```bash
cd backend
source .venv/bin/activate

# 모든 테스트 실행
pytest tests/ -v

# 특정 테스트
python tests/test_auth.py
python tests/test_server_management.py
python tests/test_tool_management.py
```

### 코드 품질

```bash
# 포맷팅
ruff format backend/src/

# 린팅
ruff check backend/src/

# 타입 체크
mypy backend/src/
```

## 유틸리티 스크립트

`backend/scripts/` 디렉토리에는 테스트, 디버깅, 관리를 위한 유틸리티 스크립트가 있습니다.

### ⚠️ 중요: 실행 위치

**모든 스크립트는 프로젝트 루트 디렉토리에서 실행해야 합니다.**

```bash
# ✅ 올바른 방법 - 프로젝트 루트에서 실행
cd /path/to/uipath-mcp
python backend/scripts/script_name.py

# ❌ 잘못된 방법 - backend/ 또는 backend/scripts/에서 실행하지 마세요
cd backend/scripts
python script_name.py  # 실패합니다!
```

### 주요 스크립트

- **인증 테스트**: `python backend/scripts/test_mcp_authentication.py`
- **토큰 관리**: `python backend/scripts/test_token_api.py`
- **데이터베이스 디버그**: `python backend/scripts/debug_mcp_access.py`
- **UiPath 연동 테스트**: `python backend/scripts/debug_uipath_api.py`
- **라이브 연결 테스트**: `python backend/scripts/test_live_connection.py`

자세한 내용은 [`backend/scripts/README.md`](backend/scripts/README.md)를 참조하세요.

## 라이선스

MIT

## 기여

Pull Request를 환영합니다!
