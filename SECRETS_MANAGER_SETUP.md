# Secrets Manager 설정 가이드

## 개요

Agent Core Runtime은 AWS Secrets Manager를 사용하여 모든 설정을 중앙 집중식으로 관리합니다.

## Secret 구성

### Secret 이름
`agent-core-secret`

### Secret 내용
```json
{
  "KNOWLEDGE_BASE_ID": "LOCNRTBMNB",
  "KNOWLEDGE_BASE_BUCKET": "knowledge-base-test-6575574",
  "AWS_REGION": "us-east-1",
  "BEDROCK_MODEL_ARN": "arn:aws:bedrock:us-east-1:324547056370:inference-profile/global.anthropic.claude-sonnet-4-5-20250929-v1:0",
  "IAM_ROLE_ARN": "arn:aws:iam::324547056370:role/DiaryOrchestratorAgentRole",
  "BEDROCK_CLAUDE_MODEL_ID": "arn:aws:bedrock:us-east-1:324547056370:inference-profile/global.anthropic.claude-sonnet-4-5-20250929-v1:0",
  "BEDROCK_NOVA_CANVAS_MODEL_ID": "amazon.nova-canvas-v1:0",
  "BEDROCK_LLM_MODEL_ID": "us.anthropic.claude-sonnet-4-20250514-v1:0"
}
```

## 아키텍처

```
배포 시점:
  deploy_from_ecr.py → Secrets Manager 읽기 → IAM_ROLE_ARN 추출
  ↓
  Agent Core Runtime 생성 (환경변수: AWS_REGION, SECRET_NAME, KNOWLEDGE_BASE_BUCKET)

런타임 시점:
  server.py 시작 → utils/secrets.py → Secrets Manager 읽기 → 모든 설정 로드
```

## 환경변수

Agent Core Runtime에 설정되는 최소 환경변수:
```python
{
    'AWS_REGION': 'us-east-1',
    'SECRET_NAME': 'agent-core-secret',
    'KNOWLEDGE_BASE_BUCKET': 'knowledge-base-test-6575574'
}
```

나머지 설정은 런타임에서 Secrets Manager에서 로드됩니다.

## Secret 업데이트

```bash
# JSON 파일 생성
cat > secret.json << EOF
{
  "KNOWLEDGE_BASE_ID": "LOCNRTBMNB",
  "KNOWLEDGE_BASE_BUCKET": "knowledge-base-test-6575574",
  ...
}
EOF

# Secret 업데이트
aws secretsmanager update-secret \
  --secret-id agent-core-secret \
  --secret-string file://secret.json

# 확인
aws secretsmanager get-secret-value \
  --secret-id agent-core-secret \
  --query SecretString \
  --output text
```

## IAM 권한

Agent Core Runtime의 Execution Role에 필요한 권한:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:*:secret:agent-core-secret-*"
    }
  ]
}
```

## 장점

1. **보안**: 민감 정보가 Agent Core 설정에 노출되지 않음
2. **유연성**: Secret 변경 시 재배포 불필요 (컨테이너 재시작만)
3. **중앙 관리**: 모든 설정이 Secrets Manager에 집중
4. **감사 추적**: 변경 이력 자동 기록

## 트러블슈팅

### Secrets Manager 접근 실패
```
❌ CRITICAL: Secrets Manager에서 설정을 가져올 수 없습니다
```

**해결:**
- IAM Role에 `secretsmanager:GetSecretValue` 권한 확인
- Secret 이름이 `agent-core-secret`인지 확인
- Region이 `us-east-1`인지 확인

### CloudWatch Logs 확인
```bash
# Log Group
/aws/bedrock/agentcore/diary_orchestrator_agent

# 최근 로그 확인
aws logs tail /aws/bedrock/agentcore/diary_orchestrator_agent --follow
```

## 배포

Secret 변경 후:
1. GitHub Actions에서 자동 배포 또는
2. 수동 배포: `python deploy_from_ecr.py`

컨테이너가 재시작되면 새 설정이 자동으로 로드됩니다.

