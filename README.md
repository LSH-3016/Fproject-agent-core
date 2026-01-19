# Diary Orchestrator Agent

AWS Bedrock Agent Core Runtime을 사용한 일기 관리 AI Agent 시스템

## 주요 기능

### 1. 질문 답변 (Question Agent)
Knowledge Base를 검색하여 사용자 질문에 답변
- 예: "2026-01-13일에 나 무슨 영화봤어?"

### 2. 일기 생성 (Summarize Agent)
사용자 데이터를 분석하여 일기 형식으로 작성
- 예: "오늘 영화 보고 파스타 먹었어" → 일기 형식 변환

### 3. 이미지 생성 (Image Generator Agent)
일기 텍스트를 분석하여 이미지 생성
- Claude Sonnet 4.5로 프롬프트 변환
- Amazon Nova Canvas로 4:5 비율 이미지 생성
- S3 자동 업로드 및 URL 제공
- 미리보기, 배치 생성 등 다양한 기능

### 4. 주간 리포트 (Weekly Report Agent)
일정 기간의 일기를 분석하여 주간 리포트 생성
- 감정 점수 분석 (1-10점)
- 주요 테마 추출
- 개인화된 피드백 제공

### 5. 데이터 그대로 반환 (No Processing)
단순 데이터 입력은 처리 없이 저장

## 아키텍처

```
orchestrator_agent (4개 tool)
├── generate_auto_summarize (일기 생성)
├── generate_auto_response (질문 답변)
├── run_image_generator (이미지 생성)
│   └── image_generator_agent (9개 tool)
│       ├── generate_image_for_history
│       ├── preview_image
│       ├── batch_generate_images
│       └── ...
└── run_weekly_report (주간 리포트)
    └── weekly_report_agent (6개 tool)
        ├── create_report
        ├── get_report_list
        └── ...
```

**특징:**
- 계층적 구조: Orchestrator → Sub-Agent → Specific Tool
- 자연어 분석으로 자동 라우팅
- 각 도메인의 복잡성을 내부에 캡슐화

## API 사용법

### 통합된 요청 형식
모든 요청은 동일한 형식으로 전송하고, orchestrator가 자동으로 적절한 에이전트를 선택합니다.

```json
{
  "content": "사용자 요청 (자연어)",
  "user_id": "user123",
  "current_date": "2026-01-19"
}
```

### 요청 예시

**일기 생성:**
```json
{
  "content": "오늘 하루 일기 써줘",
  "user_id": "user123",
  "current_date": "2026-01-19"
}
```

**질문 답변:**
```json
{
  "content": "오늘 뭐 먹었어?",
  "user_id": "user123",
  "current_date": "2026-01-19"
}
```

**이미지 생성:**
```json
{
  "content": "히스토리 123번 이미지 만들어줘",
  "user_id": "user123"
}
```

**주간 리포트:**
```json
{
  "content": "이번 주 리포트 생성해줘",
  "user_id": "user123",
  "start_date": "2026-01-13",
  "end_date": "2026-01-19"
}
```

**데이터 저장:**
```json
{
  "content": "오늘 영화 봤어",
  "user_id": "user123",
  "current_date": "2026-01-19"
}
```

### 응답 형식

```json
{
  "type": "diary|answer|image|report|data",
  "content": "생성된 내용",
  "message": "응답 메시지"
}
```

## 백엔드 연동

### boto3로 직접 호출 (권장)

```python
import boto3
import json
import uuid

client = boto3.client('bedrock-agentcore', region_name='us-east-1')

payload = {
    "content": "오늘 뭐 먹었어?",
    "user_id": "user123",
    "current_date": "2026-01-19"
}

response = client.invoke_agent_runtime(
    agentRuntimeArn="arn:aws:bedrock-agentcore:us-east-1:324547056370:runtime/diary_orchestrator_agent-90S9ctAFht",
    runtimeSessionId=str(uuid.uuid4()),
    payload=json.dumps(payload).encode('utf-8'),
    qualifier="DEFAULT"
)

# 응답 처리
content = []
for chunk in response.get("response", []):
    content.append(chunk.decode('utf-8'))

result = json.loads(''.join(content))
```

