"""
ECR 이미지를 사용하여 Agent Core Runtime 배포
GitHub Actions로 빌드된 이미지를 가져와서 Agent Core에 배포합니다.
"""
import boto3
import json
import sys
import os

# Secrets Manager에서 설정 가져오기 (필수)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'agent'))

print("=" * 60)
print("🔐 Secrets Manager에서 설정 로드 중...")
print("=" * 60)

try:
    from utils.secrets import get_config
    config = get_config()
    print("✅ Secrets Manager 로드 성공")
except Exception as e:
    print(f"❌ CRITICAL ERROR: Secrets Manager 접근 실패")
    print(f"❌ Error: {str(e)}")
    print(f"❌ Secret 이름: agent-core-secret")
    print(f"❌ Region: {os.environ.get('AWS_REGION', 'us-east-1')}")
    print("\n💡 해결 방법:")
    print("1. GitHub Actions의 AWS credentials 권한 확인")
    print("2. IAM 정책에 secretsmanager:GetSecretValue 권한 추가")
    print("3. Secret 'agent-core-secret'이 us-east-1에 존재하는지 확인")
    sys.exit(1)

# AWS 세션 설정
boto_session = boto3.Session()
region = config.get('AWS_REGION', 'us-east-1')
account_id = boto_session.client('sts').get_caller_identity()['Account']

# ========================================
# 설정값 (Secrets Manager에서만 가져옴)
# ========================================

# ECR 설정
ECR_REPOSITORY = "diary-orchestrator-agent"
# 항상 latest 태그 사용 (Agent Core Runtime은 이미지 digest로 변경 감지)
IMAGE_TAG = 'latest'
print(f"💡 IMAGE_TAG 환경변수 무시, 항상 'latest' 사용")

# Agent 설정
AGENT_NAME = "diary_orchestrator_agent"

# IAM Role ARN (필수)
EXECUTION_ROLE = config.get('IAM_ROLE_ARN', '').strip()

# Knowledge Base 설정
KNOWLEDGE_BASE_ID = config.get('KNOWLEDGE_BASE_ID', '').strip()
KNOWLEDGE_BASE_BUCKET = config.get('KNOWLEDGE_BASE_BUCKET', '').strip()
BEDROCK_MODEL_ARN = config.get('BEDROCK_MODEL_ARN', '').strip()
BEDROCK_CLAUDE_MODEL_ID = config.get('BEDROCK_CLAUDE_MODEL_ID', '').strip()
BEDROCK_NOVA_CANVAS_MODEL_ID = config.get('BEDROCK_NOVA_CANVAS_MODEL_ID', '').strip()
BEDROCK_LLM_MODEL_ID = config.get('BEDROCK_LLM_MODEL_ID', '').strip()

# ========================================

# ECR 이미지 URI 생성
ecr_image_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com/{ECR_REPOSITORY}:{IMAGE_TAG}"

print("\n" + "=" * 60)
print("🚀 Agent Core Runtime 배포 시작")
print("=" * 60)
print(f"ECR Image URI: {ecr_image_uri}")
print(f"Image Tag: {IMAGE_TAG}")
print(f"Agent Name: {AGENT_NAME}")
print(f"Region: {region}")
print("=" * 60)

# 필수값 검증
if not EXECUTION_ROLE:
    print("❌ CRITICAL ERROR: IAM_ROLE_ARN이 Secrets Manager에 없습니다!")
    print("   다음 명령으로 추가하세요:")
    print(f"   aws secretsmanager update-secret --secret-id agent-core-secret --secret-string '{{...\"IAM_ROLE_ARN\":\"arn:aws:iam::...\"}}'")
    sys.exit(1)

if not KNOWLEDGE_BASE_ID:
    print("⚠️  경고: KNOWLEDGE_BASE_ID가 비어있습니다.")

if not KNOWLEDGE_BASE_BUCKET:
    print("⚠️  경고: KNOWLEDGE_BASE_BUCKET이 비어있습니다.")

