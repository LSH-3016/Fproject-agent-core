# Agent Core 배포 최적화 가이드

## 현재 배포 시간이 오래 걸리는 이유

### 1. Docker 빌드 (가장 큰 병목)
- **ARM64 크로스 컴파일**: x86 머신에서 ARM64 이미지를 빌드하면 QEMU 에뮬레이션으로 인해 5-10배 느림
- **Python 패키지 설치**: psycopg2-binary, boto3 등 네이티브 확장 모듈 컴파일

### 2. ECR 푸시
- 이미지 크기에 따라 1-3분 소요

### 3. Agent Core Runtime 업데이트
- AWS가 새 이미지를 가져와서 컨테이너 시작: 2-5분

## 적용된 최적화

### ✅ 1. Docker 빌드 캐시 활성화
```yaml
--cache-from type=registry,ref=$ECR_REGISTRY/$ECR_REPOSITORY:buildcache
--cache-to type=registry,ref=$ECR_REGISTRY/$ECR_REPOSITORY:buildcache,mode=max
```
- **효과**: 코드만 변경 시 의존성 레이어 재사용 → 빌드 시간 50-70% 단축

### ✅ 2. Dockerfile 레이어 최적화
- requirements.txt를 먼저 복사하여 의존성 설치 레이어 캐싱
- 코드는 마지막에 복사하여 코드 변경 시에만 해당 레이어만 재빌드

### ✅ 3. 헬스체크 추가
- Agent Core가 컨테이너 준비 상태를 빠르게 감지

## 추가 최적화 방안 (선택사항)

### 🚀 옵션 1: GitHub Actions Self-Hosted Runner (ARM64)
**가장 효과적 - 빌드 시간 80% 단축**

AWS Graviton (ARM64) 인스턴스에 Self-Hosted Runner 설치:
```bash
# EC2 t4g.small (ARM64) 인스턴스 생성
# GitHub Actions Runner 설치
```

**장점**:
- 네이티브 ARM64 빌드 → QEMU 에뮬레이션 불필요
- 빌드 시간: 10분 → 2-3분

**단점**:
- EC2 인스턴스 비용 (월 $10-15)
- Runner 관리 필요

### 🚀 옵션 2: Multi-stage 빌드로 이미지 크기 축소
```dockerfile
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY agent/ /app/
ENV PATH=/root/.local/bin:$PATH
```

**효과**: 이미지 크기 20-30% 감소 → ECR 푸시 시간 단축

### 🚀 옵션 3: 변경 감지 기반 조건부 배포
```yaml
- name: Check if deployment needed
  id: check
  run: |
    if git diff HEAD^ HEAD --quiet -- agent/ Dockerfile requirements.txt; then
      echo "skip=true" >> $GITHUB_OUTPUT
    fi

- name: Deploy to Agent Core Runtime
  if: steps.check.outputs.skip != 'true'
  run: python deploy_from_ecr.py
```

**효과**: 코드 변경 없으면 배포 스킵

### 🚀 옵션 4: 병렬 빌드 (여러 agent 있을 경우)
현재는 단일 이미지지만, 향후 agent를 분리하면:
```yaml
strategy:
  matrix:
    agent: [image-generator, weekly-report, question]
```

## 예상 배포 시간

### 현재 (최적화 전)
- 전체: **12-15분**
  - Docker 빌드 (ARM64): 8-10분
  - ECR 푸시: 2-3분
  - Agent Core 배포: 2-3분

### 최적화 후 (캐시 활용)
- 전체: **6-8분** (코드만 변경 시)
  - Docker 빌드 (캐시 히트): 3-4분
  - ECR 푸시: 1-2분
  - Agent Core 배포: 2-3분

### Self-Hosted Runner 사용 시
- 전체: **4-5분**
  - Docker 빌드 (네이티브 ARM64): 1-2분
  - ECR 푸시: 1분
  - Agent Core 배포: 2-3분

## 권장 사항

1. **즉시 적용 가능**: ✅ 이미 적용됨 (캐시, Dockerfile 최적화)
2. **비용 대비 효과 최고**: Self-Hosted ARM64 Runner
3. **장기적**: Agent 분리 시 병렬 빌드 고려

## 모니터링

GitHub Actions 실행 시간을 확인하여 각 단계별 소요 시간 추적:
```
Actions → Workflow runs → 각 step 시간 확인
```
