"""
Agent Core Runtime Entrypoint
이 파일은 Bedrock Agent Core Runtime에서 호출되는 진입점입니다.
"""
import json
from typing import Any, Dict
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
        print(f"[DEBUG] Received event: {json.dumps(event, ensure_ascii=False)}")
        
        # event에서 입력 데이터 추출
        # Agent Core는 다양한 형식으로 데이터를 전달할 수 있으므로 유연하게 처리
        user_input = None
        
        # 1. 직접 필드에서 추출
        if 'content' in event:
            user_input = event['content']
        elif 'inputText' in event:
            user_input = event['inputText']
        elif 'input' in event:
            user_input = event['input']
        elif 'user_input' in event:
            user_input = event['user_input']
        # 2. body에서 추출
        elif 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
            user_input = body.get('content') or body.get('input') or body.get('inputText') or body.get('user_input')
        
        if not user_input:
            raise ValueError("입력 데이터를 찾을 수 없습니다. 'content', 'input', 'inputText', 또는 'user_input' 필드가 필요합니다.")
        
        # 추가 파라미터 추출 (여러 필드명 지원)
        user_id = event.get('user_id')
        if not user_id and 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
            user_id = body.get('user_id')
        
        # record_date 또는 current_date
        current_date = event.get('record_date') or event.get('current_date')
        if not current_date and 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
            current_date = body.get('record_date') or body.get('current_date')
        
        request_type = event.get('request_type')
        temperature = event.get('temperature')
        
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
        
        # 성공 응답 반환
        return {
            'statusCode': 200,
            'body': json.dumps(result, ensure_ascii=False),
            'headers': {
                'Content-Type': 'application/json'
            }
        }
        
    except Exception as e:
        # 에러 처리
        error_message = f"Error processing request: {str(e)}"
        print(f"[ERROR] ========== Lambda Handler 실패 ==========")
        print(f"[ERROR] {error_message}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': error_message,
                'type': 'error',
                'content': '',
                'message': '요청 처리 중 오류가 발생했습니다.'
            }, ensure_ascii=False),
            'headers': {
                'Content-Type': 'application/json'
            }
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
