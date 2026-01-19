"""
Image Generator Agent - Strands 기반 Master Agent
일기 텍스트를 이미지로 변환하는 AI Agent
"""

import os
import asyncio
from typing import Dict, Any

from strands import Agent, tool
from strands.models import BedrockModel

from .prompts import AGENT_SYSTEM_PROMPT
from .tools import ImageGeneratorTools
from agent.utils.secrets import get_config

# 설정 로드
config = get_config()

# AWS 설정
AWS_REGION = config.get("AWS_REGION", os.environ.get("AWS_REGION", "us-east-1"))

# Claude 모델 (에이전트 추론용)
model = BedrockModel(
    model_id=config.get("BEDROCK_CLAUDE_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0"),
    region_name=AWS_REGION
)

# Tools 인스턴스
_tools = ImageGeneratorTools()


# ============================================================================
# Strands Tools (ImageGeneratorTools 래핑)
# ============================================================================

@tool
def generate_image_from_text(text: str) -> Dict[str, Any]:
    """
    일기 텍스트를 입력받아 이미지를 생성합니다.
    Claude Sonnet으로 프롬프트 변환 후 Nova Canvas로 이미지 생성.
    
    Args:
        text: 일기 텍스트 (한글)
    
    Returns:
        생성된 이미지 정보 (image_base64, prompt)
    """
    return asyncio.get_event_loop().run_until_complete(
        _tools.generate_image_from_text(text)
    )


@tool
def generate_image_for_history(history_id: int) -> Dict[str, Any]:
    """
    히스토리 ID를 입력받아 이미지를 생성하고 S3에 업로드합니다.
    
    Args:
        history_id: 히스토리 ID
    
    Returns:
        생성된 이미지 정보 (s3_key, image_url)
    """
    return asyncio.get_event_loop().run_until_complete(
        _tools.generate_image_for_history(history_id)
    )


@tool
def preview_image(history_id: int) -> Dict[str, Any]:
    """
    히스토리 ID로 이미지 미리보기를 생성합니다 (S3 업로드 없음).
    
    Args:
        history_id: 히스토리 ID
    
    Returns:
        미리보기 이미지 정보 (image_base64, prompt)
    """
    return asyncio.get_event_loop().run_until_complete(
        _tools.preview_image(history_id)
    )


@tool
def confirm_and_upload_image(history_id: int, image_base64: str) -> Dict[str, Any]:
    """
    미리보기 이미지를 확인 후 S3에 업로드합니다.
    
    Args:
        history_id: 히스토리 ID
        image_base64: 업로드할 이미지 (base64)
    
    Returns:
        업로드 결과 (s3_key, image_url)
    """
    return asyncio.get_event_loop().run_until_complete(
        _tools.confirm_and_upload_image(history_id, image_base64)
    )


@tool
def batch_generate_images(limit: int = 5) -> Dict[str, Any]:
    """
    이미지가 없는 여러 히스토리에 대해 배치로 이미지를 생성합니다.
    
    Args:
        limit: 처리할 최대 개수 (기본 5, 최대 20)
    
    Returns:
        배치 처리 결과 (summary, results)
    """
    return asyncio.get_event_loop().run_until_complete(
        _tools.batch_generate_images(limit)
    )


@tool
def get_histories_without_image(limit: int = 10) -> Dict[str, Any]:
    """
    이미지가 없는 히스토리 목록을 조회합니다.
    
    Args:
        limit: 조회할 최대 개수 (기본 10)
    
    Returns:
        히스토리 목록
    """
    return asyncio.get_event_loop().run_until_complete(
        _tools.get_histories_without_image(limit)
    )


@tool
def build_prompt_from_text(text: str) -> Dict[str, Any]:
    """
    일기 텍스트를 이미지 생성 프롬프트로 변환합니다 (이미지 생성 없음).
    
    Args:
        text: 일기 텍스트 (한글)
    
    Returns:
        생성된 프롬프트 (positive_prompt, negative_prompt)
    """
    return asyncio.get_event_loop().run_until_complete(
        _tools.build_prompt_from_text(text)
    )


@tool
def get_history_by_id(history_id: int) -> Dict[str, Any]:
    """
    특정 히스토리의 상세 정보를 조회합니다.
    
    Args:
        history_id: 히스토리 ID
    
    Returns:
        히스토리 상세 정보
    """
    return asyncio.get_event_loop().run_until_complete(
        _tools.get_history_by_id(history_id)
    )


@tool
def health_check() -> Dict[str, Any]:
    """
    이미지 생성 서비스의 상태를 확인합니다.
    
    Returns:
        서비스 상태 정보
    """
    return asyncio.get_event_loop().run_until_complete(
        _tools.health_check()
    )


# ============================================================================
# Image Generator Master Agent
# ============================================================================

image_generator_agent = Agent(
    model=model,
    system_prompt=AGENT_SYSTEM_PROMPT,
    tools=[
        generate_image_from_text,
        generate_image_for_history,
        preview_image,
        confirm_and_upload_image,
        batch_generate_images,
        get_histories_without_image,
        build_prompt_from_text,
        get_history_by_id,
        health_check,
    ]
)


def run_image_generator(request: str, history_id: int = None, text: str = None) -> Dict[str, Any]:
    """
    Image Generator Agent 실행 함수
    
    Args:
        request: 사용자 요청 (자연어)
        history_id: 히스토리 ID (선택)
        text: 일기 텍스트 (선택)
    
    Returns:
        에이전트 실행 결과
    """
    # 컨텍스트 구성
    prompt = f"요청: {request}"
    if history_id:
        prompt += f"\n히스토리 ID: {history_id}"
    if text:
        prompt += f"\n일기 텍스트: {text}"
    
    try:
        response = image_generator_agent(prompt)
        return {
            "success": True,
            "response": str(response)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
