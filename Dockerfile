# Dockerfile for Agent Core Runtime
FROM public.ecr.aws/lambda/python:3.11

# 작업 디렉토리 설정
WORKDIR ${LAMBDA_TASK_ROOT}

# requirements.txt 복사 및 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY agent/ ${LAMBDA_TASK_ROOT}/agent/

# Lambda 핸들러 설정
CMD ["agent.agentcore_agent.lambda_handler"]
