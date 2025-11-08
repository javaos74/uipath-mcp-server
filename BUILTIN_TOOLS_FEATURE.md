# Built-in Tools Feature

## 개요

이 브랜치(`feat-builtin-tools`)는 UiPath Orchestrator 프로세스 외에도 Python으로 개발된 built-in tool을 MCP 서버에 추가할 수 있는 기능을 구현합니다.

## 주요 변경사항

### 1. 데이터베이스 스키마

#### 새로운 테이블: `builtin_tools`
```sql
CREATE TABLE builtin_tools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT NOT NULL,
    input_schema TEXT NOT NULL,
    python_function TEXT NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

#### `mcp_tools` 테이블 업데이트
- `tool_type` 필드 추가: 'uipath' 또는 'builtin'
- `builtin_tool_id` 필드 추가: builtin_tools 테이블에 대한 외래 키

### 2. API 엔드포인트

#### Built-in Tools 관리 (관리자 전용)

- `GET /api/builtin-tools` - Built-in tool 목록 조회
  - Query parameter: `active_only` (기본값: true)
  
- `POST /api/builtin-tools` - Built-in tool 생성 (관리자 전용)
  ```json
  {
    "name": "tool_name",
    "description": "Tool description",
    "input_schema": {
      "type": "object",
      "properties": {...}
    },
    "python_function": "module.function_name"
  }
  ```

- `GET /api/builtin-tools/{tool_id}` - Built-in tool 상세 조회

- `PUT /api/builtin-tools/{tool_id}` - Built-in tool 수정 (관리자 전용)

- `DELETE /api/builtin-tools/{tool_id}` - Built-in tool 삭제 (관리자 전용)

#### Tool 등록 업데이트

`POST /api/servers/{tenant_name}/{server_name}/tools` 엔드포인트가 이제 두 가지 타입의 tool을 지원합니다:

**UiPath Tool:**
```json
{
  "name": "process_name",
  "description": "Process description",
  "input_schema": {...},
  "tool_type": "uipath",
  "uipath_process_name": "ProcessName",
  "uipath_process_key": "process_key",
  "uipath_folder_path": "/folder/path",
  "uipath_folder_id": "folder_id"
}
```

**Built-in Tool:**
```json
{
  "name": "tool_name",
  "description": "Tool description",
  "input_schema": {...},
  "tool_type": "builtin",
  "builtin_tool_id": 1
}
```

### 3. 데이터베이스 함수

새로운 Built-in tool 관리 함수들이 `Database` 클래스에 추가되었습니다:

- `create_builtin_tool()` - Built-in tool 생성
- `get_builtin_tool()` - ID로 Built-in tool 조회
- `get_builtin_tool_by_name()` - 이름으로 Built-in tool 조회
- `list_builtin_tools()` - Built-in tool 목록 조회
- `update_builtin_tool()` - Built-in tool 수정
- `delete_builtin_tool()` - Built-in tool 삭제

기존 tool 관리 함수들이 `tool_type`과 `builtin_tool_id` 파라미터를 지원하도록 업데이트되었습니다.

### 4. Pydantic 모델

새로운 모델:
- `BuiltinToolCreate` - Built-in tool 생성 요청
- `BuiltinToolUpdate` - Built-in tool 수정 요청
- `BuiltinToolResponse` - Built-in tool 응답

업데이트된 모델:
- `ToolCreate` - `tool_type`, `builtin_tool_id` 필드 추가
- `ToolUpdate` - `tool_type`, `builtin_tool_id` 필드 추가
- `ToolResponse` - `tool_type`, `builtin_tool_id` 필드 추가

## 사용 시나리오

### 1. Built-in Tool 등록 (관리자)

1. 관리자가 Python으로 개발된 tool을 built-in tool로 등록
2. Tool의 이름, 설명, input schema, Python 함수 경로를 지정
3. 등록된 built-in tool은 모든 사용자가 자신의 MCP 서버에 추가 가능

### 2. MCP 서버에 Tool 추가

사용자는 Tool 등록 화면에서:
1. **Tool Type 선택**: UiPath Orchestrator 또는 Built-in Tool
2. **UiPath 선택 시**: 기존과 동일하게 프로세스 선택
3. **Built-in 선택 시**: 등록된 built-in tool 목록에서 선택

### 3. Tool 실행

- UiPath tool: UiPath Orchestrator에서 프로세스 실행
- Built-in tool: Python 함수 직접 실행 (향후 구현 예정)

## 다음 단계

1. **Built-in Tool 실행 로직 구현**
   - Python 함수를 동적으로 로드하고 실행하는 메커니즘
   - 보안 샌드박스 환경 구성

2. **프론트엔드 UI 개선**
   - Tool 등록 화면에서 tool type 선택 UI
   - Built-in tool 관리 화면 (관리자용)
   - Built-in tool 목록 표시

3. **샘플 Built-in Tools 개발**
   - 기본 제공 tool 예제 (예: 텍스트 처리, 데이터 변환 등)

4. **테스트 및 문서화**
   - API 테스트 작성
   - 사용자 가이드 작성

## 마이그레이션

기존 데이터베이스는 자동으로 마이그레이션됩니다:
- 기존 `mcp_tools` 레코드는 `tool_type='uipath'`로 설정됨
- 새로운 컬럼이 자동으로 추가됨
- 데이터 손실 없음

## 보안 고려사항

- Built-in tool 생성/수정/삭제는 관리자만 가능
- Built-in tool 조회는 모든 인증된 사용자 가능
- Python 함수 실행 시 보안 샌드박스 필요 (향후 구현)
