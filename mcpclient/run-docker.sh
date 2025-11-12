#!/bin/bash
# MCP Client Docker 실행 스크립트

set -e

# 색상 출력
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🚀 MCP Client Docker 실행${NC}"
echo "================================"

# .env 파일 확인
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env 파일이 없습니다.${NC}"
    echo ""
    read -p ".env.example을 복사하여 생성하시겠습니까? (y/n): " create_env
    
    if [ "$create_env" = "y" ] || [ "$create_env" = "Y" ]; then
        cp .env.example .env
        echo -e "${GREEN}✅ .env 파일이 생성되었습니다.${NC}"
        echo ""
        echo -e "${YELLOW}⚠️  .env 파일을 편집하여 OPENAI_API_KEY를 설정해주세요.${NC}"
        echo ""
        read -p "지금 편집하시겠습니까? (y/n): " edit_env
        
        if [ "$edit_env" = "y" ] || [ "$edit_env" = "Y" ]; then
            ${EDITOR:-nano} .env
        else
            echo ""
            echo "다음 명령어로 나중에 편집할 수 있습니다:"
            echo "  nano .env"
            echo ""
            exit 0
        fi
    else
        echo -e "${RED}❌ .env 파일이 필요합니다.${NC}"
        exit 1
    fi
fi

# OPENAI_API_KEY 확인
source .env
if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "sk-your-openai-api-key-here" ]; then
    echo -e "${RED}❌ OPENAI_API_KEY가 설정되지 않았습니다.${NC}"
    echo ""
    echo ".env 파일을 편집하여 OPENAI_API_KEY를 설정해주세요:"
    echo "  nano .env"
    echo ""
    exit 1
fi

echo -e "${GREEN}✅ 환경 변수 확인 완료${NC}"
echo ""

# 실행 옵션 선택
echo "실행 옵션을 선택하세요:"
echo "  1) Docker Compose로 실행 (권장)"
echo "  2) Docker 직접 실행"
echo "  3) 로컬에서 실행 (Python)"
read -p "선택 (1-3): " choice

case $choice in
    1)
        echo -e "${YELLOW}🐳 Docker Compose로 실행 중...${NC}"
        docker-compose up -d
        echo ""
        echo -e "${GREEN}✅ 실행 완료!${NC}"
        echo ""
        echo "접속 URL: http://localhost:8000"
        echo ""
        echo "로그 확인:"
        echo "  docker-compose logs -f"
        echo ""
        echo "중지:"
        echo "  docker-compose down"
        ;;
    
    2)
        echo -e "${YELLOW}🐳 Docker로 실행 중...${NC}"
        
        # 기존 컨테이너 확인 및 제거
        if docker ps -a | grep -q uipath-mcp-client; then
            echo "기존 컨테이너 제거 중..."
            docker rm -f uipath-mcp-client
        fi
        
        # 컨테이너 실행
        docker run -d \
            --name uipath-mcp-client \
            -p 8000:8000 \
            -e OPENAI_API_KEY="${OPENAI_API_KEY}" \
            -e MCP_SERVER_URL="${MCP_SERVER_URL:-}" \
            -e MCP_SERVER_TOKEN="${MCP_SERVER_TOKEN:-}" \
            -e CHAINLIT_AUTH_SECRET="${CHAINLIT_AUTH_SECRET:-change-this-secret}" \
            -v mcpclient-data:/app/.chainlit \
            --restart unless-stopped \
            uipath-mcp-client:latest
        
        echo ""
        echo -e "${GREEN}✅ 실행 완료!${NC}"
        echo ""
        echo "접속 URL: http://localhost:8000"
        echo ""
        echo "로그 확인:"
        echo "  docker logs -f uipath-mcp-client"
        echo ""
        echo "중지:"
        echo "  docker stop uipath-mcp-client"
        ;;
    
    3)
        echo -e "${YELLOW}🐍 Python으로 실행 중...${NC}"
        
        # 가상환경 확인
        if [ ! -d "venv" ]; then
            echo "가상환경 생성 중..."
            python3 -m venv venv
        fi
        
        # 가상환경 활성화
        source venv/bin/activate
        
        # 의존성 설치
        echo "의존성 설치 중..."
        pip install -q -r requirements.txt
        
        # Chainlit 실행
        echo ""
        echo -e "${GREEN}✅ 실행 중...${NC}"
        echo ""
        chainlit run app.py --port 8000
        ;;
    
    *)
        echo -e "${RED}❌ 잘못된 선택입니다.${NC}"
        exit 1
        ;;
esac
