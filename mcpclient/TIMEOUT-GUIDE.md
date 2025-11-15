# MCP Client Timeout 설정 가이드

## 📚 Timeout 종류

mcpclient에는 두 가지 timeout 설정이 있습니다:

### 1. `timeout` (연결 타임아웃)

**용도**: 초기 HTTP 연결 설정 시간 제한

**적용 시점**:
- MCP 서버에 처음 연결할 때
- HTTP 핸드셰이크 과정
- SSE 연결 초기화

**기본값**: 30초

**예시 시나리오**:
```
Client → [연결 시도] → MCP Server
         ↑
         이 과정에 30초 이상 걸리면 타임아웃
```

**언제 늘려야 하나요?**
- ✅ 네트워크가 느린 환경
- ✅ 서버가 멀리 있는 경우 (해외 서버 등)
- ✅ 서버 초기화가 오래 걸리는 경우
- ❌ 도구 실행이 오래 걸리는 경우 (이건 sse_read_timeout)

### 2. `sse_read_timeout` (SSE 읽기 타임아웃)

**용도**: SSE 이벤트 스트림에서 데이터를 기다리는 시간 제한

**적용 시점**:
- 연결이 성공한 후
- 도구(Tool) 실행 중
- 서버로부터 응답을 기다리는 동안
- 장시간 실행되는 작업 처리 중

**기본값**: 3600초 (1시간)

**예시 시나리오**:
```
Client ←→ [연결됨] ←→ MCP Server
         ↓
    [도구 실행 중...]
         ↓
    5분 동안 응답 없으면 타임아웃
```

**언제 늘려야 하나요?**
- ✅ UiPath 프로세스 실행 시간이 긴 경우
- ✅ 대용량 데이터 처리 작업
- ✅ 복잡한 워크플로우 실행
- ✅ 배치 작업 실행

## 🔍 상세 비교

| 항목 | timeout | sse_read_timeout |
|------|---------|------------------|
| **목적** | 연결 수립 | 데이터 수신 대기 |
| **단계** | 연결 초기화 | 연결 후 통신 |
| **기본값** | 30초 | 3600초 (1시간) |
| **일반적 범위** | 10-60초 | 60-600초 (1-10분) |
| **오류 메시지** | "Connection timeout" | "Read timeout" |

## 💡 실제 사용 예시

### 예시 1: 일반 작업 (기본 설정)

```json
{
  "timeout": 30,
  "sse_read_timeout": 3600
}
```

**적합한 경우**:
- 일반적인 UiPath 프로세스 실행
- 대부분의 도구 실행
- 장시간 실행 가능한 작업 (1시간 이내)

### 예시 2: 매우 긴 배치 작업

```json
{
  "timeout": 30,
  "sse_read_timeout": 7200
}
```

**적합한 경우**:
- 1-2시간 실행되는 배치 작업
- 대규모 데이터 처리
- 매우 복잡한 워크플로우

**설명**:
- `timeout`: 30초 - 연결은 빠르게 수립됨
- `sse_read_timeout`: 7200초 (2시간) - 프로세스 실행을 2시간까지 기다림

### 예시 3: 느린 네트워크 환경

```json
{
  "timeout": 60,
  "sse_read_timeout": 3600
}
```

**적합한 경우**:
- 해외 서버 연결
- 느린 네트워크
- VPN 사용 환경

**설명**:
- `timeout`: 60초 - 연결 수립에 더 많은 시간 허용
- `sse_read_timeout`: 3600초 - 일반 작업 시간 유지

### 예시 4: 빠른 작업 (타임아웃 단축)

```json
{
  "timeout": 30,
  "sse_read_timeout": 300
}
```

**적합한 경우**:
- 5분 이내 완료되는 빠른 작업
- 간단한 데이터 조회
- 빠른 API 호출

**설명**:
- `timeout`: 30초 - 연결은 정상
- `sse_read_timeout`: 300초 (5분) - 빠른 작업만 허용

## 🎯 권장 설정

### UiPath 프로세스 실행 시간별 권장값

