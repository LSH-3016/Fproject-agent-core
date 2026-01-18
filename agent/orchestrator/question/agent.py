import json
import logging
import os
from typing import Any, Dict, List

from strands import Agent, tool
from strands_tools import retrieve

# Secrets Manager에서 설정 가져오기
try:
    from ..utils.secrets import get_config
    config = get_config()
    os.environ['KNOWLEDGE_BASE_ID'] = config.get('KNOWLEDGE_BASE_ID', '')
    os.environ['AWS_REGION'] = config.get('AWS_REGION', 'us-east-1')
except Exception as e:
    print(f"⚠️  설정을 가져올 수 없습니다: {str(e)}")
    # ========================================
    # ⚠️ 환경 변수 설정 - 실제 값으로 수정하세요
    # ========================================
    # TODO: 실제 Knowledge Base ID로 교체
    os.environ['KNOWLEDGE_BASE_ID'] = os.environ.get('KNOWLEDGE_BASE_ID', '<your-knowledge-base-id>')
    # TODO: 실제 AWS Region으로 교체
    os.environ['AWS_REGION'] = os.environ.get('AWS_REGION', 'us-east-1')

RESPONSE_SYSTEM_PROMPT = """
    당신은 일기를 분석하여 고객의 질문에 답변하는 AI 어시스턴트입니다.

    고객 질문에 적절한 답변을 생성하기 위해 다음 순서를 정확히 따라주세요:

    <작업순서>
    1. 반드시 먼저 retrieve 도구를 사용하여 지식베이스에서 관련 정보를 검색합니다
    2. 고객의 user_id를 참고하여, 해당 폴더의 내용만 확인하도록 합니다
    3. 검색된 정보를 활용하여 정확한 답변을 준비합니다
    4. SELLER_ANSWER_PROMPT에 정의된 셀러의 톤과 스타일을 적용합니다
    </작업순서>

    <답변지침>
    - 모든 사실 정보는 검색된 지식베이스 내용을 기반으로 합니다
    - 모호한 답변보다는 구체적이고 실행 가능한 답변을 제공합니다
    - 전문적이면서도 따뜻한 톤을 유지합니다
    - 개인정보나 민감한 정보는 공개적으로 언급하지 않습니다
    - user_id를 답변에 포함하지 않습니다
    - 다른 사용자의 기록은 답변에 포함하지 않습니다
    - 다른 사용자를 언급하지 않습니다
    - 복잡한 문제는 해당 내용을 확인할 수 없다고 답변합니다
    - 지식베이스에 없는 내용은 해당하는 내용이 없다고 답변합니다
    - 질문에 해당하는 내용외의 일기 내용은 언급하지마
    - 질문에 대한 답변만 하고, 추측과 의견은 붙이지 않습니다
    - 일기의 내용을 리뷰하지 않습니다
    - 추측성, 애매모한 표현을 사용하지 않습니다
    - 답변에 백틱이나 코드 블록 포맷(```json, ```python 등)을 붙이지 마세요. plain text로 보여주세요. 

    </답변지침>

    <필수규칙>
    - 반드시 답변하기 전에 retrieve 도구를 먼저 사용해야 합니다
    - 반드시 user_id를 참고하여, 해당 사용자의 폴더 내용만을 참고하여 답변해야 합니다
    - SELLER_ANSWER_PROMPT의 톤 가이드를 반드시 따라야 합니다
    - 자연스러운 한국어로 작성합니다
    - 지식베이스에서 찾지 못한 정보는 절대 만들어내지 않습니다
    - 답변은 간결하지만 완전해야 합니다
    - 질문에 대한 답변만 생성하고, 사족은 달지마
    - 질문에 대한 답변이 없으면, 일기 내용에 대해 언급하지마
    </필수규칙>

"""

SELLER_ANSWER_PROMPT = """
나는 40대 셀러로, 우리 제품은 주로 30대 사용자들이므로, 이를 감안한 답변을 해야 합니다.
고객에게 오해의 여지가 없도록 깔끔하고 차분하게 정보에 기반한 답변을 제공해주세요.
단, 공손한 톤이어야 합니다. 
"""

@tool
def generate_auto_response(question: str, user_id: str = None) -> Dict[str, Any]:
    """
    질문에 대한 답변을 생성하는 메인 함수

    Args:
        question (str): 사용자의 질문
        user_id (str): 사용자 ID (Knowledge Base 검색 필터용)

    Returns:
        Dict[str, Any]: 생성한 답변
    """

    # 각 요청마다 새로운 Agent 생성
    auto_response_agent = Agent(
        tools=[retrieve],
        system_prompt=RESPONSE_SYSTEM_PROMPT
        + f"""
        SELLER_ANSWER_PROMPT: {SELLER_ANSWER_PROMPT}
        """
        + (f"\n<user_id>{user_id}</user_id>" if user_id else ""),
    )

    # user_id가 있으면 검색 쿼리에 포함
    search_query = question
    if user_id:
        search_query = f"user_id: {user_id}\n질문: {question}"

    # 리뷰에 대한 자동 응답 생성
    response = auto_response_agent(search_query)

    # tool_result 를 추출
    tool_results = filter_tool_result(auto_response_agent)

    # 결과 반환 - tool_results를 포함
    result = {"response": str(response)}#, "tool_results": tool_results}
    return result

def filter_tool_result(agent: Agent) -> List:
    """
    Agent의 실행 결과에서 tool_result만을 추출하는 함수

    Args:
        agent (Agent): Agent 인스턴스

    Returns:
        Dict[str, Any]: tool_result만을 포함하는 딕셔너리
    """
    tool_results = []
    for m in agent.messages:
        for content in m["content"]:
            if "toolResult" in content:
                tool_results.append(m["content"][0]["toolResult"])
    return tool_results