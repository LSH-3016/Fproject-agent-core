import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field
from strands import Agent

from .summerize.agent import generate_auto_summerize
from .question.agent import generate_auto_response

# Secrets Manager에서 설정 가져오기
try:
    from ..utils.secrets import get_config
    config = get_config()
    BEDROCK_MODEL_ARN = config.get('BEDROCK_MODEL_ARN', '')
except Exception as e:
    print(f"⚠️  설정을 가져올 수 없습니다: {str(e)}")
    # 환경변수 또는 기본값 사용
    BEDROCK_MODEL_ARN = os.environ.get('BEDROCK_MODEL_ARN', '<your-bedrock-model-arn>')

# Configure the root strands logger
logging.getLogger("strands").setLevel(logging.INFO)

# Add a handler to see the logs
logging.basicConfig(
    format="%(levelname)s | %(name)s | %(message)s", handlers=[logging.StreamHandler()]
)

ORCHESTRATOR_PROMPT = """
당신은 AI의 워크플로우를 관리하는 오케스트레이터입니다.
사용자가 입력하는 데이터를 기반으로 다음 중 가장 적절한 처리 방법을 선택해주세요.

<처리 방법>
1. generate_auto_summerize: 사용자의 데이터를 분석하여 일기 생성
   - 사용 조건: 일기 작성, 일기 생성, 요약 생성 등의 요청
   
2. generate_auto_response: 사용자의 질문에 답변을 생성
   - 사용 조건: 질문, 조회, 검색, "~했어?", "~뭐야?" 등의 질문 형태
   - 필수 파라미터: question (질문 내용 전체를 문자열로 전달)
   - 반환 형식: {"response": "답변내용"} 형태의 딕셔너리

3. 데이터 그대로 반환 (no_processing)
   - 사용 조건: 단순 데이터 입력, 저장 요청, 특별한 처리가 필요 없는 경우
   - 예시: "오늘 영화 봤어", "점심에 파스타 먹었어", "운동 30분 했어"
   - 이 경우 tool을 사용하지 않고 입력 데이터를 그대로 반환합니다
</처리 방법>

<작업순서>
1. 사용자의 요청 유형을 판단합니다:
   - 질문 형태인가? (질문, 조회, "~했어?", "~뭐야?") → generate_auto_response
   - 일기 생성 요청인가? (일기 작성, 요약 생성) → generate_auto_summerize
   - 단순 데이터 입력인가? (사실 진술, 활동 기록) → no_processing

2. 질문이면 generate_auto_response tool을 호출합니다
   - user_input 전체를 question 파라미터로 전달

3. 일기 생성이면 generate_auto_summerize tool을 호출합니다

4. 단순 데이터 입력이면 tool을 사용하지 않고 입력 데이터를 그대로 반환합니다

5. tool 결과 처리:
   - tool 결과가 딕셔너리 형태면 "response" 키의 값을 추출
   - no_processing인 경우 입력 데이터를 그대로 사용
</작업순서>

<필수규칙>
- 질문이나 일기 생성 요청은 반드시 해당 tool을 사용해야 합니다
- 단순 데이터 입력은 tool을 사용하지 않고 그대로 반환합니다
- tool 결과를 수정하거나 추가 설명을 붙이지 마세요
</필수규칙>

"""


class OrchestratorResult(BaseModel):
    """Orchestrator result."""

    request_type: str = Field(description="요청 타입: summerize, question, 또는 no_processing")
    result: str = Field(description="생성된 결과")


def orchestrate_request(
    user_input: str,
    request_type: Optional[str] = None,
    temperature: Optional[float] = None,
) -> Dict[str, Any]:
    """
    사용자 요청을 분석하여 적절한 agent로 라우팅하는 메인 함수

    Args:
        user_input (str): 사용자 입력 데이터
        request_type (Optional[str]): 요청 타입 ('summerize' 또는 'question'). 
                                       None이면 orchestrator가 자동 판단
        temperature (Optional[float]): summerize agent용 temperature 파라미터 (0.0 ~ 1.0)

    Returns:
        Dict[str, Any]: 처리 결과
    """

    # 각 요청마다 새로운 Agent 생성
    orchestrator_agent = Agent(
        model=BEDROCK_MODEL_ARN,
        tools=[
            generate_auto_summerize,
            generate_auto_response,
        ],
        system_prompt=ORCHESTRATOR_PROMPT,
    )

    # orchestrator에게 요청 처리
    prompt = f"""
    <user_input>{user_input}</user_input>
    <request_type>{request_type if request_type else '자동 판단'}</request_type>
    """
    
    # summerize 요청인 경우 temperature 정보 추가
    if request_type == "summerize" or request_type is None:
        if temperature is not None:
            prompt += f"\n<temperature>{temperature}</temperature>"
    
    orchestrator_agent(prompt)

    result = orchestrator_agent.structured_output(
        OrchestratorResult, "사용자 요청에 대한 처리 결과를 구조화된 형태로 추출하시오"
    )

    # Pydantic 모델을 dict로 변환
    if hasattr(result, "model_dump"):
        result_dict = result.model_dump()
    elif hasattr(result, "dict"):
        result_dict = result.dict()
    else:
        result_dict = result

    return result_dict
