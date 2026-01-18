# Diary Orchestrator Agent

AWS Bedrock Agent Core Runtime을 사용한 일기 관리 AI Agent 시스템

## 주요 기능

### 1. 질문 답변 (Question Agent)
Knowledge Base를 검색하여 사용자 질문에 답변
- 예: "2026-01-13일에 나 무슨 영화봤어?"

### 2. 일기 생성 (Summarize Agent)
사용자 데이터를 분석하여 일기 형식으로 작성
- 예: "오늘 영화 보고 파스타 먹었어" → 일기 형식 변환

### 3. 데이터 그대로 반환 (No Processing)
단순 데이터 입력은 처리 없이 저장

## 배포 방법

### 사전 준비
1. **AWS Secrets Manager에 `agent-core-secret` 생성**
2. **GitHub Secrets 설정:**
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`

### 자동 배포 ✅

```bash
git push origin main
```

**자동 실행 흐름:**
1. Docker 이미지 빌드
2. ECR에 푸시 (commit SHA 태그)
3. Agent Core Runtime 배포

**로컬에서 배포:**
```bash
export IMAGE_TAG=abc123def456
python deploy_from_ecr.py
```

### 로그 확인
```bash
# 실시간 로그
aws logs tail /aws/lambda/diary_orchestrator_agent --follow

# GitHub Actions
https://github.com/YOUR_USERNAME/YOUR_REPO/actions
```

## 기술 스택
- Runtime: AWS Lambda (Python 3.11)
- AI Framework: Strands Agents
- Model: AWS Bedrock (Claude Sonnet 4.5)
- Knowledge Base: AWS Bedrock Knowledge Base
- Container: Docker + Amazon ECR
- CI/CD: GitHub Actions
- Secrets: AWS Secrets Manager

## 프로젝트 구조
```
.
├── .github/workflows/
│   └── deploy-to-ecr.yml       # CI/CD: ECR 빌드 + Agent Core 배포
├── agent/
│   ├── utils/
│   │   └── secrets.py          # Secrets Manager 통합
│   ├── orchestrator/
│   │   ├── orchestra_agent.py  # 메인 오케스트레이터
│   │   ├── question/agent.py   # 질문 답변 Agent
│   │   └── summarize/agent.py  # 일기 생성 Agent
│   └── agentcore_agent.py      # Lambda 핸들러
├── Dockerfile
├── deploy_from_ecr.py          # 배포 스크립트
├── requirements.txt            # 로컬 개발용
└── requirements-lambda.txt     # Lambda 런타임용
```

## Secrets Manager 구조
```json
{
  "KNOWLEDGE_BASE_ID": "your-kb-id",
  "AWS_REGION": "us-east-1",
  "BEDROCK_MODEL_ARN": "arn:aws:bedrock:...",
  "IAM_ROLE_ARN": "arn:aws:iam::...:role/..."
}
```

## 라이선스
MIT License
