# 토큰 인증 가이드

## 개요

이 시스템은 JWT (JSON Web Token) 기반 인증을 사용합니다. 사용자는 로그인 후 받은 토큰을 사용하여 API에 접근합니다.

## 인증 플로우

### 1. 사용자 등록

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john",
    "email": "john@example.com",
    "password": "password123",
    "role": "user"
  }'
```

**응답:**
```json
{
  "id": 1,
  "username": "john",
  "email": "john@example.com",
  "role": "user",
  "is_active": true,
  "uipath_url": null,
  "uipath_folder_path": null,
  "created_at": "2025-10-18 09:00:00",
  "updated_at": "2025-10-18 09:00:00"
}
```

### 2. 로그인 및 토큰 발급

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john",
    "password": "password123"
  }'
```

**응답:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "john",
    "email": "john@example.com",
    "role": "user",
    "is_active": true,
    "uipath_url": null,
    "uipath_folder_path": null,
    "created_at": "2025-10-18 09:00:00",
    "updated_at": "2025-10-18 09:00:00"
  }
}
```

### 3. 토큰 사용

받은 `access_token`을 모든 API 요청의 `Authorization` 헤더에 포함시킵니다:

```bash
curl -X GET http://localhost:8000/api/servers \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

## 토큰 저장 방법

### 웹 브라우저

```javascript
// 로그인 후 토큰 저장
const response = await fetch('http://localhost:8000/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: 'john', password: 'password123' })
});

const data = await response.json();
localStorage.setItem('access_token', data.access_token);
localStorage.setItem('user', JSON.stringify(data.user));

// API 호출 시 토큰 사용
const serversResponse = await fetch('http://localhost:8000/api/servers', {
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
  }
});
```

### Python 스크립트

```python
import requests
import os

# 로그인
response = requests.post('http://localhost:8000/auth/login', json={
    'username': 'john',
    'password': 'password123'
})

data = response.json()
token = data['access_token']

# 환경변수에 저장 (선택)
os.environ['MCP_TOKEN'] = token

# API 호출
headers = {'Authorization': f'Bearer {token}'}
servers = requests.get('http://localhost:8000/api/servers', headers=headers)
print(servers.json())
```

### CLI 도구

```bash
# 토큰을 파일에 저장
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"john","password":"password123"}' \
  | jq -r '.access_token' > ~/.mcp_token

# 저장된 토큰 사용
TOKEN=$(cat ~/.mcp_token)
curl -X GET http://localhost:8000/api/servers \
  -H "Authorization: Bearer $TOKEN"
```

## UiPath 설정

### UiPath PAT 저장

사용자는 자신의 UiPath Personal Access Token을 저장할 수 있습니다:

```bash
curl -X PUT http://localhost:8000/auth/uipath-config \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "uipath_url": "https://cloud.uipath.com/myaccount/mytenant",
    "uipath_access_token": "YOUR_UIPATH_PAT",
    "uipath_folder_path": "/Production/Finance"
  }'
```

**응답:**
```json
{
  "id": 1,
  "username": "john",
  "email": "john@example.com",
  "role": "user",
  "is_active": true,
  "uipath_url": "https://cloud.uipath.com/myaccount/mytenant",
  "uipath_folder_path": "/Production/Finance",
  "created_at": "2025-10-18 09:00:00",
  "updated_at": "2025-10-18 09:05:00"
}
```

**참고:** `uipath_access_token`은 보안상 응답에 포함되지 않습니다.

### UiPath PAT 사용

사용자가 UiPath 설정을 저장하면, 해당 사용자가 생성한 MCP 서버의 Tool이 실행될 때 자동으로 사용자의 UiPath 자격 증명이 사용됩니다.

## 토큰 만료

- JWT 토큰은 **24시간** 동안 유효합니다
- 토큰이 만료되면 다시 로그인해야 합니다
- 401 Unauthorized 응답을 받으면 토큰이 만료되었거나 유효하지 않은 것입니다

## 보안 권장사항

1. **HTTPS 사용**: 프로덕션 환경에서는 반드시 HTTPS를 사용하세요
2. **SECRET_KEY 변경**: `.env` 파일의 `SECRET_KEY`를 강력한 랜덤 값으로 변경하세요
   ```bash
   openssl rand -hex 32
   ```
3. **토큰 안전하게 저장**: 
   - 브라우저: localStorage 대신 httpOnly 쿠키 사용 권장
   - 서버: 환경변수 또는 보안 저장소 사용
4. **토큰 노출 방지**: 
   - 로그에 토큰 출력하지 않기
   - Git에 토큰 커밋하지 않기
   - 공개 채널에 토큰 공유하지 않기

## 로그인 화면 예시

### HTML + JavaScript

```html
<!DOCTYPE html>
<html>
<head>
    <title>MCP Server Login</title>
</head>
<body>
    <h1>Login</h1>
    <form id="loginForm">
        <input type="text" id="username" placeholder="Username" required>
        <input type="password" id="password" placeholder="Password" required>
        <button type="submit">Login</button>
    </form>
    <div id="message"></div>

    <script>
        document.getElementById('loginForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            
            try {
                const response = await fetch('http://localhost:8000/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    localStorage.setItem('access_token', data.access_token);
                    localStorage.setItem('user', JSON.stringify(data.user));
                    
                    document.getElementById('message').textContent = 'Login successful!';
                    // Redirect to dashboard
                    window.location.href = '/dashboard.html';
                } else {
                    const error = await response.json();
                    document.getElementById('message').textContent = error.error;
                }
            } catch (error) {
                document.getElementById('message').textContent = 'Login failed: ' + error.message;
            }
        });
    </script>
</body>
</html>
```

## API 엔드포인트

### 인증 관련

- `POST /auth/register` - 사용자 등록
- `POST /auth/login` - 로그인 (토큰 발급)
- `GET /auth/me` - 현재 사용자 정보 조회 (인증 필요)
- `PUT /auth/uipath-config` - UiPath 설정 업데이트 (인증 필요)

### 보호된 엔드포인트

모든 `/api/*` 및 `/mcp/*` 엔드포인트는 인증이 필요합니다.
