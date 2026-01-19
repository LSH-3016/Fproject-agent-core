import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field
from strands import Agent

from .summarize.agent import generate_auto_summarize
from .question.agent import generate_auto_response
from .image_generator.agent import run_image_generator
from .weekly_report.agent import run_weekly_report

# Secrets Manager에서 설정 가져오기
try:
    from ..utils.secrets import get_config
    config = get_config()
    BEDROCK_MODEL_ARN = config.get('BEDROCK_MODEL_ARN', '')
    if not BEDROCK_MODEL_ARN:
        # 환경변수에서 시도
        BEDROCK_MODEL_ARN = os.environ.get('BEDROCK_MODEL_ARN', '')
    if not BEDROCK_MODEL_ARN:
        raise ValueError("BEDROCK_MODEL_ARN이 설정되지 않았습니다.")
except Exception as e:
    print(f"⚠️  설정을 가져올 수 없습니다: {str(e)}")
    # 환경변수에서 시도
    BEDROCK_MODEL_ARN = os.environ.get('BEDROCK_MODEL_ARN', '')
    if not BEDROCK_MODEL_ARN:
        raise ValueError("BEDROCK_MODEL_ARN이 설정되지 않았습니다. Secrets Manager 또는 환경변수를 확인하세요.")

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
1. generate_auto_summarize: 사용자의 데이터를 분석하여 일기 생성
   - 사용 조건: 일기 작성, 일기 생성, 요약 생성 등의 요청
   - 응답 형식: {"type": "diary", "content": "생성된 일기 내용", "message": "일기가 생성되었습니다."}
   
2. generate_auto_response: 사용자의 질문에 답변을 생성
   - 사용 조건: 질문, 조회, 검색, "~했어?", "~뭐야?" 등의 질문 형태
   - **반드시 전달해야 할 파라미터:**
     * question: 질문 내용 전체를 문자열로 전달
     * user_id: 사용자 ID (제공된 경우 반드시 전달)
     * current_date: 현재 날짜 (제공된 경우 반드시 전달)
   - 응답 형식: {"type": "answer", "content": "답변 내용", "message": "질문에 대한 답변입니다."}

3. run_image_generator: 이미지 생성 관련 모든 작업 처리
   - 사용 조건: "이미지 생성", "사진 만들어줘", "미리보기", "배치 생성" 등
   - **반드시 전달해야 할 파라미터:**
     * request: 사용자 요청 (자연어)
     * history_id: 히스토리 ID (제공된 경우)
     * text: 일기 텍스트 (제공된 경우)
   - 응답 형식: {"type": "image", "content": "이미지 생성 결과", "message": "이미지가 생성되었습니다."}
   - 내부에서 자동으로 적절한 작업 선택 (생성, 미리보기, 배치 등)

4. run_weekly_report: 주간 리포트 관련 모든 작업 처리
   - 사용 조건: "주간 리포트", "이번 주 요약", "리포트 목록", "리포트 조회" 등
   - **반드시 전달해야 할 파라미터:**
     * request: 사용자 요청 (자연어)
     * user_id: 사용자 ID (제공된 경우)
     * start_date: 시작일 (제공된 경우)
     * end_date: 종료일 (제공된 경우)
     * report_id: 리포트 ID (제공된 경우)
   - 응답 형식: {"type": "report", "content": "리포트 내용", "message": "리포트가 생성되었습니다."}
   - 내부에서 자동으로 적절한 작업 선택 (생성, 목록, 조회 등)

5. 데이터 그대로 반환 (no_processing)
   - 사용 조건: 단순 데이터 입력, 저장 요청, 특별한 처리가 필요 없는 경우
   - 예시: "오늘 영화 봤어", "점심에 파스타 먹었어", "운동 30분 했어"
   - 응답 형식: {"type": "data", "content": "", "message": "메시지가 저장되었습니다."}
   - 이 경우 tool을 사용하지 않고 입력 데이터를 그대로 반환합니다
</처리 방법>

<작업순서>
1. 사용자의 요청 유형을 판단합니다:
   - 질문 형태인가? → generate_auto_response → type: "answer"
   - 일기 생성 요청인가? → generate_auto_summarize → type: "diary"
   - 이미지 관련 요청인가? → run_image_generator → type: "image"
   - 주간 리포트 요청인가? → run_weekly_report → type: "report"
   - 단순 데이터 입력인가? → no_processing → type: "data"

2. 질문이면 generate_auto_response tool을 호출합니다
   - question 파라미터: user_input 전체를 전달
   - user_id, current_date: 제공된 경우 반드시 전달

3. 일기 생성이면 generate_auto_summarize tool을 호출합니다

4. 이미지 요청이면 run_image_generator tool을 호출합니다
   - request 파라미터: user_input 전체를 전달
   - history_id, text: 제공된 경우 전달
   - 내부 Agent가 자동으로 적절한 작업 선택

