"""
ECR 이미지를 사용하여 Agent Core Runtime 배포
GitHub Actions로 빌드된 이미지를 가져와서 Agent Core에 배포합니다.
"""
from bedrock_agentcore_starter_toolkit import Runtime
from boto3.session import Session
import sys
import os

# Secrets Manager에서 설정 가져오기
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'agent'))
from utils.secrets import get_config

config = get_config()

# AWS 세션 설정
boto_session = Session()
region = config.get('AWS_REGION', boto_session.region_name)
account_id = boto_session.client('sts').get_caller_identity()['Account']

# ========================================
# 설정값 (Secrets Manager에서 자동으로 가져옴)
# ========================================

# ECR 설정
ECR_REPOSITORY = "diary-orchestrator-agent"
# 환경변수에서 이미지 태그 가져오기 (GitHub Actions에서 설정)
# 없으면 'latest' 사용
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
if not EXECUTION_ROLE or EXECUTION_ROLE == "<your-runtime-execution-role-arn>":
    print("❌ 오류: IAM Role ARN을 Secrets Manager에서 가져올 수 없습니다!")
    print("   Secrets Manager에 'agent-core-secret'이 올바르게 설정되어 있는지 확인하세요.")
    sys.exit(1)

# Runtime 설정
agentcore_runtime = Runtime()

try:
    # ECR 이미지를 사용하여 설정
    response = agentcore_runtime.configure(
        image_uri=ecr_image_uri,  # ECR 이미지 URI 사용
        execution_role=EXECUTION_ROLE,
        region=region,
        agent_name=AGENT_NAME,
    )
    
    print("✅ Agent 설정 완료")
    
    # Agent 배포
    launch_result = agentcore_runtime.launch(auto_update_on_conflict=True)
    
    print("=" * 60)
    print("✅ Agent Runtime 배포 완료!")
    print("=" * 60)
    print(f"Agent Name: {AGENT_NAME}")
    print(f"Agent Runtime ARN: {launch_result.agent_arn}")
    print(f"Image URI: {ecr_image_uri}")
    print(f"Image Tag: {IMAGE_TAG}")
    print("=" * 60)
    
except Exception as e:
    print("=" * 60)
    print("❌ 배포 실패")
    print("=" * 60)
    print(f"Error: {str(e)}")
    print("=" * 60)
    sys.exit(1)
