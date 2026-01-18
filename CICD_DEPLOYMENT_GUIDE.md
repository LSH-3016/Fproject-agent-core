# CI/CD 배포 가이드 (GitHub Actions + ECR)

이 가이드는 GitHub Actions를 사용하여 ECR에 이미지를 배포하고, Agent Core Runtime에서 사용하는 방법을 설명합니다.

## 아키텍처

```
GitHub Repository
    ↓ (push to main/develop)
GitHub Actions
    ↓ (build & push)
Amazon ECR
    ↓ (pull image)
Agent Core Runtime
```

## 사전 준비사항

### 1. AWS IAM 설정

#### GitHub Actions용 IAM User 생성
필요한 권한:
- ECR 접근 (이미지 push)
- Agent Core 배포 권한

#### Agent Runtime용 IAM Role 생성
필요한 권한:
- Bedrock 모델 호출
- Knowledge Base 접근
- CloudWatch Logs
- ECR 이미지 pull

### 2. GitHub Secrets 설정

Repository Settings > Secrets and variables > Actions에서 추가:

```
AWS_ACCESS_KEY_ID: GitHub Actions용 IAM User의 Access Key
AWS_SECRET_ACCESS_KEY: GitHub Actions용 IAM User의 Secret Key
```

## 배포 순서

### Step 1: 코드 작성 및 커밋
```bash
git add .
git commit -m "Update agent code"
git push origin main
```

### Step 2: GitHub Actions 자동 실행
- Push하면 자동으로 GitHub Actions 워크플로우가 실행됩니다
- Actions 탭에서 진행 상황을 확인할 수 있습니다

### Step 3: ECR 이미지 확인
```bash
# ECR 이미지 목록 확인
aws ecr describe-images --repository-name diary-orchestrator-agent
```


### Step 4: Agent Core에 배포
```bash
# IAM Role ARN 설정 후 실행
python deploy_from_ecr.py
```

## 파일 설명

### 1. Dockerfile
Lambda 런타임 기반 Docker 이미지 정의
- Python 3.11 Lambda 베이스 이미지 사용
- 의존성 설치
- 애플리케이션 코드 복사

### 2. .github/workflows/deploy-to-ecr.yml
GitHub Actions 워크플로우
- main/develop 브랜치에 push 시 자동 실행
- Docker 이미지 빌드 및 ECR에 푸시
- latest 태그와 commit SHA 태그 생성

### 3. deploy_from_ecr.py
ECR 이미지를 사용한 Agent Core 배포 스크립트
- ECR에서 이미지를 가져와 Agent Core에 배포

### 4. .dockerignore
Docker 빌드 시 제외할 파일 목록

## 로컬 테스트

### Docker 이미지 로컬 빌드
```bash
docker build -t diary-orchestrator-agent:local .
```

### 로컬에서 실행
```bash
docker run -p 9000:8080 diary-orchestrator-agent:local
```

### 테스트 요청
```bash
curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" \
  -d '{"user_input": "오늘 영화 봤어"}'
```

## 환경별 배포

### Development 환경
```bash
# develop 브랜치에 push
git push origin develop
```

### Production 환경
```bash
# main 브랜치에 push
git push origin main
```


## 고급 설정

### 1. 환경별 이미지 태그 관리

`.github/workflows/deploy-to-ecr.yml` 수정:
```yaml
env:
  IMAGE_TAG: ${{ github.ref_name }}-${{ github.sha }}
```

### 2. 자동 배포 추가

GitHub Actions에 Agent Core 배포 단계 추가:
```yaml
- name: Deploy to Agent Core
  run: |
    python deploy_from_ecr.py
  env:
    EXECUTION_ROLE: ${{ secrets.AGENT_EXECUTION_ROLE }}
```

### 3. 멀티 스테이지 빌드

Dockerfile 최적화:
```dockerfile
FROM public.ecr.aws/lambda/python:3.11 as builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --target /build -r requirements.txt

FROM public.ecr.aws/lambda/python:3.11
COPY --from=builder /build ${LAMBDA_TASK_ROOT}
COPY agent/ ${LAMBDA_TASK_ROOT}/agent/
CMD ["agent.agentcore_agent.lambda_handler"]
```

## 트러블슈팅

### ECR 로그인 실패
```bash
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  <account-id>.dkr.ecr.us-east-1.amazonaws.com
```

### 이미지 빌드 실패
- Dockerfile 문법 확인
- requirements.txt 의존성 확인
- .dockerignore 설정 확인

### Agent Core 배포 실패
- IAM Role ARN 확인
- ECR 이미지 URI 확인
- 실행 권한 확인

## 비용 최적화

1. **ECR 이미지 정리**: 오래된 이미지 자동 삭제
2. **캐시 활용**: Docker 레이어 캐싱
3. **이미지 크기 최적화**: 불필요한 파일 제외

## 모니터링

### CloudWatch Logs
```bash
aws logs tail /aws/lambda/diary_orchestrator_agent --follow
```

### ECR 이미지 스캔
```bash
aws ecr start-image-scan \
  --repository-name diary-orchestrator-agent \
  --image-id imageTag=latest
```
