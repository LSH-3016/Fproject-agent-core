# 배포 노트 - 500 에러 수정

## 문제
Agent Core Runtime에서 500 에러 발생:
```
RuntimeClientError: Received error (500) from runtime
```

## 원인 분석
1. Secret 이름 불일치 가능성
2. 누락된 설정 키들
3. Model ID 형식 문제

## 수정 사항

### 1. agent/utils/secrets.py
- **여러 Secret 이름 시도**: 
  - `agent-core-secret` (us-east-1, 우선)
  - `one-agent-core-secret` (ap-northeast-2, fallback)
  - 환경변수 `SECRET_NAME` (최우선)

- **누락된 키 자동 보완**:
  - `BEDROCK_CLAUDE_MODEL_ID`: `BEDROCK_MODEL_ARN`에서 복사 또는 기본값
  - `BEDROCK_LLM_MODEL_ID`: 기본값 `anthropic.claude-sonnet-4-20250514-v1:0`
  - `BEDROCK_NOVA_CANVAS_MODEL_ID`: 기본값 `amazon.nova-canvas-v1:0`
  - `KNOWLEDGE_BASE_BUCKET`: 환경변수에서 가져옴

- **Model ID 정규화 강화**:
  - `BEDROCK_MODEL_ARN`도 정규화 대상에 추가
  - ARN 형식 → model ID 추출
  - `us.` 접두사 자동 제거

### 2. agent/orchestrator/orchestra_agent.py
- **유연한 Model ID 로딩**:
  ```python
  BEDROCK_MODEL_ARN = (
      config.get('BEDROCK_MODEL_ARN') or 
      config.get('BEDROCK_CLAUDE_MODEL_ID') or 
      os.environ.get('BEDROCK_MODEL_ARN', '')
  )
  ```

- **최후의 fallback**: 모든 방법 실패 시 기본 모델 ID 사용
- **상세한 에러 로깅**: traceback 출력으로 디버깅 용이

## 검증된 Secret 값 (us-east-1)
```json
{
  "KNOWLEDGE_BASE_ID": "LOCNRTBMNB",
  "KNOWLEDGE_BASE_BUCKET": "knowledge-base-test-6575574",
  "AWS_REGION": "us-east-1",
  "BEDROCK_MODEL_ARN": "arn:aws:bedrock:us-east-1:324547056370:inference-profile/global.anthropic.claude-sonnet-4-5-20250929-v1:0",
  "IAM_ROLE_ARN": "arn:aws:iam::324547056370:role/DiaryOrchestratorAgentRole",
  "BEDROCK_CLAUDE_MODEL_ID": "anthropic.claude-sonnet-4-5-20250929-v1:0",
  "BEDROCK_NOVA_CANVAS_MODEL_ID": "amazon.nova-canvas-v1:0",
  "BEDROCK_LLM_MODEL_ID": "anthropic.claude-sonnet-4-20250514-v1:0"
}
```

## 배포 후 확인 사항
1. Agent Core Runtime 로그 확인
2. Secret 로딩 성공 여부 확인
3. Model ID 정규화 로그 확인
4. 실제 요청 테스트

## 배포 명령
```bash
git add agent/utils/secrets.py agent/orchestrator/orchestra_agent.py
git commit -m "fix: Agent Core Runtime 500 에러 수정 - Secret 로딩 및 Model ID 처리 개선"
git push origin main
```

배포는 GitHub Actions가 자동으로 수행합니다.