### 필수 IAM 권한

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["bedrock-agentcore:InvokeAgentRuntime"],
      "Resource": "arn:aws:bedrock-agentcore:us-east-1:324547056370:runtime/diary_orchestrator_agent-90S9ctAFht"
    }
  ]
}
```

## 배포 방법

### 자동 배포 (GitHub Actions)

```bash
git push origin main
```

**자동 실행 흐름:**
1. Docker 이미지 빌드
2. ECR에 푸시 (commit SHA 태그)
3. Agent Core Runtime 배포

### 로컬에서 배포

```bash
export IMAGE_TAG=abc123def456
python deploy_from_ecr.py
```

### 로그 확인

```bash
# Agent Core Runtime 로그
aws logs tail /aws/bedrock-agentcore/runtimes/diary_orchestrator_agent-90S9ctAFht-DEFAULT --follow

# GitHub Actions
https://github.com/YOUR_USERNAME/YOUR_REPO/actions
```

## 환경 설정

### Secrets Manager 구조
```json
{
  "KNOWLEDGE_BASE_ID": "your-kb-id",
  "KNOWLEDGE_BASE_BUCKET": "your-s3-bucket",
  "AWS_REGION": "us-east-1",
  "BEDROCK_MODEL_ARN": "arn:aws:bedrock:...",
  "BEDROCK_MODEL_ID": "amazon.nova-canvas-v1:0",
  "BEDROCK_LLM_MODEL_ID": "us.anthropic.claude-sonnet-4-20250514-v1:0",
  "IAM_ROLE_ARN": "arn:aws:iam::...:role/...",
  "DB_HOST": "your-rds-endpoint",
  "DB_PORT": "5432",
  "DB_NAME": "postgres",
  "DB_USER": "postgres",
  "DB_PASSWORD": "your-password",
  "API_BASE_URL": "https://api.aws11.shop"
}
```

## 기술 스택

- **Runtime**: AWS Agent Core Runtime (Docker 컨테이너)
- **AI Framework**: Strands Agents
- **Models**: 
  - AWS Bedrock Claude Sonnet 4.5 (텍스트 생성)
  - Amazon Nova Canvas (이미지 생성)
- **Knowledge Base**: AWS Bedrock Knowledge Base
- **Database**: PostgreSQL (RDS)
- **Storage**: Amazon S3
- **Container**: Docker + Amazon ECR
- **CI/CD**: GitHub Actions
- **Secrets**: AWS Secrets Manager

## 프로젝트 구조

```
.
├── .github/workflows/
│   └── deploy-to-ecr.yml           # CI/CD: ECR 빌드 + Agent Core 배포
├── agent/
│   ├── utils/
│   │   └── secrets.py              # Secrets Manager 통합
│   ├── orchestrator/
│   │   ├── orchestra_agent.py      # 메인 오케스트레이터 (4개 tool)
│   │   ├── question/               # 질문 답변 Agent
│   │   │   └── agent.py
│   │   ├── summarize/              # 일기 생성 Agent
│   │   │   └── agent.py
│   │   ├── image_generator/        # 이미지 생성 Agent (9개 tool)
│   │   │   ├── agent.py
│   │   │   ├── tools.py
│   │   │   └── prompts.py
│   │   └── weekly_report/          # 주간 리포트 Agent (6개 tool)
│   │       ├── agent.py
│   │       ├── tools.py
│   │       └── prompts.py
│   └── server.py                   # FastAPI 서버 (단일 진입점)
├── Dockerfile
├── deploy_from_ecr.py              # 배포 스크립트
└── requirements.txt                # 의존성 (로컬 개발 + Docker)
```

## 로컬 개발

### 서버 실행
```bash
python agent/server.py
```

### 테스트
```bash
# 헬스체크
curl http://localhost:8080/ping

# 일기 생성
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"content":"오늘 하루 일기 써줘","user_id":"user123"}'
```

## 라이선스
MIT License
