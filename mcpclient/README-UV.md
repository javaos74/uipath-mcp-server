# MCP Client - UV 가상환경 사용 가이드

## 🚀 빠른 시작

### 1. UV 설치 (아직 설치하지 않은 경우)

```bash
# macOS/Linux (Homebrew)
brew install uv

# macOS/Linux (curl)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. 가상환경 생성

```bash
cd mcpclient

# UV로 가상환경 생성
uv venv

# 가상환경 활성화
source .venv/bin/activate  # macOS/Linux
# 또는
.venv\Scripts\activate     # Windows
```

### 3. 의존성 설치

```bash
# UV로 빠르게 설치 (권장)
uv pip install -r requirements.txt

# 또는 일반 pip 사용
pip install -r requirements.txt
```

### 4. 환경 변수 설정

```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 편집
nano .env
```

`.env` 파일에 다음 내용 추가:
```bash
OPENAI_API_KEY=sk-your-openai-api-key-here
MCP_SERVER_URL=http://localhost:8000/mcp/UiPath/Test/sse
MCP_SERVER_TOKEN=your-mcp-server-token
```

### 5. 실행

```bash
# Chainlit 실행
chainlit run app.py --port 8000

# 또는 watch 모드로 실행 (개발 시)
chainlit run app.py --port 8000 -w
```

브라우저에서 `http://localhost:8000` 접속

## 📦 UV의 장점

### 속도 비교

| 작업 | pip | uv | 속도 향상 |
|------|-----|----|---------:|
| 의존성 설치 | ~30초 | ~1초 | **30배** |
| 가상환경 생성 | ~5초 | ~0.5초 | **10배** |
| 패키지 해결 | ~10초 | ~1초 | **10배** |

### 주요 기능

- ✅ **매우 빠른 속도**: Rust로 작성되어 pip보다 10-100배 빠름
- ✅ **호환성**: pip와 완전히 호환되는 인터페이스
- ✅ **의존성 해결**: 더 정확하고 빠른 의존성 해결
- ✅ **캐싱**: 효율적인 패키지 캐싱으로 재설치 시간 단축

## 🔧 UV 명령어

### 가상환경 관리

```bash
# 가상환경 생성
uv venv

# 특정 Python 버전으로 생성
uv venv --python 3.11

# 가상환경 삭제
rm -rf .venv
```

### 패키지 관리

```bash
# 패키지 설치
uv pip install chainlit

# requirements.txt에서 설치
uv pip install -r requirements.txt

# 패키지 업그레이드
uv pip install --upgrade chainlit

# 패키지 제거
uv pip uninstall chainlit

# 설치된 패키지 목록
uv pip list

# requirements.txt 생성
uv pip freeze > requirements.txt
```

### 프로젝트 관리

```bash
# 프로젝트 초기화 (pyproject.toml 생성)
uv init

# 의존성 동기화
uv sync

# 스크립트 실행
uv run chainlit run app.py
```

## 🎯 개발 워크플로우

### 1. 새 프로젝트 시작

```bash
cd mcpclient

# 가상환경 생성 및 활성화
uv venv
source .venv/bin/activate

# 의존성 설치
uv pip install -r requirements.txt

# 개발 시작
chainlit run app.py -w
```

### 2. 의존성 추가

```bash
# 새 패키지 설치
uv pip install new-package

# requirements.txt 업데이트
uv pip freeze > requirements.txt
```

### 3. 의존성 업데이트

```bash
# 모든 패키지 업그레이드
uv pip install --upgrade -r requirements.txt

# requirements.txt 업데이트
uv pip freeze > requirements.txt
```

## 🐛 문제 해결

### 가상환경이 활성화되지 않는 경우

```bash
# 가상환경 재생성
rm -rf .venv
uv venv
source .venv/bin/activate
```

### 패키지 설치 오류

```bash
# 캐시 삭제 후 재설치
uv cache clean
uv pip install -r requirements.txt
```

### Python 버전 문제

```bash
# 특정 Python 버전 사용
uv venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt
```

## 📚 추가 리소스

- [UV 공식 문서](https://docs.astral.sh/uv/)
- [UV GitHub](https://github.com/astral-sh/uv)
- [Chainlit 문서](https://docs.chainlit.io/)

## 💡 팁

### 1. 가상환경 자동 활성화

`.bashrc` 또는 `.zshrc`에 추가:
```bash
# mcpclient 디렉토리 진입 시 자동 활성화
cd() {
  builtin cd "$@"
  if [[ -f .venv/bin/activate ]]; then
    source .venv/bin/activate
  fi
}
```

### 2. UV 별칭 설정

```bash
# .bashrc 또는 .zshrc에 추가
alias uvinstall='uv pip install'
alias uvlist='uv pip list'
alias uvfreeze='uv pip freeze'
```

### 3. 프로젝트 템플릿

```bash
# 새 프로젝트 빠르게 시작
mkdir my-project && cd my-project
uv venv
source .venv/bin/activate
uv pip install chainlit openai httpx python-dotenv
```

## 🔄 pip에서 UV로 마이그레이션

기존 pip 프로젝트를 UV로 전환:

```bash
# 1. 기존 가상환경 백업 (선택사항)
mv venv venv.backup

# 2. UV로 새 가상환경 생성
uv venv

# 3. 활성화
source .venv/bin/activate

# 4. 의존성 설치
uv pip install -r requirements.txt

# 5. 테스트
chainlit run app.py

# 6. 문제없으면 백업 삭제
rm -rf venv.backup
```
