"""
설정 확인 스크립트
배포 전에 필수 설정이 완료되었는지 확인합니다.
"""
import os
import sys
import re

def check_file_setting(filepath, pattern, description):
    """파일에서 특정 패턴이 수정되었는지 확인"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            if re.search(pattern, content):
                print(f"❌ {description}")
                print(f"   파일: {filepath}")
                return False
            else:
                print(f"✅ {description}")
                return True
    except FileNotFoundError:
        print(f"❌ 파일을 찾을 수 없습니다: {filepath}")
        return False

def main():
    print("=" * 60)
    print("🔍 설정 확인 시작")
    print("=" * 60)
    
    all_ok = True
    
    # 1. deploy_from_ecr.py 확인
    print("\n[1] deploy_from_ecr.py 확인")
    if not check_file_setting(
        "deploy_from_ecr.py",
        r'EXECUTION_ROLE = "<your-runtime-execution-role-arn>"',
        "IAM Role ARN 설정"
    ):
        all_ok = False
        print("   💡 EXECUTION_ROLE을 실제 IAM Role ARN으로 수정하세요")
    
    # 2. question agent 확인
    print("\n[2] agent/orchestrator/question/agent.py 확인")
    if not check_file_setting(
        "agent/orchestrator/question/agent.py",
        r"os\.environ\['KNOWLEDGE_BASE_ID'\] = 'LOCNRTBMNB'",
        "Knowledge Base ID 확인 (기본값 사용 중)"
    ):
        print("   💡 실제 Knowledge Base ID로 수정이 필요할 수 있습니다")
    
    # 3. GitHub Secrets 안내
    print("\n[3] GitHub Secrets 확인")
    print("⚠️  GitHub Repository Settings에서 다음 Secrets를 설정했는지 확인하세요:")
    print("   - AWS_ACCESS_KEY_ID")
    print("   - AWS_SECRET_ACCESS_KEY")
    
    # 4. AWS 자격 증명 확인
    print("\n[4] AWS 자격 증명 확인")
    try:
        import boto3
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"✅ AWS 자격 증명 확인됨")
        print(f"   Account: {identity['Account']}")
        print(f"   ARN: {identity['Arn']}")
    except Exception as e:
        print(f"❌ AWS 자격 증명 오류: {str(e)}")
        print("   💡 AWS CLI를 설정하거나 자격 증명을 확인하세요")
        all_ok = False
    
    # 결과 출력
    print("\n" + "=" * 60)
    if all_ok:
        print("✅ 모든 필수 설정이 완료되었습니다!")
        print("   다음 단계: git push 후 GitHub Actions 확인")
    else:
        print("❌ 일부 설정이 완료되지 않았습니다")
        print("   SETUP_CHECKLIST.md를 참고하여 설정을 완료하세요")
    print("=" * 60)
    
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
