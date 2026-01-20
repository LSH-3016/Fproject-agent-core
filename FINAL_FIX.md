# 최종 수정 - Runtime 이미지 업데이트 문제 해결

## 문제 진단
1. ✅ ECR에 최신 이미지 푸시됨
2. ✅ deploy_from_ecr.py 실행됨
3. ❌ Runtime이 최신 이미지를 사용하지 않음

**원인**: 
- GitHub Actions가 commit SHA를 IMAGE_TAG로 전달
- 하지만 Runtime은 이미지 digest로 변경을 감지
- `latest` 태그가 업데이트되어도 Runtime이 자동으로 pull하지 않음

## 해결 방법

### deploy_from_ecr.py 수정
```python
# 항상 latest 태그 사용
IMAGE_TAG = 'latest'
```

이렇게 하면:
1. 매번 같은 태그(`latest`)로 업데이트 시도
2. Agent Core Runtime이 이미지 digest 변경을 감지
3. 새 이미지를 자동으로 pull

## 추가 개선사항

### 1. agent/server.py
- 모든 로그에 `flush=True` 추가
- 에러를 stderr로 출력
- 상세한 디버그 로깅

### 2. agent/utils/secrets.py  
- 여러 Secret 이름 시도
- 누락된 키 자동 보완
- Model ID 정규화

### 3. agent/orchestrator/orchestra_agent.py
- 유연한 Model ID 로딩
- 최후의 fallback

### 4. .github/workflows/deploy-to-ecr.yml
- Docker 빌드 캐시 비활성화 (`--no-cache`)

## 배포 후 확인
```bash
# Runtime 버전 확인
aws bedrock-agentcore-control list-agent-runtimes --region us-east-1 \
  --query "agentRuntimes[?agentRuntimeName=='diary_orchestrator_agent']"

# 사용 중인 이미지 확인
aws bedrock-agentcore-control get-agent-runtime --region us-east-1 \
  --agent-runtime-id diary_orchestrator_agent-90S9ctAFht \
  --query "agentRuntime.agentRuntimeArtifact.containerConfiguration.containerUri"

# 최신 ECR 이미지 확인
aws ecr describe-images --repository-name diary-orchestrator-agent \
  --region us-east-1 --image-ids imageTag=latest
```

## 다음 단계
1. 커밋 & 푸시
2. GitHub Actions 완료 대기 (5-10분)
3. Runtime 버전 증가 확인
4. 테스트 요청 전송
5. CloudWatch 로그 확인
