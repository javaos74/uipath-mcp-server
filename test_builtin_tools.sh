#!/bin/bash

echo "============================================================"
echo "Built-in Tools 검증 테스트"
echo "============================================================"
echo ""

cd backend || exit 1

PYTHONPATH=src python3 << 'EOF'
import sys
import asyncio
from builtin_registry import discover_builtin_tools

async def verify():
    print("📋 1단계: 도구 발견 중...")
    tools = await discover_builtin_tools()
    
    if not tools:
        print("❌ 오류: 도구를 발견하지 못했습니다!")
        return False
    
    print(f"✅ {len(tools)}개의 도구를 발견했습니다.\n")
    
    # 모듈별로 그룹화
    print("📋 2단계: 발견된 도구 목록")
    print("-" * 60)
    
    modules = {}
    for tool in tools:
        name = tool.get("name", "이름없음")
        
        # Extract python_function
        python_function = tool.get("python_function")
        if not python_function and "function" in tool:
            func = tool["function"]
            if callable(func):
                module_name = func.__module__
                func_name = func.__name__
                if module_name.startswith("src.builtin."):
                    module_name = module_name.replace("src.builtin.", "")
                python_function = f"{module_name}.{func_name}"
        
        if python_function:
            module = python_function.split(".")[0]
            if module not in modules:
                modules[module] = []
            modules[module].append((name, python_function))
    
    for module, tool_list in sorted(modules.items()):
        print(f"\n📦 {module}.py ({len(tool_list)}개)")
        for name, python_function in tool_list:
            print(f"  ✓ {name}")
            print(f"    → {python_function}")
    
    print("\n" + "-" * 60)
    
    # 검증
    print("\n📋 3단계: 검증")
    print("-" * 60)
    
    errors = []
    for tool in tools:
        name = tool.get("name")
        if not name:
            errors.append("도구 이름이 없는 항목 발견")
            continue
        
        if "description" not in tool:
            errors.append(f"{name}: description 필드 누락")
        
        if "input_schema" not in tool:
            errors.append(f"{name}: input_schema 필드 누락")
        
        if "function" not in tool and "python_function" not in tool:
            errors.append(f"{name}: function 또는 python_function 필드 누락")
    
    if errors:
        print("❌ 검증 실패:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    print("✅ 모든 도구가 필수 필드를 포함하고 있습니다.\n")
    
    # 요약
    print("=" * 60)
    print("검증 완료")
    print("=" * 60)
    print(f"✅ 총 {len(tools)}개의 도구가 정상적으로 등록 가능합니다.")
    print(f"✅ {len(modules)}개의 모듈에서 도구를 발견했습니다.")
    print("")
    
    return True

try:
    result = asyncio.run(verify())
    sys.exit(0 if result else 1)
except Exception as e:
    print(f"\n❌ 오류 발생: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF

exit_code=$?

cd ../..

if [ $exit_code -eq 0 ]; then
    echo "✅ 테스트 성공!"
else
    echo "❌ 테스트 실패!"
fi

exit $exit_code
