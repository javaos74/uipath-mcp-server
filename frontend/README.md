# UiPath MCP Server Manager - Frontend

React + TypeScript + Vite 기반 프론트엔드

## 기술 스택

- **React 18** - UI 라이브러리
- **TypeScript** - 타입 안전성
- **Vite** - 빌드 도구
- **React Router** - 라우팅
- **TanStack Query** - 서버 상태 관리
- **Zustand** - 클라이언트 상태 관리
- **Axios** - HTTP 클라이언트

## 설치

```bash
cd frontend
npm install
```

## 개발 서버 실행

```bash
npm run dev
```

개발 서버가 http://localhost:3000 에서 실행됩니다.

백엔드 서버가 http://localhost:8000 에서 실행 중이어야 합니다.

## 빌드

```bash
npm run build
```

빌드된 파일은 `dist/` 폴더에 생성됩니다.

## 프로젝트 구조

```
frontend/
├── src/
│   ├── components/      # 재사용 가능한 컴포넌트
│   │   └── Layout.tsx
│   ├── pages/          # 페이지 컴포넌트
│   │   ├── Login.tsx
│   │   ├── Register.tsx
│   │   ├── Dashboard.tsx
│   │   ├── ServerDetail.tsx
│   │   └── Settings.tsx
│   ├── lib/            # 유틸리티 및 API
│   │   └── api.ts
│   ├── store/          # 상태 관리
│   │   └── authStore.ts
│   ├── types/          # TypeScript 타입 정의
│   │   └── index.ts
│   ├── App.tsx         # 메인 앱 컴포넌트
│   ├── main.tsx        # 진입점
│   └── index.css       # 글로벌 스타일
├── index.html
├── package.json
├── tsconfig.json
└── vite.config.ts
```

## 주요 기능

### 1. 인증
- 로그인/회원가입
- JWT 토큰 기반 인증
- 자동 로그아웃 (토큰 만료 시)

### 2. 대시보드
- MCP 서버 목록 조회
- 서버 생성/삭제
- 서버별 엔드포인트 표시

### 3. 서버 상세
- Tool 목록 조회
- Tool 생성/수정/삭제 (예정)

### 4. 설정
- 사용자 정보 표시
- UiPath 설정 (URL, PAT, Folder Path)

## API 통합

모든 API 호출은 `src/lib/api.ts`에서 관리됩니다:

```typescript
import { authAPI, serversAPI, toolsAPI } from '@/lib/api'

// 로그인
const response = await authAPI.login({ username, password })

// 서버 목록
const servers = await serversAPI.list()

// Tool 생성
const tool = await toolsAPI.create(tenantName, serverName, toolData)
```

## 상태 관리

### 인증 상태 (Zustand)
```typescript
import { useAuthStore } from '@/store/authStore'

const { user, token, isAuthenticated, setAuth, clearAuth } = useAuthStore()
```

### 서버 데이터 (TanStack Query)
```typescript
import { useQuery } from '@tanstack/react-query'

const { data, isLoading } = useQuery({
  queryKey: ['servers'],
  queryFn: serversAPI.list,
})
```

## 환경 변수

`.env` 파일 생성:

```bash
cp .env.example .env
```

```
VITE_API_URL=http://localhost:8000
```

## 개발 가이드

### 새 페이지 추가

1. `src/pages/` 에 컴포넌트 생성
2. `src/App.tsx` 에 라우트 추가
3. 필요시 `src/components/Layout.tsx` 에 네비게이션 링크 추가

### 새 API 엔드포인트 추가

1. `src/types/index.ts` 에 타입 정의
2. `src/lib/api.ts` 에 API 함수 추가
3. 컴포넌트에서 TanStack Query로 사용

## 프록시 설정

개발 서버는 백엔드 API를 프록시합니다 (`vite.config.ts`):

```typescript
proxy: {
  '/api': 'http://localhost:8000',
  '/auth': 'http://localhost:8000',
  '/mcp': 'http://localhost:8000',
}
```

## 배포

### 프로덕션 빌드

```bash
npm run build
```

### 정적 파일 서빙

```bash
npm run preview
```

또는 Nginx, Apache 등으로 `dist/` 폴더를 서빙합니다.

## 라이선스

MIT
