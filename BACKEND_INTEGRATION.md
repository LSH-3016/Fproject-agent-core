# Agent Core Runtime 백엔드 연동 가이드

## ✅ 직접 호출 가능!

Agent Core Runtime은 boto3의 `bedrock-agentcore` 클라이언트를 사용하여 **Lambda 없이 직접 호출** 가능합니다.

---

## Agent Core Runtime 정보

**Agent Runtime ARN:**
```
arn:aws:bedrock-agentcore:us-east-1:324547056370:runtime/diary_orchestrator_agent-90S9ctAFht
```

**Agent Runtime ID:**
```
diary_orchestrator_agent-90S9ctAFht
```

**Status:** READY  
**Version:** 8  
**Region:** us-east-1  
**Network Mode:** PUBLIC

---

## 직접 호출 방법 (권장)

### ⚠️ 중요: boto3 버전 확인

```bash
pip install --upgrade boto3
pip show boto3  # 최신 버전 확인
```

`bedrock-agentcore` 클라이언트는 최신 boto3에서만 지원됩니다.

### 기본 사용법

```python
import boto3
import json
import uuid

# ✅ 올바른 클라이언트: 'bedrock-agentcore'
client = boto3.client('bedrock-agentcore', region_name='us-east-1')

# 요청 페이로드
payload = {
    "content": "오늘 뭐 먹었어?",
    "user_id": "user123",
    "record_date": "2026-01-18"
}

# Agent Runtime 호출
response = client.invoke_agent_runtime(
    agentRuntimeArn="arn:aws:bedrock-agentcore:us-east-1:324547056370:runtime/diary_orchestrator_agent-90S9ctAFht",
    runtimeSessionId=str(uuid.uuid4()),  # 매번 새로운 UUID
    payload=json.dumps(payload).encode('utf-8'),  # ⚠️ bytes로 인코딩 필수!
    qualifier="DEFAULT"
)

# 응답 처리
content = []
for chunk in response.get("response", []):
    content.append(chunk.decode('utf-8'))

result = json.loads(''.join(content))
print(result)
```

### 완전한 예제 (에러 처리 포함)

```python
import boto3
import json
import uuid

def call_agent(content: str, user_id: str, record_date: str):
    """Agent Core Runtime 호출"""
    
    client = boto3.client('bedrock-agentcore', region_name='us-east-1')
    
    payload = {
        "content": content,
        "user_id": user_id,
        "record_date": record_date
    }
    
    try:
        response = client.invoke_agent_runtime(
            agentRuntimeArn="arn:aws:bedrock-agentcore:us-east-1:324547056370:runtime/diary_orchestrator_agent-90S9ctAFht",
            runtimeSessionId=str(uuid.uuid4()),
            payload=json.dumps(payload).encode('utf-8'),
            qualifier="DEFAULT"
        )
        
        # 응답 수집
        content_parts = []
        response_body = response.get('response', [])
        
        # 다양한 응답 형식 처리
        if isinstance(response_body, bytes):
            content_parts.append(response_body.decode('utf-8'))
        elif hasattr(response_body, 'read'):
            content_parts.append(response_body.read().decode('utf-8'))
        else:
            for chunk in response_body:
                if isinstance(chunk, bytes):
                    content_parts.append(chunk.decode('utf-8'))
                elif isinstance(chunk, dict) and 'bytes' in chunk:
                    content_parts.append(chunk['bytes'].decode('utf-8'))
        
        # JSON 파싱
        full_response = ''.join(content_parts)
        return json.loads(full_response)
        
    except Exception as e:
        print(f"Error: {type(e).__name__} - {str(e)}")
        if hasattr(e, 'response'):
            print(f"Response: {e.response}")
        raise

# 사용
result = call_agent(
    content="오늘 뭐 먹었어?",
    user_id="user123",
    record_date="2026-01-18"
)
print(result)
```

### FastAPI 예제

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import boto3
import json
import uuid

app = FastAPI()

# Bedrock AgentCore 클라이언트
client = boto3.client('bedrock-agentcore', region_name='us-east-1')
AGENT_ARN = "arn:aws:bedrock-agentcore:us-east-1:324547056370:runtime/diary_orchestrator_agent-90S9ctAFht"

class AgentRequest(BaseModel):
    content: str
    user_id: str
    record_date: str

@app.post("/process")
async def process_request(request: AgentRequest):
    try:
        # Agent 호출
        response = client.invoke_agent_runtime(
            agentRuntimeArn=AGENT_ARN,
            runtimeSessionId=str(uuid.uuid4()),
            payload=json.dumps(request.dict()).encode('utf-8'),
            qualifier="DEFAULT"
        )
        
        # 응답 수집
        content = []
        for chunk in response.get("response", []):
            content.append(chunk.decode('utf-8'))
        
        result = json.loads(''.join(content))
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 요청/응답 형식

