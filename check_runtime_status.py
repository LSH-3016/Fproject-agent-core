"""
Agent Core Runtime 상태 확인 및 재시작
"""
import boto3
import sys
import os

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

client = boto3.client('bedrock-agentcore-control', region_name=region)

print("=" * 60)
print("🔍 Agent Runtime 상태 확인")
print("=" * 60)

try:
    # Runtime 목록 조회
    list_response = client.list_agent_runtimes()
    
    for runtime in list_response.get('agentRuntimes', []):
        if runtime.get('agentRuntimeName') == AGENT_NAME:
            runtime_arn = runtime['agentRuntimeArn']
            runtime_id = runtime_arn.split('/')[-1]
            
            print(f"Runtime ARN: {runtime_arn}")
            print(f"Runtime ID: {runtime_id}")
            print(f"Status: {runtime.get('status', 'UNKNOWN')}")
            print(f"Created: {runtime.get('createdAt', 'N/A')}")
            print(f"Updated: {runtime.get('updatedAt', 'N/A')}")
            
            # 상세 정보 조회
            try:
                detail_response = client.get_agent_runtime(
                    agentRuntimeId=runtime_id
                )
                
                runtime_detail = detail_response.get('agentRuntime', {})
                artifact = runtime_detail.get('agentRuntimeArtifact', {})
                container_config = artifact.get('containerConfiguration', {})
                
                print(f"\n현재 이미지:")
                print(f"  {container_config.get('containerUri', 'N/A')}")
                
                print(f"\n환경변수:")
                env_vars = runtime_detail.get('environmentVariables', {})
                for key, value in env_vars.items():
                    print(f"  {key}: {value}")
                
            except Exception as e:
                print(f"⚠️  상세 정보 조회 실패: {str(e)}")
            
            # Runtime 재시작 옵션
            print("\n" + "=" * 60)
            print("💡 Runtime을 재시작하려면 다음 명령을 실행하세요:")
            print("=" * 60)
            print(f"python restart_runtime.py")
            print("=" * 60)
            
            sys.exit(0)
    
    print("❌ Runtime을 찾을 수 없습니다.")
    sys.exit(1)
    
except Exception as e:
    print(f"❌ 에러 발생: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
