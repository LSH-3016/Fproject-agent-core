"""
ECR 이미지를 사용하여 Agent Core Runtime 배포
GitHub Actions로 빌드된 이미지를 가져와서 Agent Core에 배포합니다.
"""
import boto3
import json
import sys
import os

# Secrets Manager에서 설정 가져오기
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'agent'))
from utils.secrets import get_config

config = get_config()

# AWS 세션 설정
boto_session = boto3.Session()
region = config.get('AWS_REGION', boto_session.region_name)
account_id = boto_session.client('sts').get_caller_identity()['Account']

# ========================================
# 설정값 (Secrets Manager에서 자동으로 가져옴)
# ========================================

# ECR 설정
ECR_REPOSITORY = "diary-orchestrator-agent"
# 환경변수에서 이미지 태그 가져오기 (GitHub Actions에서 설정)
IMAGE_TAG = os.environ.get('IMAGE_TAG', 'latest')

# Agent 설정
AGENT_NAME = "diary_orchestrator_agent"

# IAM Role ARN (Secrets Manager에서 가져옴)
EXECUTION_ROLE = config.get('IAM_ROLE_ARN', '')

# ========================================

# ECR 이미지 URI 생성
ecr_image_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com/{ECR_REPOSITORY}:{IMAGE_TAG}"

print("=" * 60)
print("🚀 Agent Core Runtime 배포 시작")
print("=" * 60)
print(f"ECR Image URI: {ecr_image_uri}")
print(f"Image Tag: {IMAGE_TAG}")
print(f"Agent Name: {AGENT_NAME}")
print(f"Region: {region}")
print("=" * 60)

# Execution Role 확인
if not EXECUTION_ROLE:
    print("❌ 오류: IAM Role ARN을 Secrets Manager에서 가져올 수 없습니다!")
    print("   Secrets Manager에 'agent-core-secret'이 올바르게 설정되어 있는지 확인하세요.")
    sys.exit(1)

# Bedrock AgentCore 클라이언트
client = boto3.client('bedrock-agentcore-control', region_name=region)

try:
    # 기존 Agent Runtime 확인
    print("\n기존 Agent Runtime 확인 중...")
    try:
        list_response = client.list_agent_runtimes()
        existing_runtime = None
        
        for runtime in list_response.get('agentRuntimes', []):
            if runtime.get('agentRuntimeName') == AGENT_NAME:
                existing_runtime = runtime
                print(f"✅ 기존 Runtime 발견: {runtime['agentRuntimeArn']}")
                break
        
        if existing_runtime:
            # 기존 Runtime 업데이트
            print("\n기존 Runtime 업데이트 중...")
            response = client.update_agent_runtime(
                agentRuntimeArn=existing_runtime['agentRuntimeArn'],
                agentRuntimeArtifact={
                    'containerConfiguration': {
                        'imageUri': ecr_image_uri
                    }
                }
            )
            print("✅ Agent Runtime 업데이트 완료!")
            agent_arn = existing_runtime['agentRuntimeArn']
        else:
            # 새 Runtime 생성 (Public 모드)
            print("\n새 Agent Runtime 생성 중 (Public 모드)...")
            response = client.create_agent_runtime(
                agentRuntimeName=AGENT_NAME,
                agentRuntimeArtifact={
                    'containerConfiguration': {
                        'imageUri': ecr_image_uri
                    }
                },
                roleArn=EXECUTION_ROLE,
                networkConfiguration={
                    'networkMode': 'PUBLIC'  # VPC 사용 안 함
                }
            )
            print("✅ Agent Runtime 생성 완료!")
            agent_arn = response['agentRuntimeArn']
        
    except client.exceptions.ResourceNotFoundException:
        # Runtime이 없으면 새로 생성 (Public 모드)
        print("\n새 Agent Runtime 생성 중 (Public 모드)...")
        response = client.create_agent_runtime(
            agentRuntimeName=AGENT_NAME,
            agentRuntimeArtifact={
                'containerConfiguration': {
                    'imageUri': ecr_image_uri
                }
            },
            roleArn=EXECUTION_ROLE,
            networkConfiguration={
                'networkMode': 'PUBLIC'  # VPC 사용 안 함
            }
        )
        print("✅ Agent Runtime 생성 완료!")
        agent_arn = response['agentRuntimeArn']
    
    print("=" * 60)
    print("✅ Agent Runtime 배포 완료!")
    print("=" * 60)
    print(f"Agent Name: {AGENT_NAME}")
    print(f"Agent Runtime ARN: {agent_arn}")
    print(f"Image URI: {ecr_image_uri}")
    print(f"Image Tag: {IMAGE_TAG}")
    print(f"Network Mode: PUBLIC (VPC 사용 안 함)")
    print("=" * 60)
    
except Exception as e:
    print("=" * 60)
    print("❌ 배포 실패")
    print("=" * 60)
    print(f"Error: {str(e)}")
    print("\n💡 문제 해결:")
    print("1. IAM Role 권한 확인")
    print("2. ECR 이미지 존재 확인")
    print("3. Bedrock AgentCore 서비스 활성화 확인")
    print("=" * 60)
    sys.exit(1)