### 요청 예시

**질문:**
```json
{
  "content": "오늘 뭐 먹었어?",
  "user_id": "user123",
  "record_date": "2026-01-18"
}
```

**데이터 입력:**
```json
{
  "content": "오늘 점심에 맛있는 파스타를 먹었다",
  "user_id": "user123",
  "record_date": "2026-01-18"
}
```

**일기 생성:**
```json
{
  "content": "오늘 하루 일기 써줘",
  "user_id": "user123",
  "record_date": "2026-01-18",
  "request_type": "summarize"
}
```

### 응답 예시

**질문 답변:**
```json
{
  "type": "answer",
  "content": "오늘 점심에 파스타를 드셨습니다.",
  "message": "질문에 대한 답변입니다."
}
```

**데이터 저장:**
```json
{
  "type": "data",
  "content": "",
  "message": "메시지가 저장되었습니다."
}
```

**일기 생성:**
```json
{
  "type": "diary",
  "content": "오늘은 맛있는 파스타를 먹으며...",
  "message": "일기가 생성되었습니다."
}
```

---

## 필수 IAM 권한

백엔드 서비스의 IAM Role에 다음 권한이 필요합니다:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:InvokeAgentRuntime"
      ],
      "Resource": "arn:aws:bedrock-agentcore:us-east-1:324547056370:runtime/diary_orchestrator_agent-90S9ctAFht"
    }
  ]
}
```

---

## AWS CLI 테스트

```bash
# 페이로드 파일 생성
echo '{"content":"오늘 뭐 먹었어?","user_id":"user123","record_date":"2026-01-18"}' > payload.json

# Agent 호출
aws bedrock-agentcore invoke-agent-runtime \
  --agent-runtime-arn "arn:aws:bedrock-agentcore:us-east-1:324547056370:runtime/diary_orchestrator_agent-90S9ctAFht" \
  --runtime-session-id $(uuidgen) \
  --payload file://payload.json \
  --qualifier DEFAULT \
  --region us-east-1 \
  output.json

# 결과 확인
cat output.json
```

---

## 요청 형식

### 질문 (Question)
```json
{
  "content": "오늘 뭐 먹었어?",
  "user_id": "user123",
  "record_date": "2026-01-18"
}
```

### 데이터 입력 (Data)
```json
{
  "content": "오늘 점심에 맛있는 파스타를 먹었다",
  "user_id": "user123",
  "record_date": "2026-01-18"
}
```

### 일기 생성 (Diary)
```json
{
  "content": "오늘 하루 일기 써줘",
  "user_id": "user123",
  "record_date": "2026-01-18",
  "request_type": "summarize"
}
```

---

## 응답 형식

### 질문 답변
```json
{
  "statusCode": 200,
  "body": {
    "type": "answer",
    "content": "오늘 점심에 파스타를 드셨습니다.",
    "message": "질문에 대한 답변입니다."
  }
}
```

### 데이터 저장
```json
{
  "statusCode": 200,
  "body": {
    "type": "data",
    "content": "",
    "message": "메시지가 저장되었습니다."
  }
}
```

### 일기 생성
```json
{
  "statusCode": 200,
  "body": {
    "type": "diary",
    "content": "오늘은 맛있는 파스타를 먹으며...",
    "message": "일기가 생성되었습니다."
  }
}
```

---

## 필수 IAM 권한

백엔드 서비스의 IAM Role에 다음 권한이 필요합니다:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore-runtime:InvokeAgentRuntime"
      ],
      "Resource": "arn:aws:bedrock-agentcore:us-east-1:324547056370:runtime/diary_orchestrator_agent-90S9ctAFht"
    }
  ]
}
```

---

## 로그 확인

CloudWatch Logs에서 다음 로그 그룹을 확인하세요:

```
/aws/bedrock-agentcore/runtimes/diary_orchestrator_agent-90S9ctAFht-DEFAULT
```

---

## 문제 해결

### 1. 로그가 비어있는 경우
- Agent Runtime이 호출되지 않고 있습니다
- 백엔드에서 올바른 ARN으로 호출하는지 확인하세요
- IAM 권한을 확인하세요

### 2. Knowledge Base 접근 실패
- Agent Runtime의 IAM Role에 Bedrock Knowledge Base 권한이 있는지 확인
- 환경변수 `KNOWLEDGE_BASE_ID`가 올바르게 설정되었는지 확인

### 3. 타임아웃
- Agent Core Runtime은 최대 30초까지 실행됩니다
- 복잡한 요청은 시간이 걸릴 수 있습니다

---

## 테스트 스크립트

`test_agent_invoke.py` 파일을 사용하여 로컬에서 테스트할 수 있습니다:

```bash
python test_agent_invoke.py
```