5. 리포트 요청이면 run_weekly_report tool을 호출합니다
   - request 파라미터: user_input 전체를 전달
   - user_id, start_date, end_date, report_id: 제공된 경우 전달
   - 내부 Agent가 자동으로 적절한 작업 선택

6. 단순 데이터 입력이면 tool을 사용하지 않습니다
   - type: "data", content: "", message: "메시지가 저장되었습니다."

7. tool 결과 처리:
   - tool 결과를 적절히 content에 담습니다
   - no_processing인 경우 content는 빈 문자열("")입니다
</작업순서>

<응답 형식>
반드시 다음 형식으로 응답하세요:
- type: "data", "answer", "diary", "image", "report" 중 하나
- content: 생성된 내용 (data인 경우 빈 문자열)
- message: 적절한 응답 메시지
</응답 형식>

<필수규칙>
- 질문이나 일기 생성 요청은 반드시 해당 tool을 사용해야 합니다
- generate_auto_response 호출 시 user_id와 current_date가 제공되면 반드시 함께 전달해야 합니다
- 단순 데이터 입력은 tool을 사용하지 않고 type: "data"로 반환합니다
- tool 결과를 수정하거나 추가 설명을 붙이지 마세요
- 응답은 반드시 type, content, message 세 필드를 포함해야 합니다
</필수규칙>

"""


class OrchestratorResult(BaseModel):
    """Orchestrator result."""

    type: str = Field(description="응답 타입: data, answer, diary, image, 또는 report")
    content: str = Field(description="생성된 결과 내용")
    message: str = Field(description="응답 메시지")


def orchestrate_request(
    user_input: str,
    user_id: Optional[str] = None,
    current_date: Optional[str] = None,
    request_type: Optional[str] = None,
    temperature: Optional[float] = None,
    text: Optional[str] = None,
    image_base64: Optional[str] = None,
    record_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    사용자 요청을 분석하여 적절한 agent로 라우팅하는 메인 함수

    Args:
        user_input (str): 사용자 입력 데이터
        user_id (Optional[str]): 사용자 ID (Knowledge Base 검색 필터용)
        current_date (Optional[str]): 현재 날짜 (검색 컨텍스트용)
        request_type (Optional[str]): 요청 타입 ('summarize' 또는 'question'). 
                                       None이면 orchestrator가 자동 판단
        temperature (Optional[float]): summarize agent용 temperature 파라미터 (0.0 ~ 1.0)
        text (Optional[str]): 이미지 생성용 일기 텍스트
        image_base64 (Optional[str]): S3 업로드용 이미지 (base64)
        record_date (Optional[str]): S3 업로드용 날짜

    Returns:
        Dict[str, Any]: 처리 결과
            - type: "data" (데이터 저장), "answer" (질문 답변), "diary" (일기 생성), 
                    "image" (이미지 생성), "report" (주간 리포트)
            - content: 생성된 내용 (data인 경우 빈 문자열)
            - message: 응답 메시지
    """

    # 각 요청마다 새로운 Agent 생성
    orchestrator_agent = Agent(
        model=BEDROCK_MODEL_ARN,
        tools=[
            generate_auto_summarize,
            generate_auto_response,
            run_image_generator,
            run_weekly_report,
        ],
        system_prompt=ORCHESTRATOR_PROMPT,
    )

    # orchestrator에게 요청 처리
    prompt = f"""
사용자 요청을 분석하고 적절한 tool을 호출하세요.

<user_input>{user_input}</user_input>
<request_type>{request_type if request_type else '자동 판단'}</request_type>
"""
    
    # user_id 추가 (중요: tool 호출 시 반드시 전달)
    if user_id:
        prompt += f"\n<user_id>{user_id}</user_id>\n⚠️ 중요: generate_auto_response 호출 시 이 user_id를 반드시 전달하세요!"
    
    # current_date 추가 (중요: tool 호출 시 반드시 전달)
    if current_date:
        prompt += f"\n<current_date>{current_date}</current_date>\n⚠️ 중요: generate_auto_response 호출 시 이 current_date를 반드시 전달하세요!"
    
    # 이미지 생성 관련 파라미터 추가
    if text:
        prompt += f"\n<text>{text[:200]}...</text>\n⚠️ 중요: run_image_generator 호출 시 이 text를 반드시 전달하세요!"
    
    if image_base64:
        prompt += f"\n<image_base64>제공됨 (길이: {len(image_base64)})</image_base64>\n⚠️ 중요: run_image_generator 호출 시 이 image_base64를 반드시 전달하세요!"
    
    if record_date:
        prompt += f"\n<record_date>{record_date}</record_date>\n⚠️ 중요: run_image_generator 호출 시 이 record_date를 반드시 전달하세요!"
    
    # summarize 요청인 경우 temperature 정보 추가
    if request_type == "summarize" or request_type is None:
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
