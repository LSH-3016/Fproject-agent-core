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
        print(f"[DEBUG] Request body: {json.dumps(body, ensure_ascii=False)}")
        
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
        print(f"[DEBUG]   user_input: {user_input}")
        print(f"[DEBUG]   user_id: {user_id}")
        print(f"[DEBUG]   current_date: {current_date}")
        
        # orchestrator 실행
        result = orchestrate_request(
            user_input=user_input,
            user_id=user_id,
            current_date=current_date,
            request_type=request_type,
            temperature=temperature
        )
        
        print(f"[DEBUG] Result: {json.dumps(result, ensure_ascii=False)}")
        print(f"[DEBUG] ========== Invocations 완료 ==========")
        
        return JSONResponse(content=result)
        
    except Exception as e:
        print(f"[ERROR] ========== Invocations 실패 ==========")
        print(f"[ERROR] {str(e)}")
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
