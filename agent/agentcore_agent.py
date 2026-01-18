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
        # event에서 입력 데이터 추출
        # Agent Core는 다양한 형식으로 데이터를 전달할 수 있으므로 유연하게 처리
        if 'inputText' in event:
            user_input = event['inputText']
        elif 'input' in event:
            user_input = event['input']
        elif 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
            user_input = body.get('input') or body.get('inputText') or body.get('user_input')
        else:
            user_input = event.get('user_input', '')
        
        # 추가 파라미터 추출
        request_type = event.get('request_type')
        temperature = event.get('temperature')
        
        # orchestrator 실행
        result = orchestrate_request(
            user_input=user_input,
            request_type=request_type,
            temperature=temperature
        )
        
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
        print(error_message)
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': error_message,
                'request_type': 'error',
                'result': ''
            }, ensure_ascii=False),
            'headers': {
                'Content-Type': 'application/json'
            }
        }


# 로컬 테스트용
if __name__ == "__main__":
    # 테스트 이벤트
    test_event = {
        'user_input': '2026-01-13일에 나 무슨 영화봤어?, current_date=2026-01-16, user_id=44681408-c0b1-70f3-2d06-2a725f290f8b'
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2, ensure_ascii=False))
