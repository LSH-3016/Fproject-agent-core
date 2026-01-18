# 설정 체크리스트

배포 전에 반드시 설정해야 하는 항목들입니다.

## ✅ 1. GitHub Secrets 설정

**위치**: Repository Settings > Secrets and variables > Actions

설정할 Secrets:
```
AWS_ACCESS_KEY_ID: <your-aws-access-key-id>
AWS_SECRET_ACCESS_KEY: <your-aws-secret-access-key>
```

### AWS IAM User 생성 방법
1. AWS Console > IAM > Users > Create user
2. User name: `github-actions-deploy`
3. Attach policies:
   - `AmazonEC2ContainerRegistryFullAccess` (ECR 접근)
   - `AWSLambda_FullAccess` (Lambda 배포)
4. Create access key > Application running outside AWS
5. Access key와 Secret key를 GitHub Secrets에 등록

---

## ✅ 2. AWS IAM Role 생성 (Agent Runtime용)

**위치**: AWS Console > IAM > Roles > Create role

### Trust Policy
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

### Permissions Policy
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:Retrieve"
      ],
      "Resource": "arn:aws:bedrock:us-east-1:*:knowledge-base/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:BatchCheckLayerAvailability"
      ],
      "Resource": "*"
    }
  ]
}
```

### Role 생성 후
Role ARN을 복사: `arn:aws:iam::123456789012:role/AgentCoreExecutionRole`

---

## ✅ 3. deploy_from_ecr.py 설정

**파일**: `deploy_from_ecr.py`

수정할 부분:
```python
# Line 11-12
ECR_REPOSITORY = "diary-orchestrator-agent"  # 원하는 ECR 저장소 이름
IMAGE_TAG = "latest"  # 또는 특정 commit SHA

# Line 14
EXECUTION_ROLE = "arn:aws:iam::123456789012:role/AgentCoreExecutionRole"  # ✅ 여기 수정!
```

---

## ✅ 4. .github/workflows/deploy-to-ecr.yml 설정

**파일**: `.github/workflows/deploy-to-ecr.yml`

확인할 부분:
```yaml
# Line 9-11
env:
  AWS_REGION: us-east-1  # ✅ 사용할 AWS 리전
  ECR_REPOSITORY: diary-orchestrator-agent  # ✅ ECR 저장소 이름
  IMAGE_TAG: ${{ github.sha }}
```

---

## ✅ 5. 환경 변수 확인

**파일**: `agent/orchestrator/question/agent.py`

확인할 부분:
```python
# Line 18-19
os.environ['KNOWLEDGE_BASE_ID'] = 'LOCNRTBMNB'  # ✅ 실제 Knowledge Base ID
os.environ['AWS_REGION'] = 'us-east-1'  # ✅ 실제 리전
```

---

## ✅ 6. Bedrock 모델 ARN 확인

**파일**: `agent/orchestrator/orchestra_agent.py`

확인할 부분:
```python
# Line 95
model="arn:aws:bedrock:us-east-1:324547056370:inference-profile/global.anthropic.claude-sonnet-4-5-20250929-v1:0"
# ✅ 실제 사용 가능한 모델 ARN인지 확인
```

### 모델 ARN 확인 방법
```bash
aws bedrock list-foundation-models --region us-east-1
```

---

## 📋 설정 순서

### Step 1: AWS 설정
1. [ ] IAM User 생성 (GitHub Actions용)
2. [ ] IAM Role 생성 (Agent Runtime용)
3. [ ] Knowledge Base ID 확인
4. [ ] Bedrock 모델 접근 권한 확인

### Step 2: GitHub 설정
1. [ ] GitHub Secrets 등록
   - AWS_ACCESS_KEY_ID
   - AWS_SECRET_ACCESS_KEY

### Step 3: 코드 설정
1. [ ] `deploy_from_ecr.py` - EXECUTION_ROLE 수정
2. [ ] `agent/orchestrator/question/agent.py` - KNOWLEDGE_BASE_ID 확인
3. [ ] `agent/orchestrator/orchestra_agent.py` - 모델 ARN 확인
4. [ ] `.github/workflows/deploy-to-ecr.yml` - AWS_REGION, ECR_REPOSITORY 확인

### Step 4: 배포
1. [ ] Git commit & push
2. [ ] GitHub Actions 실행 확인
3. [ ] ECR 이미지 확인
4. [ ] `python deploy_from_ecr.py` 실행

---

## 🔍 설정 확인 명령어

### AWS 자격 증명 확인
```bash
aws sts get-caller-identity
```

### ECR 저장소 확인
```bash
aws ecr describe-repositories --repository-names diary-orchestrator-agent
```

### Knowledge Base 확인
```bash
aws bedrock-agent list-knowledge-bases --region us-east-1
```

### Bedrock 모델 확인
```bash
aws bedrock list-foundation-models --region us-east-1 | grep claude
```

---

## ⚠️ 주의사항

1. **IAM Role ARN**: 반드시 실제 생성한 Role의 ARN으로 교체
2. **Knowledge Base ID**: 실제 사용 중인 Knowledge Base ID 확인
3. **AWS Region**: 모든 파일에서 동일한 리전 사용
4. **GitHub Secrets**: 절대 코드에 직접 입력하지 말 것
5. **ECR 저장소 이름**: 고유한 이름 사용 (중복 불가)

---

## 🆘 문제 해결

### GitHub Actions 실패
- AWS Secrets 확인
- IAM User 권한 확인
- ECR 저장소 이름 중복 확인

### Agent Core 배포 실패
- IAM Role ARN 확인
- ECR 이미지 URI 확인
- Bedrock 모델 접근 권한 확인

### Knowledge Base 접근 실패
- Knowledge Base ID 확인
- IAM Role에 Bedrock Retrieve 권한 확인
- 리전 일치 확인
