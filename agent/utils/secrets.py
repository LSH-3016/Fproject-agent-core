"""
AWS Secrets Manager에서 민감 정보를 가져오는 유틸리티
"""
import json
import os
import boto3
from botocore.exceptions import ClientError


def get_secret(secret_name: str, region_name: str = None) -> dict:
    """
    AWS Secrets Manager에서 시크릿을 가져옵니다.
    
    Args:
        secret_name: Secrets Manager의 시크릿 이름
        region_name: AWS 리전 (기본값: 환경변수 또는 us-east-1)
    
    Returns:
        시크릿 값을 담은 딕셔너리
    """
    if region_name is None:
        region_name = os.environ.get('AWS_REGION', 'us-east-1')
    
    # Secrets Manager 클라이언트 생성
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )
    
    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        # 에러 처리
        error_code = e.response['Error']['Code']
        if error_code == 'ResourceNotFoundException':
            print(f"❌ Secret을 찾을 수 없습니다: {secret_name}")
        elif error_code == 'InvalidRequestException':
            print(f"❌ 잘못된 요청입니다: {error_code}")
        elif error_code == 'InvalidParameterException':
            print(f"❌ 잘못된 파라미터입니다: {error_code}")
        elif error_code == 'DecryptionFailure':
            print(f"❌ 복호화 실패: {error_code}")
        elif error_code == 'InternalServiceError':
            print(f"❌ 내부 서비스 오류: {error_code}")
        else:
            print(f"❌ 알 수 없는 오류: {error_code}")
        raise e
    
    # 시크릿 값 파싱
    if 'SecretString' in get_secret_value_response:
        secret = get_secret_value_response['SecretString']
        return json.loads(secret)
    else:
        # 바이너리 시크릿의 경우
        import base64
        decoded_binary_secret = base64.b64decode(get_secret_value_response['SecretBinary'])
        return json.loads(decoded_binary_secret)


def get_config() -> dict:
    """
    애플리케이션 설정을 가져옵니다.
    Secrets Manager에서 가져옵니다.
    
    Returns:
        설정 딕셔너리
    """
    # Secrets Manager에서 가져오기
    secret_name = 'agent-core-secret'
    
    try:
        config = get_secret(secret_name)
        print(f"✅ Secrets Manager에서 설정을 가져왔습니다: {secret_name}")
        return config
    except Exception as e:
        print(f"⚠️  Secrets Manager에서 설정을 가져올 수 없습니다: {str(e)}")
        print("⚠️  환경변수를 사용합니다.")
        
        # 환경변수에서 가져오기 (Fallback)
        return {
            'KNOWLEDGE_BASE_ID': os.environ.get('KNOWLEDGE_BASE_ID', ''),
            'AWS_REGION': os.environ.get('AWS_REGION', 'us-east-1'),
            'BEDROCK_MODEL_ARN': os.environ.get('BEDROCK_MODEL_ARN', ''),
            'IAM_ROLE_ARN': os.environ.get('IAM_ROLE_ARN', ''),
        }
