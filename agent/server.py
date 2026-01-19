"""
Agent Core Runtime HTTP Server
FastAPI 기반 서버로 /ping과 /invocations 엔드포인트 제공
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
import json
import sys
import os

# orchestrator import
sys.path.insert(0, os.path.dirname(__file__))

# 시작 시 설정 로드 및 검증
print("=" * 80)
print("🔧 Agent Core Runtime 초기화 중...")
print("=" * 80)

try:
    from utils.secrets import get_config
    config = get_config()
    print(f"✅ 설정 로드 완료")
    print(f"   - AWS Region: {config.get('AWS_REGION')}")
    print(f"   - Knowledge Base ID: {config.get('KNOWLEDGE_BASE_ID', 'N/A')}")
    print(f"   - Claude Model: {config.get('BEDROCK_CLAUDE_MODEL_ID', 'N/A')[:50]}...")
    print(f"   - Nova Canvas Model: {config.get('BEDROCK_NOVA_CANVAS_MODEL_ID', 'N/A')}")
except Exception as e:
    print(f"⚠️  설정 로드 실패: {str(e)}")
    print(f"⚠️  일부 기능이 제한될 수 있습니다.")

from orchestrator.orchestra_agent import orchestrate_request

app = FastAPI(title="Diary Orchestrator Agent")


@app.get("/ping")
async def ping():
    """헬스체크 엔드포인트"""
    return {"status": "healthy"}


@app.post("/invocations")
async def invocations(request: Request):
    """
    Agent 호출 엔드포인트
    Agent Core Runtime이 이 엔드포인트로 요청을 보냄
    """
    try:
        # 요청 본문 파싱
        body = await request.json()
        
        print(f"[DEBUG] ========== Invocations 시작 ==========")
        print(f"[DEBUG] Request body: {json.dumps(body, ensure_ascii=False)[:200]}...")
        
        # 파라미터 추출
        user_input = body.get('content') or body.get('inputText') or body.get('input') or body.get('user_input')
        user_id = body.get('user_id')
        current_date = body.get('record_date') or body.get('current_date')
        request_type = body.get('request_type')
        temperature = body.get('temperature')
        
        if not user_input:
            return JSONResponse(
                status_code=400,
                content={
                    "type": "error",
                    "content": "",
                    "message": "입력 데이터가 필요합니다."
                }
            )
        
        print(f"[DEBUG] Extracted parameters:")
        print(f"[DEBUG]   user_input: {user_input[:100]}..." if len(str(user_input)) > 100 else f"[DEBUG]   user_input: {user_input}")
        print(f"[DEBUG]   user_id: {user_id}")
        print(f"[DEBUG]   current_date: {current_date}")
        
        # orchestrator 실행 - 모든 요청을 orchestrator가 처리
        result = orchestrate_request(
            user_input=user_input,
            user_id=user_id,
            current_date=current_date,
            request_type=request_type,
            temperature=temperature
        )
        
        print(f"[DEBUG] Result type: {result.get('type', 'unknown')}")
        print(f"[DEBUG] ========== Invocations 완료 ==========")
        
        return JSONResponse(content=result)
        
    except Exception as e:
        print(f"[ERROR] ========== Invocations 실패 ==========")
        print(f"[ERROR] Exception type: {type(e).__name__}")
        print(f"[ERROR] Exception message: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return JSONResponse(
            status_code=500,
            content={
                "type": "error",
                "content": "",
                "message": f"요청 처리 중 오류가 발생했습니다: {str(e)}"
            }
        )


if __name__ == "__main__":
    # 0.0.0.0:8080에서 서버 시작
    print("=" * 80)
    print("🚀 Agent Core Runtime Server 시작")
    print("=" * 80)
    print("Host: 0.0.0.0")
    print("Port: 8080")
    print("Endpoints:")
    print("  - GET  /ping")
    print("  - POST /invocations")
    print("=" * 80)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        log_level="info"
    )

