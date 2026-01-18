"""
ECR 이미지를 사용하여 Agent Core Runtime 배포
GitHub Actions로 빌드된 이미지를 가져와서 Agent Core에 배포합니다.
"""
from bedrock_agentcore_starter_toolkit import Runtime
from boto3.session import Session
import sys

# AWS 세션 설정
boto_session = Session()
region = boto_session.region_name
account_id = boto_session.client('sts').get_caller_identity()['Account']

# ========================================
# ⚠️ 아래 설정값들을 수정하세요
# ========================================

# ECR 설정
ECR_REPOSITORY = "diary-orchestrator-agent"  # ECR 저장소 이름
IMAGE_TAG = "latest"  # 또는 특정 commit SHA

# Agent 설정
AGENT_NAME = "diary_orchestrator_agent"

# ✅ TODO: 실제 IAM Role ARN으로 교체 필요!
# AWS Console > IAM > Roles에서 생성한 Role의 ARN을 입력하세요
EXECUTION_ROLE = "<your-runtime-execution-role-arn>"  # 예: "arn:aws:iam::123456789012:role/AgentCoreExecutionRole"

# ========================================

# ECR 이미지 URI 생성
ecr_image_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com/{ECR_REPOSITORY}:{IMAGE_TAG}"

print("=" * 60)
print("🚀 Agent Core Runtime 배포 시작")
print("=" * 60)
print(f"ECR Image URI: {ecr_image_uri}")
print(f"Agent Name: {AGENT_NAME}")
print(f"Region: {region}")
print("=" * 60)

# Execution Role 확인
if EXECUTION_ROLE == "<your-runtime-execution-role-arn>":
    print("❌ 오류: EXECUTION_ROLE을 설정하지 않았습니다!")
    print("   deploy_from_ecr.py 파일을 열어 EXECUTION_ROLE을 실제 IAM Role ARN으로 수정하세요.")
    print("   예: arn:aws:iam::123456789012:role/AgentCoreExecutionRole")
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
    print("=" * 60)
    
except Exception as e:
    print("=" * 60)
    print("❌ 배포 실패")
    print("=" * 60)
    print(f"Error: {str(e)}")
    print("=" * 60)
    sys.exit(1)
