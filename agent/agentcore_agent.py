"""
Agent Core Runtime Entrypoint
이 파일은 Bedrock Agent Core Runtime에서 호출되는 진입점입니다.
"""
import json
import sys
import os
from typing import Any, Dict

# orchestrator import
sys.path.insert(0, os.path.dirname(__file__))
from orchestrator.orchestra_agent import orchestrate_request


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Agent Core Runtime에서 호출되는 Lambda 핸들러
    
    Args:
        event: Lambda 이벤트 객체
        context: Lambda 컨텍스트 객체
        
    Returns:
        처리 결과를 포함한 응답 딕셔너리
    """
    try:
        print(f"[DEBUG] ========== Lambda Handler 시작 ==========")
        print(f"[DEBUG] Event type: {type(event)}")
        print(f"[DEBUG] Event keys: {event.keys() if isinstance(event, dict) else 'N/A'}")
        print(f"[DEBUG] Raw event: {json.dumps(event, ensure_ascii=False, default=str)}")
        
        # Agent Core Runtime은 다양한 형식으로 이벤트를 전달할 수 있음
        # 1. 직접 페이로드
        # 2. body 안에 JSON 문자열
        # 3. inputText 필드
        
        user_input = None
        user_id = None
        current_date = None
        request_type = None
        temperature = None
        
        # 페이로드 파싱 시도
        if isinstance(event, str):
            # 문자열로 온 경우 JSON 파싱
            try:
                event = json.loads(event)
            except:
                # JSON이 아니면 그대로 user_input으로 사용
                user_input = event
        
        if isinstance(event, dict):
            # 1. 직접 필드 확인
            user_input = event.get('content') or event.get('inputText') or event.get('input') or event.get('user_input')
            user_id = event.get('user_id')
            current_date = event.get('record_date') or event.get('current_date')
            request_type = event.get('request_type')
            temperature = event.get('temperature')
            
            # 2. body 필드 확인
            if not user_input and 'body' in event:
                body = event['body']
                if isinstance(body, str):
                    try:
                        body = json.loads(body)
                    except:
                        user_input = body
                
                if isinstance(body, dict):
                    user_input = body.get('content') or body.get('inputText') or body.get('input') or body.get('user_input')
                    user_id = user_id or body.get('user_id')
                    current_date = current_date or body.get('record_date') or body.get('current_date')
                    request_type = request_type or body.get('request_type')
                    temperature = temperature or body.get('temperature')
            
            # 3. payload 필드 확인 (Agent Core Runtime이 사용할 수 있음)
            if not user_input and 'payload' in event:
                payload = event['payload']
                if isinstance(payload, str):
                    try:
                        payload = json.loads(payload)
                    except:
                        user_input = payload
                
                if isinstance(payload, dict):
                    user_input = payload.get('content') or payload.get('inputText') or payload.get('input') or payload.get('user_input')
                    user_id = user_id or payload.get('user_id')
                    current_date = current_date or payload.get('record_date') or payload.get('current_date')
                    request_type = request_type or payload.get('request_type')
                    temperature = temperature or payload.get('temperature')
        
        if not user_input:
            raise ValueError("입력 데이터를 찾을 수 없습니다. 'content', 'input', 'inputText', 또는 'user_input' 필드가 필요합니다.")
        
        print(f"[DEBUG] Extracted parameters:")
        print(f"[DEBUG]   user_input: {user_input}")
        print(f"[DEBUG]   user_id: {user_id}")
        print(f"[DEBUG]   current_date: {current_date}")
        print(f"[DEBUG]   request_type: {request_type}")
        print(f"[DEBUG]   temperature: {temperature}")
        
        # orchestrator 실행
        print(f"[DEBUG] Calling orchestrator...")
        result = orchestrate_request(
            user_input=user_input,
            user_id=user_id,
            current_date=current_date,
            request_type=request_type,
            temperature=temperature
        )
        
        print(f"[DEBUG] Orchestrator result: {json.dumps(result, ensure_ascii=False)}")
        print(f"[DEBUG] ========== Lambda Handler 완료 ==========")
        
        # Agent Core Runtime은 다양한 응답 형식을 지원
        # 1. 직접 반환
        # 2. statusCode + body 형식
        
        # 두 형식 모두 지원하도록 반환
        response = {
            'statusCode': 200,
            'body': json.dumps(result, ensure_ascii=False),
            'headers': {
                'Content-Type': 'application/json'
            }
        }
        
        # 직접 결과도 포함 (Agent Core Runtime이 어떤 형식을 기대하는지 모르므로)
        response.update(result)
        
        return response
        
    except Exception as e:
        # 에러 처리
        error_message = f"Error processing request: {str(e)}"
        print(f"[ERROR] ========== Lambda Handler 실패 ==========")
        print(f"[ERROR] {error_message}")
        import traceback
        traceback.print_exc()
        
        error_response = {
            'type': 'error',
            'content': '',
            'message': f'요청 처리 중 오류가 발생했습니다: {str(e)}'
        }
        
        return {
            'statusCode': 500,
            'body': json.dumps(error_response, ensure_ascii=False),
            'headers': {
                'Content-Type': 'application/json'
            },
            **error_response  # 직접 필드도 포함
        }


# 로컬 테스트용
if __name__ == "__main__":
    # 테스트 이벤트 - 백엔드 API 형식
    test_event = {
        'user_id': 'user123',
        'content': '오늘 점심에 맛있는 파스타를 먹었다',
        'record_date': '2026-01-18'
    }
    
    print("=" * 80)
    print("로컬 테스트 시작")
    print("=" * 80)
    result = lambda_handler(test_event, None)
    print("\n" + "=" * 80)
    print("결과:")
    print("=" * 80)
    print(json.dumps(result, indent=2, ensure_ascii=False))
