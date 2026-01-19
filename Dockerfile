# Dockerfile for Agent Core Runtime
# Agent Core Runtime은 HTTP 서버가 필요함 (/ping, /invocations 엔드포인트)
FROM public.ecr.aws/docker/library/python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 (최소화)
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# pip 업그레이드
RUN pip install --upgrade pip

# requirements 복사 및 의존성 설치 (캐시 활용)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사 (마지막에 복사하여 캐시 활용)
COPY agent/ /app/

# 포트 8080 노출 (Agent Core Runtime 필수)
EXPOSE 8080

# 헬스체크 추가
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8080/ping')" || exit 1

# FastAPI 서버 실행
CMD ["python", "server.py"]
