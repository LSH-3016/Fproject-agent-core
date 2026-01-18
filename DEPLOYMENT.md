# 배포 가이드

## 사전 준비

### 1. AWS 설정
- AWS CLI 설치 및 구성
- IAM Role 생성 (Bedrock, Lambda, ECR, CloudWatch, Secrets Manager 권한)
- Knowledge Base 생성
- **Secrets Manager에 `agent-core-secret` 생성 완료** ✅

### 2. GitHub Secrets 설정
Repository Settings > Secrets and variables > Actions

```
AWS_ACCESS_KEY_ID: <your-access-key>
AWS_SECRET_ACCESS_KEY: <your-secret-key>
```

## 설정 완료 ✅

모든 민감 정보는 AWS Secrets Manager에 안전하게 저장되어 있습니다:

```
Secret Name: agent-core-secret
```

애플리케이션이 자동으로 Secrets Manager에서 다음 설정을 가져옵니다:
- KNOWLEDGE_BASE_ID
- AWS_REGION
- BEDROCK_MODEL_ARN
- IAM_ROLE_ARN

## 배포 순서

### 1. GitHub Actions로 ECR 배포
```bash
git add .
git commit -m "Deploy to ECR"
git push origin main
```

GitHub Actions가 자동으로:
- Docker 이미지 빌드
- ECR에 푸시

### 2. Agent Core 배포
```bash
python deploy_from_ecr.py
```

## Secrets Manager 확인

```bash
# 시크릿 확인
aws secretsmanager get-secret-value --secret-id agent-core-secret

# 시크릿 업데이트 (필요시)
aws secretsmanager update-secret --secret-id agent-core-secret --secret-string '{"KNOWLEDGE_BASE_ID":"...","AWS_REGION":"...","BEDROCK_MODEL_ARN":"...","IAM_ROLE_ARN":"..."}'
```

## 참고 문서
- [CI/CD 가이드](CICD_DEPLOYMENT_GUIDE.md)
- [README](README.md)
