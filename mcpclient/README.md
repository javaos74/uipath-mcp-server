# MCP Client with Chainlit

Chainlit 기반의 MCP (Model Context Protocol) 클라이언트입니다.

## 기능

- OpenAI LLM 통합 (Function Calling 지원)
- 여러 MCP 서버 연결 (SSE 기반)
- 파일 업로드 및 처리
- 채팅 세션 관리
- 실시간 도구 실행 및 결과 표시

## 설치

```bash
pip install -r requirements.txt
```

## 환경 설정

### 방법 1: UI에서 설정 (권장)

1. 애플리케이션 실행:
```bash
chainlit run app.py -w
```

2. 브라우저에서 `http://localhost:8000` 접속

3. 설정 화면에서:
   - `/settings` 명령으로 OpenAI API 키 입력
   - `/servers` 명령으로 MCP 서버 추가 (URL과 토큰)

### 방법 2: 파일로 설정

#### 1. config.json 파일 생성

샘플 파일을 복사하여 시작:
```bash
cp config.json.example config.json
```

#### 2. OpenAI API 키 설정

`config.json` 파일을 열고 `openai_api_key` 필드에 API 키 입력:
```json
{
  "openai_api_key": "sk-proj-your-actual-api-key-here",
  "mcpServers": {}
}
```

또는 `.env` 파일 사용:
```bash
cp .env.example .env
```

`.env` 파일에 추가:
```
OPENAI_API_KEY=sk-proj-your-actual-api-key-here
```

#### 3. MCP 서버 설정

`config.json`의 `mcpServers` 섹션에 서버 추가:

**Azure 배포 서버 예시:**
```json
{
  "openai_api_key": "sk-proj-...",
  "mcpServers": {
    "uipath-mcp": {
      "url": "https://uipath-mcp.azurewebsites.net/mcp/UiPath/DemoMCP/sse",
      "token": "your_bearer_token_here",
      "headers": {},
      "timeout": 30,
      "sse_read_timeout": 300,
      "enabled": true
    }
  }
}
```

**로컬 서버 예시:**
```json
{
  "openai_api_key": "sk-proj-...",
  "mcpServers": {
    "local-server": {
      "url": "http://localhost:3000/mcp/your-tenant/your-server/sse",
      "token": "your_bearer_token_here",
      "headers": {},
      "timeout": 30,
      "sse_read_timeout": 300,
      "enabled": true
    }
  }
}
```

**여러 서버 동시 사용:**
```json
{
  "openai_api_key": "sk-proj-...",
  "mcpServers": {
    "production": {
      "url": "https://prod-server.com/mcp/tenant/server/sse",
      "token": "prod_token",
      "enabled": true
    },
    "development": {
      "url": "http://localhost:3000/mcp/dev/test/sse",
      "token": "dev_token",
      "enabled": true
    },
    "disabled-server": {
      "url": "http://old-server.com/sse",
      "token": "old_token",
      "enabled": false
    }
  }
}
```

#### 4. 설정 옵션 설명

| 필드 | 필수 | 설명 | 기본값 |
|------|------|------|--------|
| `url` | ✅ | SSE 엔드포인트 URL | - |
| `token` | ❌ | Bearer 인증 토큰 | null |
| `headers` | ❌ | 추가 HTTP 헤더 | {} |
| `timeout` | ❌ | HTTP 요청 타임아웃 (초) | 30 |
| `sse_read_timeout` | ❌ | SSE 읽기 타임아웃 (초) | 300 |
| `enabled` | ❌ | 서버 활성화 여부 | true |

## 실행

### 기본 실행
```bash
chainlit run app.py -w
```

기본 포트: `http://localhost:8000`

### 포트 변경
```bash
chainlit run app.py -w -p 8080
```

### 외부 접속 허용
```bash
chainlit run app.py -w -h 0.0.0.0
```

## 사용 방법

### 명령어
- `/settings` - OpenAI API 키 설정
- `/servers` - MCP 서버 관리 (추가/삭제)
- `/tools` - 사용 가능한 도구 목록 보기
- `/new` - 새 채팅 시작

### 첫 실행 시
1. 애플리케이션이 자동으로 설정 화면을 표시합니다
2. OpenAI API 키를 입력하세요
3. `/servers` 명령으로 MCP 서버를 추가하세요

### 파일 업로드
채팅 입력창에서 파일을 드래그 앤 드롭하거나 파일 아이콘을 클릭하여 업로드할 수 있습니다.

### 도구 사용
AI가 자동으로 필요한 도구를 선택하고 실행합니다. 도구 실행 과정과 결과가 실시간으로 표시됩니다.

## 토큰 발급 방법

### Backend MCP 서버 토큰 발급

1. Backend 서버 실행:
```bash
cd backend
python -m uvicorn src.main:app --port 3000
```

2. 웹 브라우저에서 `http://localhost:3000` 접속

3. 로그인 후 MCP 서버 관리 페이지에서 토큰 발급

4. 발급받은 토큰을 `config.json`에 입력

## 문제 해결

### 서버 연결 오류

**증상:** `SSEError: Expected response header Content-Type to contain 'text/event-stream'`

**원인:**
- MCP 서버가 실행되지 않음
- 잘못된 URL
- 포트 충돌

**해결:**
1. MCP 서버가 실행 중인지 확인
2. URL이 정확한지 확인 (특히 `/sse` 경로)
3. 포트 번호 확인

### 인증 오류

**증상:** 401 Unauthorized 또는 403 Forbidden

**원인:**
- 잘못된 토큰
- 만료된 토큰

**해결:**
1. 토큰을 다시 발급받아 `config.json` 업데이트
2. `enabled: true`로 설정되어 있는지 확인

### API 키 오류

**증상:** OpenAI API 오류

**해결:**
1. `/settings` 명령으로 API 키 확인
2. OpenAI 계정에서 API 키 유효성 확인
3. 사용량 한도 확인
