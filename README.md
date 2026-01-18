# Diary Orchestrator Agent

AWS Bedrock Agent Core Runtime을 사용한 일기 관리 AI Agent 시스템

## 프로젝트 구조

```
.
├── .github/
│   └── workflows/
│       └── deploy-to-ecr.yml      # GitHub Actions CI/CD 워크플로우
├── agent/
│   ├── agentcore_agent.py         # Lambda 핸들러 (Entrypoint)
│   └── orchestrator/
│       ├── orchestra_agent.py     # 메인 오케스트레이터
│       ├── question/
│       │   └── agent.py          # 질문 답변 Agent
│       └── summerize/
│           └── agent.py          # 일기 생성 Agent
├── .dockerignore                  # Docker 빌드 제외 파일
├── .gitignore                     # Git 제외 파일
├── Dockerfile                     # Lambda 런타임 이미지
├── deploy_from_ecr.py            # ECR 이미지로 배포
├── requirements.txt               # Python 의존성
├── CICD_DEPLOYMENT_GUIDE.md      # CI/CD 배포 가이드
└── README.md                      # 이 파일
```

## 주요 기능

### 1. 질문 답변 (Question Agent)
- Knowledge Base를 검색하여 사용자 질문에 답변
- user_id 기반 개인화된 검색
- 예시: "2026-01-13일에 나 무슨 영화봤어?"

### 2. 일기 생성 (Summarize Agent)
- 사용자 데이터를 분석하여 일기 형식으로 작성
- 자연스러운 한국어 일기 생성
- 예시: "오늘 영화 보고 파스타 먹었어" → 일기 형식 변환

### 3. 데이터 그대로 반환 (No Processing)
- 단순 데이터 입력은 처리 없이 저장
- 예시: "오늘 영화 봤어" → 그대로 반환

## 배포 방법

### CI/CD 배포 (권장)

자세한 내용은 [CICD_DEPLOYMENT_GUIDE.md](CICD_DEPLOYMENT_GUIDE.md) 참조

1. GitHub Secrets 설정
2. 코드 푸시 → 자동 빌드 & ECR 배포
3. `deploy_from_ecr.py` 실행

### 로컬 테스트

```bash
# 가상환경 활성화
venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 로컬 테스트
python agent/agentcore_agent.py
```

## 기술 스택

- **Runtime**: AWS Lambda (Python 3.11)
- **AI Framework**: Strands Agents
- **Model**: AWS Bedrock (Claude Sonnet 4.5)
- **Knowledge Base**: AWS Bedrock Knowledge Base
- **Container**: Docker + Amazon ECR
- **CI/CD**: GitHub Actions

## 환경 변수

```python
KNOWLEDGE_BASE_ID = 'LOCNRTBMNB'
AWS_REGION = 'us-east-1'
```

## 라이선스

MIT License
