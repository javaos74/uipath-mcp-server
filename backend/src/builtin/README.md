# Built-in Tools

이 디렉토리는 MCP 서버에서 사용할 수 있는 Python 기반 Built-in tool을 포함합니다.

## 구조

```
builtin/
├── __init__.py          # 모듈 초기화
├── executor.py          # Tool 실행 엔진
├── google_search.py     # Google 검색 tool
└── README.md           # 이 파일
```

## Built-in Tool 추가하기

### 1. Python 함수 작성

새로운 tool을 추가하려면 이 디렉토리에 Python 파일을 생성하고 async 함수를 작성합니다:

```python
# my_tool.py
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

async def my_tool_function(
    param1: str,
    param2: int,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Tool 설명.
    
    Args:
        param1: 첫 번째 매개변수
        param2: 두 번째 매개변수
        api_key: API 키 (선택사항, builtin_tools 테이블에서 자동 전달)
        
    Returns:
        실행 결과를 포함하는 딕셔너리
    """
    try:
        # Tool 로직 구현
        result = f"Processed: {param1} with {param2}"
        
        return {
            "success": True,
            "result": result
        }
    except Exception as e:
        logger.error(f"Error in my_tool: {e}")
        return {
            "success": False,
            "error": str(e)
        }
```

### 2. __init__.py에 등록

```python
# __init__.py
from .my_tool import my_tool_function

__all__ = ["google_search", "my_tool_function"]
```

### 3. 데이터베이스에 등록

관리자 페이지(`/admin/builtin-tools`)에서 tool을 등록하거나 스크립트를 사용:

```python
tool_data = {
    "name": "my_tool",
    "description": "내 도구 설명",
    "input_schema": {
        "type": "object",
        "properties": {
            "param1": {
                "type": "string",
                "description": "첫 번째 매개변수"
            },
            "param2": {
                "type": "integer",
                "description": "두 번째 매개변수"
            }
        },
        "required": ["param1", "param2"]
    },
    "python_function": "src.builtin.my_tool.my_tool_function",
    "api_key": None  # 필요한 경우 API 키 설정
}

tool_id = await db.create_builtin_tool(**tool_data)
```

## 기존 Tool

### google_search

Google 검색을 수행하는 샘플 tool입니다.

**매개변수:**
- `q` (string, required): 검색 질문

**함수 경로:** `src.builtin.google_search.google_search`

**API 키:** Google Custom Search API 키 (선택사항)

**사용 예시:**
```json
{
  "q": "Python programming"
}
```

**응답 예시:**
```json
{
  "success": true,
  "query": "Python programming",
  "results": [
    {
      "title": "Sample result",
      "link": "https://example.com",
      "snippet": "Result description"
    }
  ]
}
```

## Tool 실행 흐름

1. MCP 클라이언트가 tool 호출
2. `mcp_server.py`가 tool 정보 조회
3. `tool_type`이 'builtin'인 경우:
   - `builtin_tool_id`로 built-in tool 정보 조회
   - `executor.execute_builtin_tool()` 호출
   - Python 함수 동적 import 및 실행
   - 결과 반환

## 테스트

Built-in tool을 테스트하려면:

```bash
python backend/scripts/test_builtin_tool.py
```

## 주의사항

1. **함수 시그니처**: 모든 built-in tool 함수는 `api_key` 매개변수를 선택적으로 받아야 합니다.
2. **반환 값**: 항상 딕셔너리를 반환하고 `success` 필드를 포함해야 합니다.
3. **에러 처리**: 예외를 적절히 처리하고 에러 정보를 반환해야 합니다.
4. **비동기**: 가능하면 async 함수로 작성하세요 (동기 함수도 지원됨).
5. **로깅**: 적절한 로깅을 추가하여 디버깅을 용이하게 하세요.

## API 키 관리

Built-in tool이 외부 서비스를 사용하는 경우:

1. 관리자 페이지에서 tool 편집
2. API Key 필드에 키 입력
3. 함수 실행 시 `api_key` 매개변수로 자동 전달

API 키는 데이터베이스에 저장되며, tool 실행 시에만 함수에 전달됩니다.
