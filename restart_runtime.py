"""
Agent Core Runtime 재시작
Runtime을 삭제하고 재생성하여 새 이미지를 강제로 적용합니다.
"""
import boto3
import sys
import os
import time

# Secrets Manager에서 설정 가져오기
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'agent'))

try:
    from utils.secrets import get_config
    config = get_config()
except Exception as e:
    print(f"❌ Secrets Manager 접근 실패: {str(e)}")
    sys.exit(1)

region = config.get('AWS_REGION', 'us-east-1')
AGENT_NAME = "diary_orchestrator_agent"
ECR_REPOSITORY = "diary-orchestrator-agent"
IMAGE_TAG = os.environ.get('IMAGE_TAG', 'latest')

boto_session = boto3.Session()
account_id = boto_session.client('sts').get_caller_identity()['Account']
ecr_image_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com/{ECR_REPOSITORY}:{IMAGE_TAG}"

EXECUTION_ROLE = config.get('IAM_ROLE_ARN', '').strip()
KNOWLEDGE_BASE_BUCKET = config.get('KNOWLEDGE_BASE_BUCKET', '').strip()

client = boto3.client('bedrock-agentcore-control', region_name=region)

print("=" * 60)
print("🔄 Agent Runtime 재시작")
print("=" * 60)
print(f"Agent Name: {AGENT_NAME}")
print(f"New Image: {ecr_image_uri}")
print("=" * 60)

try:
    # 1. 기존 Runtime 찾기
    list_response = client.list_agent_runtimes()
    runtime_id = None
    runtime_arn = None
    
    for runtime in list_response.get('agentRuntimes', []):
        if runtime.get('agentRuntimeName') == AGENT_NAME:
            runtime_arn = runtime['agentRuntimeArn']
            runtime_id = runtime_arn.split('/')[-1]
            break
    
    if not runtime_id:
        print("❌ Runtime을 찾을 수 없습니다.")
        print("💡 deploy_from_ecr.py를 먼저 실행하세요.")
        sys.exit(1)
    
    print(f"✅ Runtime 발견: {runtime_id}")
    
    # 2. Runtime 삭제
    print(f"\n🗑️  Runtime 삭제 중...")
    client.delete_agent_runtime(agentRuntimeId=runtime_id)
    print("✅ Runtime 삭제 완료")
    
    # 3. 잠시 대기 (삭제 완료 대기)
    print("\n⏳ 삭제 완료 대기 중 (10초)...")
    time.sleep(10)
    
    # 4. 새 Runtime 생성
    print(f"\n🚀 새 Runtime 생성 중...")
    
    environment_variables = {
        'AWS_REGION': region,
        'SECRET_NAME': 'agent-core-secret',
    }
    
    if KNOWLEDGE_BASE_BUCKET:
        environment_variables['KNOWLEDGE_BASE_BUCKET'] = KNOWLEDGE_BASE_BUCKET
    
    response = client.create_agent_runtime(
        agentRuntimeName=AGENT_NAME,
        agentRuntimeArtifact={
            'containerConfiguration': {
                'containerUri': ecr_image_uri
            }
        },
        roleArn=EXECUTION_ROLE,
        networkConfiguration={
            'networkMode': 'PUBLIC'
        },
        environmentVariables=environment_variables,
        lifecycleConfiguration={
            'idleRuntimeSessionTimeout': 3600,
            'maxLifetime': 28800
        }
    )
    
    new_runtime_arn = response['agentRuntimeArn']
    
    print("=" * 60)
    print("✅ Runtime 재시작 완료!")
    print("=" * 60)
    print(f"New Runtime ARN: {new_runtime_arn}")
    print(f"Image URI: {ecr_image_uri}")
    print(f"Image Tag: {IMAGE_TAG}")
    print("=" * 60)
    print("\n💡 새 Runtime이 시작되는 데 1-2분 정도 걸릴 수 있습니다.")
    print("💡 상태 확인: python check_runtime_status.py")
    print("=" * 60)
    
except Exception as e:
    print(f"❌ 재시작 실패: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
