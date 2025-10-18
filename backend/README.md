# UiPath Dynamic MCP Server - Backend

Python/FastAPI 기반 백엔드 서버

## 구조

```
backend/
├── src/                    # 소스 코드
│   ├── __init__.py
│   ├── main.py            # 서버 진입점
│   ├── http_server.py     # HTTP/SSE 서버 (Starlette)
│   ├── mcp_server.py      # MCP 서버 로직
│   ├── database.py        # SQLite 데이터베이스
│   ├── models.py          # Pydantic 모델
│   ├── auth.py            # 인증/권한 관리
│   └── uipath_client.py   # UiPath SDK 래퍼
├── tests/                 # 테스트 코드
│   ├── test_auth.py
│   ├── test_server_management.py
│   └── test_tool_management.py
├── pyproject.toml         # Python 프로젝트 설정
└── mcp.json              # MCP 서버 설정
```

## 설치

```bash
# 가상환경 생성 및 활성화
cd backend
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 의존성 설치
uv pip install -e .
```

## 실행

```bash
cd backend
source .venv/bin/activate
python -m src.main
```

서버가 http://localhost:8000 에서 실행됩니다.

## 테스트

```bash
cd backend
source .venv/bin/activate

# 모든 테스트 실행
pytest tests/ -v

# 특정 테스트 실행
python tests/test_auth.py
python tests/test_server_management.py
python tests/test_tool_management.py
```

## API 문서

서버 실행 후 다음 URL에서 확인:
- Swagger UI: http://localhost:8000/docs (구현 예정)
- ReDoc: http://localhost:8000/redoc (구현 예정)

## 환경 변수

`.env` 파일 생성:

```bash
cp .env.example .env
```

필수 환경 변수:
- `SECRET_KEY`: JWT 토큰 서명 키
- `UIPATH_URL`: UiPath Cloud URL (선택)
- `UIPATH_ACCESS_TOKEN`: UiPath PAT (선택)
- `UIPATH_FOLDER_PATH`: UiPath 폴더 경로 (선택)

## 개발

### 코드 포맷팅

```bash
ruff format src/
```

### 타입 체크

```bash
mypy src/
```
