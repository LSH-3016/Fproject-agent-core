# Runtime 강제 재생성

## 문제
`update_agent_runtime`이 새 이미지를 제대로 적용하지 않음

## 해결책
매 배포마다 Runtime을 **삭제 후 재생성**

### 변경사항
```python
# deploy_from_ecr.py

if existing_runtime:
    # 1. 기존 Runtime 삭제
    client.delete_agent_runtime(agentRuntimeId=runtime_id)
    
    # 2. 10초 대기
    time.sleep(10)
    
    # 3. 새 Runtime 생성
    client.create_agent_runtime(...)
```

## 장점
- ✅ 항상 최신 이미지 사용 보장
- ✅ 캐시 문제 완전 해결
- ✅ 환경변수 변경도 확실히 반영

## 단점
- ⚠️ 배포 시간 약 10-20초 증가
- ⚠️ 배포 중 잠깐 서비스 중단 (10초)

## 대안 (나중에 고려)
- Blue-Green 배포
- 새 Runtime 생성 → 테스트 → 기존 Runtime 삭제

## 배포 명령
```bash
git add deploy_from_ecr.py
git commit -m "fix: Runtime 강제 재생성으로 이미지 업데이트 보장"
git push origin main
```

배포 후 확인:
```bash
# Runtime ARN이 변경되었는지 확인 (마지막 ID 부분이 달라짐)
aws bedrock-agentcore-control list-agent-runtimes --region us-east-1 \
  --query "agentRuntimes[?agentRuntimeName=='diary_orchestrator_agent']"
```
