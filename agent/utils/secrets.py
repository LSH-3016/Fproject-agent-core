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
        print(f"[Secrets] Fetching secret: {secret_name} from region: {region_name}")
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
        print(f"[Secrets] Secret fetched successfully")
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
        secret_string = get_secret_value_response['SecretString']
        print(f"[Secrets] Secret string length: {len(secret_string)}")
        print(f"[Secrets] Secret string preview: {secret_string[:100]}...")
        
        # 작은따옴표로 감싸진 경우 제거 (AWS CLI 출력 형식)
        if secret_string.startswith("'") and secret_string.endswith("'"):
            print(f"[Secrets] Removing surrounding single quotes from secret string")
            secret_string = secret_string[1:-1]
        
        try:
            secret_dict = json.loads(secret_string)
            print(f"[Secrets] Successfully parsed JSON with {len(secret_dict)} keys")
            return secret_dict
        except json.JSONDecodeError as e:
            print(f"❌ JSON 파싱 실패: {str(e)}")
            print(f"❌ Secret string: {secret_string}")
            print(f"❌ First 50 chars: {repr(secret_string[:50])}")
            print(f"❌ Last 50 chars: {repr(secret_string[-50:])}")
            raise ValueError(f"Secret '{secret_name}'의 JSON 파싱 실패: {str(e)}")
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
    # Secret 이름 (환경변수 또는 기본값)
    # 여러 가능한 이름을 시도
    possible_secret_names = [
        os.environ.get('SECRET_NAME'),
        'agent-core-secret',       # us-east-1 Secret
        'one-agent-core-secret',  # ap-northeast-2 Secret (fallback)
    ]
    
    secret_name = None
    region_name = os.environ.get('AWS_REGION', 'us-east-1')
    
    # 여러 Secret 이름을 시도
    config = None
    for name in possible_secret_names:
        if not name:
            continue
        try:
            config = get_secret(name, region_name)
            secret_name = name
            print(f"✅ Secrets Manager에서 설정을 가져왔습니다: {secret_name}")
            break
        except Exception as e:
            print(f"⚠️  Secret '{name}' 시도 실패: {str(e)}")
            continue
    
    if not config:
        raise Exception(f"모든 Secret 이름 시도 실패: {possible_secret_names}")
    
    try:
        
        # 필수 키 검증
        required_keys = ['KNOWLEDGE_BASE_ID', 'AWS_REGION']
        missing_keys = [key for key in required_keys if not config.get(key)]
        
        if missing_keys:
            print(f"⚠️  경고: 다음 필수 키가 누락되었습니다: {', '.join(missing_keys)}")
        
        # AWS_REGION은 환경변수 우선
        if 'AWS_REGION' not in config or not config['AWS_REGION']:
            config['AWS_REGION'] = region_name
        
        # Model ID에서 'us.' 접두사 제거 (cross-region inference profile 형식 정규화)
        model_id_keys = ['BEDROCK_CLAUDE_MODEL_ID', 'BEDROCK_LLM_MODEL_ID', 'BEDROCK_MODEL_ARN']
        for key in model_id_keys:
            if key in config and config[key]:
                original_value = config[key]
                # ARN 형식이면 model ID만 추출
                if original_value.startswith('arn:aws:bedrock:'):
                    # arn:aws:bedrock:us-east-1:...:inference-profile/global.anthropic.claude-sonnet-4-5-20250929-v1:0
                    # → anthropic.claude-sonnet-4-5-20250929-v1:0
                    if '/global.' in original_value:
                        config[key] = original_value.split('/global.')[-1]
                        print(f"[Config] {key}: ARN에서 model ID 추출: {original_value} → {config[key]}")
                    elif '/' in original_value:
                        config[key] = original_value.split('/')[-1]
                        print(f"[Config] {key}: ARN에서 model ID 추출: {original_value} → {config[key]}")
                # us. 접두사 제거
                elif config[key].startswith('us.'):
                    config[key] = config[key].replace('us.', '', 1)
                    print(f"[Config] {key}: 'us.' 접두사 제거: {original_value} → {config[key]}")
        
        # 누락된 키들에 대한 fallback 설정
        if 'BEDROCK_CLAUDE_MODEL_ID' not in config or not config['BEDROCK_CLAUDE_MODEL_ID']:
            # BEDROCK_MODEL_ARN에서 추출 시도
            if 'BEDROCK_MODEL_ARN' in config and config['BEDROCK_MODEL_ARN']:
                config['BEDROCK_CLAUDE_MODEL_ID'] = config['BEDROCK_MODEL_ARN']
                print(f"[Config] BEDROCK_CLAUDE_MODEL_ID: BEDROCK_MODEL_ARN에서 복사")
            else:
                config['BEDROCK_CLAUDE_MODEL_ID'] = 'anthropic.claude-sonnet-4-5-20250929-v1:0'
                print(f"[Config] BEDROCK_CLAUDE_MODEL_ID: 기본값 사용")
        
        if 'BEDROCK_LLM_MODEL_ID' not in config or not config['BEDROCK_LLM_MODEL_ID']:
            config['BEDROCK_LLM_MODEL_ID'] = 'anthropic.claude-sonnet-4-20250514-v1:0'
            print(f"[Config] BEDROCK_LLM_MODEL_ID: 기본값 사용")
        
        if 'BEDROCK_NOVA_CANVAS_MODEL_ID' not in config or not config['BEDROCK_NOVA_CANVAS_MODEL_ID']:
            config['BEDROCK_NOVA_CANVAS_MODEL_ID'] = 'amazon.nova-canvas-v1:0'
            print(f"[Config] BEDROCK_NOVA_CANVAS_MODEL_ID: 기본값 사용")
        
        if 'KNOWLEDGE_BASE_BUCKET' not in config or not config['KNOWLEDGE_BASE_BUCKET']:
            config['KNOWLEDGE_BASE_BUCKET'] = os.environ.get('KNOWLEDGE_BASE_BUCKET', '')
            print(f"[Config] KNOWLEDGE_BASE_BUCKET: 환경변수에서 가져옴")
        
        return config
    except Exception as e:
        print(f"❌ CRITICAL: Secrets Manager에서 설정을 가져올 수 없습니다: {str(e)}")
        print(f"❌ Secret 이름: {secret_name}")
        print(f"❌ Region: {region_name}")
        
        # 런타임 오류 방지를 위해 기본값 반환 (최소한의 동작 보장)
        print(f"⚠️  WARNING: 기본값으로 fallback합니다. 일부 기능이 제한될 수 있습니다.")
        return {
            'AWS_REGION': region_name,
            'KNOWLEDGE_BASE_ID': os.environ.get('KNOWLEDGE_BASE_ID', ''),
            'KNOWLEDGE_BASE_BUCKET': os.environ.get('KNOWLEDGE_BASE_BUCKET', ''),
            'BEDROCK_MODEL_ARN': os.environ.get('BEDROCK_MODEL_ARN', ''),
            'IAM_ROLE_ARN': os.environ.get('IAM_ROLE_ARN', ''),
            'BEDROCK_CLAUDE_MODEL_ID': os.environ.get('BEDROCK_CLAUDE_MODEL_ID', 'anthropic.claude-sonnet-4-5-20250929-v1:0'),
            'BEDROCK_NOVA_CANVAS_MODEL_ID': os.environ.get('BEDROCK_NOVA_CANVAS_MODEL_ID', 'amazon.nova-canvas-v1:0'),
            'BEDROCK_LLM_MODEL_ID': os.environ.get('BEDROCK_LLM_MODEL_ID', 'anthropic.claude-sonnet-4-20250514-v1:0'),
        }