| 프로세스 실행 시간 | timeout | sse_read_timeout | 설명 |
|-------------------|---------|------------------|------|
| < 1분 | 30 | 120 | 매우 빠른 작업 |
| 1-5분 | 30 | 300 | 빠른 작업 |
| 5-30분 | 30 | 1800 | 중간 작업 |
| 30-60분 | 30 | 3600 | 일반 작업 (기본값) |
| 1-2시간 | 30 | 7200 | 긴 작업 |
| > 2시간 | 30 | 10800 | 매우 긴 배치 작업 |

## 🔧 설정 방법

### config.json에서 설정

```json
{
  "mcpServers": {
    "my-server": {
      "url": "http://localhost:8000/mcp/tenant/server/sse",
      "token": "your-token",
      "timeout": 30,
      "sse_read_timeout": 600,
      "enabled": true
    }
  }
}
```

### 서버별로 다르게 설정

```json
{
  "mcpServers": {
    "quick-tasks": {
      "url": "http://server1/sse",
      "timeout": 30,
      "sse_read_timeout": 120,
      "enabled": true
    },
    "long-running-tasks": {
      "url": "http://server2/sse",
      "timeout": 30,
      "sse_read_timeout": 3600,
      "enabled": true
    }
  }
}
```

## ⚠️ 주의사항

### 1. 너무 짧은 timeout

```json
{
  "timeout": 5,  // ❌ 너무 짧음
  "sse_read_timeout": 30  // ❌ 너무 짧음
}
```

**문제점**:
- 정상적인 작업도 타임아웃 발생
- 불필요한 재시도 증가
- 사용자 경험 저하

### 2. 너무 긴 timeout

```json
{
  "timeout": 300,  // ❌ 불필요하게 김
  "sse_read_timeout": 86400  // ❌ 24시간은 과함
}
```

**문제점**:
- 실제 문제 발생 시 감지가 늦어짐
- 리소스 낭비
- 응답 없는 연결이 오래 유지됨

### 3. 균형잡힌 설정 (권장)

```json
{
  "timeout": 30,  // ✅ 적절한 연결 시간
  "sse_read_timeout": 3600  // ✅ 1시간 - 대부분의 작업 커버 (기본값)
}
```

## 🐛 타임아웃 오류 해결

### "Connection timeout" 오류

```
Error: Connection timeout after 30 seconds
```

**원인**: 서버 연결 실패
**해결**:
1. 서버 URL 확인
2. 네트워크 연결 확인
3. `timeout` 값 증가 (30 → 60)
4. 방화벽/프록시 설정 확인

### "Read timeout" 오류

```
Error: Read timeout after 3600 seconds
```

**원인**: 작업 실행 시간 초과 (1시간 이상)
**해결**:
1. `sse_read_timeout` 값 증가 (3600 → 7200 또는 10800)
2. UiPath 프로세스 최적화
3. 작업을 더 작은 단위로 분할

### 타임아웃 로그 확인

```bash
# Chainlit 로그에서 타임아웃 확인
tail -f .chainlit/logs/chainlit.log | grep -i timeout
```

## 📊 성능 모니터링

### 작업 실행 시간 측정

실제 작업이 얼마나 걸리는지 측정하여 적절한 timeout 설정:

```python
import time

start = time.time()
# 작업 실행
end = time.time()

print(f"실행 시간: {end - start:.2f}초")
```

### 권장 공식

```
sse_read_timeout = (평균 실행 시간 × 2) + 60초
```

**예시**:
- 평균 실행 시간: 3분 (180초)
- 권장 timeout: (180 × 2) + 60 = 420초 (7분)

## 🔗 관련 설정

### Backend MCP Server의 TOOL_CALL_TIMEOUT

Backend 서버에도 별도의 timeout 설정이 있습니다:

```bash
# backend/.env
TOOL_CALL_TIMEOUT=600  # 10분
```

**주의**: 
- `sse_read_timeout`은 클라이언트 측 설정
- `TOOL_CALL_TIMEOUT`은 서버 측 설정
- 두 값이 조화를 이루어야 함

**권장**:
```
sse_read_timeout >= TOOL_CALL_TIMEOUT + 30초
```

## 📚 추가 리소스

- [httpx Timeout 문서](https://www.python-httpx.org/advanced/#timeout-configuration)
- [SSE (Server-Sent Events) 스펙](https://html.spec.whatwg.org/multipage/server-sent-events.html)
- [MCP Protocol 문서](https://modelcontextprotocol.io/)