print(f"\n✅ Execution Role: {EXECUTION_ROLE[:50]}...")
print(f"✅ Knowledge Base ID: {KNOWLEDGE_BASE_ID}")
print(f"✅ Knowledge Base Bucket: {KNOWLEDGE_BASE_BUCKET}")

# Bedrock AgentCore 클라이언트
client = boto3.client('bedrock-agentcore-control', region_name=region)

# 환경변수 구성 (최소한만 설정, 나머지는 런타임에서 Secrets Manager 사용)
environment_variables = {
    'AWS_REGION': region,
    'SECRET_NAME': 'agent-core-secret',  # Secrets Manager 이름만 전달
}

# KNOWLEDGE_BASE_BUCKET은 image_generator에서 필요하므로 환경변수로도 설정
if KNOWLEDGE_BASE_BUCKET:
    environment_variables['KNOWLEDGE_BASE_BUCKET'] = KNOWLEDGE_BASE_BUCKET

print(f"\n환경변수 설정 ({len(environment_variables)}개):")
print(f"  ✓ AWS_REGION: {region}")
print(f"  ✓ SECRET_NAME: agent-core-secret")
if KNOWLEDGE_BASE_BUCKET:
    print(f"  ✓ KNOWLEDGE_BASE_BUCKET: {KNOWLEDGE_BASE_BUCKET}")
print(f"\n💡 나머지 설정은 런타임에서 Secrets Manager에서 로드됩니다.")

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
            # ARN에서 ID 추출 (마지막 부분)
            runtime_arn = existing_runtime['agentRuntimeArn']
            runtime_id = runtime_arn.split('/')[-1]
            
            # 🔥 기존 Runtime 삭제 (강제 재생성)
            print(f"\n🗑️  기존 Runtime 삭제 중 (ID: {runtime_id})...")
            print(f"💡 이유: update_agent_runtime이 이미지를 제대로 업데이트하지 않음")
            try:
                client.delete_agent_runtime(agentRuntimeId=runtime_id)
                print("✅ Runtime 삭제 완료")
                
                # 삭제 완료 대기
                import time
                print("⏳ 삭제 완료 대기 중 (10초)...")
                time.sleep(10)
            except Exception as delete_error:
                print(f"⚠️  삭제 실패 (무시하고 계속): {str(delete_error)}")
            
            # 새 Runtime 생성
            print(f"\n🚀 새 Runtime 생성 중...")
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
            print("✅ 새 Runtime 생성 완료!")
            agent_arn = response['agentRuntimeArn']
        else:
            # 새 Runtime 생성 (Public 모드)
            print("\n새 Agent Runtime 생성 중 (Public 모드)...")
            response = client.create_agent_runtime(
                agentRuntimeName=AGENT_NAME,
                agentRuntimeArtifact={
                    'containerConfiguration': {
                        'containerUri': ecr_image_uri  # ✅ imageUri → containerUri
                    }
                },
                roleArn=EXECUTION_ROLE,
                networkConfiguration={
                    'networkMode': 'PUBLIC'  # VPC 사용 안 함
                },
                environmentVariables=environment_variables,
                lifecycleConfiguration={
                    'idleRuntimeSessionTimeout': 3600,  # 1시간
                    'maxLifetime': 28800  # 8시간
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
                    'containerUri': ecr_image_uri  # ✅ imageUri → containerUri
                }
            },
            roleArn=EXECUTION_ROLE,
            networkConfiguration={
                'networkMode': 'PUBLIC'  # VPC 사용 안 함
            },
            environmentVariables=environment_variables,
            lifecycleConfiguration={
                'idleRuntimeSessionTimeout': 3600,  # 1시간
                'maxLifetime': 28800  # 8시간
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
    print(f"\n환경변수:")
    for key, value in environment_variables.items():
        print(f"  - {key}: {value}")
    print(f"\n💡 런타임 설정은 Secrets Manager '{environment_variables.get('SECRET_NAME')}'에서 로드됩니다.")
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
