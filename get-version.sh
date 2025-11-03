#!/bin/bash
# pyproject.toml에서 버전 추출 유틸리티

if [ ! -f "backend/pyproject.toml" ]; then
    echo "latest"
    exit 0
fi

# Python 3.11+ (tomllib 내장)
if command -v python3 &> /dev/null; then
    VERSION=$(python3 << 'EOF' 2>/dev/null
try:
    import tomllib
    with open('backend/pyproject.toml', 'rb') as f:
        data = tomllib.load(f)
        print(data['project']['version'])
except:
    try:
        import toml
        data = toml.load('backend/pyproject.toml')
        print(data['project']['version'])
    except:
        pass
EOF
)
fi

# Python으로 추출 실패 시 grep 사용
if [ -z "$VERSION" ]; then
    VERSION=$(grep -E '^version = ' backend/pyproject.toml | sed 's/version = "\(.*\)"/\1/')
fi

# 여전히 비어있으면 latest
if [ -z "$VERSION" ]; then
    VERSION="latest"
fi

echo "$VERSION"
