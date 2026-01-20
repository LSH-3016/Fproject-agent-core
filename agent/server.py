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
print("=" * 80, flush=True)
print("🔧 Agent Core Runtime 초기화 중...", flush=True)
print("=" * 80, flush=True)

config = None
try:
    from utils.secrets import get_config
    config = get_config()
    print(f"✅ 설정 로드 완료", flush=True)
    print(f"   - AWS Region: {config.get('AWS_REGION')}", flush=True)
    print(f"   - Knowledge Base ID: {config.get('KNOWLEDGE_BASE_ID', 'N/A')}", flush=True)
    print(f"   - Claude Model: {config.get('BEDROCK_CLAUDE_MODEL_ID', 'N/A')[:50]}...", flush=True)
    print(f"   - Nova Canvas Model: {config.get('BEDROCK_NOVA_CANVAS_MODEL_ID', 'N/A')}", flush=True)
    print(f"   - S3 Bucket: {config.get('KNOWLEDGE_BASE_BUCKET', 'N/A')}", flush=True)
except Exception as e:
    import sys
    print(f"⚠️  설정 로드 실패: {str(e)}", file=sys.stderr, flush=True)
    print(f"⚠️  일부 기능이 제한될 수 있습니다.", file=sys.stderr, flush=True)
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.stderr.flush()

# orchestrator import - 이것도 실패할 수 있으므로 try-catch
orchestrate_request = None
try:
    print("🔄 Orchestrator 로드 중...", flush=True)
    from orchestrator.orchestra_agent import orchestrate_request
    print("✅ Orchestrator 로드 완료", flush=True)
except Exception as e:
    import sys
    print(f"❌ CRITICAL: Orchestrator 로드 실패: {str(e)}", file=sys.stderr, flush=True)
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.stderr.flush()
    # 서버는 시작하되, 요청 시 에러 반환

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
    import sys
    import traceback
    
    # orchestrator가 로드되지 않았으면 에러 반환
    if orchestrate_request is None:
        error_msg = "Orchestrator 초기화 실패. CloudWatch Logs를 확인하세요."
        print(f"❌ ERROR: {error_msg}", file=sys.stderr, flush=True)
        return JSONResponse(
            status_code=500,
            content={
                "type": "error",
                "content": "",
                "message": error_msg
            }
        )
    
    try:
        # 요청 본문 파싱
        body = await request.json()
        
        print(f"[DEBUG] ========== Invocations 시작 ==========", flush=True)
        print(f"[DEBUG] Request body: {json.dumps(body, ensure_ascii=False)[:200]}...", flush=True)
        
        # 파라미터 추출
        user_input = body.get('content') or body.get('inputText') or body.get('input') or body.get('user_input')
        user_id = body.get('user_id')
        current_date = body.get('record_date') or body.get('current_date')
        request_type = body.get('request_type')
        temperature = body.get('temperature')
        
        # 이미지 생성 관련 파라미터
        text = body.get('text')  # 이미지 생성용 일기 텍스트
        image_base64 = body.get('image_base64')  # S3 업로드용 이미지
        record_date = body.get('record_date')  # S3 업로드용 날짜
        
        if not user_input:
            error_msg = "입력 데이터가 필요합니다."
            print(f"❌ ERROR: {error_msg}", file=sys.stderr, flush=True)
            return JSONResponse(
                status_code=400,
                content={
                    "type": "error",
                    "content": "",
                    "message": error_msg
                }
            )
        
        print(f"[DEBUG] Extracted parameters:", flush=True)
        print(f"[DEBUG]   user_input: {user_input[:100]}..." if len(str(user_input)) > 100 else f"[DEBUG]   user_input: {user_input}", flush=True)
        print(f"[DEBUG]   user_id: {user_id}", flush=True)
        print(f"[DEBUG]   current_date: {current_date}", flush=True)
        print(f"[DEBUG]   request_type: {request_type}", flush=True)
        print(f"[DEBUG]   text: {text[:50] if text else None}...", flush=True)
        print(f"[DEBUG]   image_base64: {'<provided>' if image_base64 else None}", flush=True)
        print(f"[DEBUG]   record_date: {record_date}", flush=True)
        
        # orchestrator 실행 - 모든 요청을 orchestrator가 처리
        print(f"[DEBUG] Calling orchestrate_request...", flush=True)
        result = orchestrate_request(
            user_input=user_input,
            user_id=user_id,
            current_date=current_date,
            request_type=request_type,
            temperature=temperature,
            text=text,
            image_base64=image_base64,
            record_date=record_date
        )
        print(f"[DEBUG] orchestrate_request completed", flush=True)
        
        print(f"[DEBUG] Result type: {result.get('type', 'unknown')}", flush=True)
        print(f"[DEBUG] ========== Invocations 완료 ==========", flush=True)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        print(f"[ERROR] ========== Invocations 실패 ==========", file=sys.stderr, flush=True)
        print(f"[ERROR] Exception type: {type(e).__name__}", file=sys.stderr, flush=True)
        print(f"[ERROR] Exception message: {str(e)}", file=sys.stderr, flush=True)
        print(f"[ERROR] Traceback:", file=sys.stderr, flush=True)
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
        
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
    print(f"Orchestrator 상태: {'✅ 로드됨' if orchestrate_request else '❌ 로드 실패'}")
    print("=" * 80)
    
    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8080,
            log_level="info"
        )
    except Exception as e:
        print(f"❌ 서버 시작 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

