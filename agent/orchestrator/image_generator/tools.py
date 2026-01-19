"""
Image Generator Tools - boto3 기반 직접 AWS 호출
TypeScript 서비스 없이 독립 실행
"""

import os
import json
import base64
import random
import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime

import boto3
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

# ============================================================================
# 설정
# ============================================================================

# Nova Canvas 설정
NOVA_CANVAS_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "amazon.nova-canvas-v1:0")
CLAUDE_MODEL_ID = os.getenv("BEDROCK_LLM_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET = os.getenv("KNOWLEDGE_BASE_BUCKET", "")

# 이미지 생성 설정
IMAGE_CONFIG = {
    "width": 1024,
    "height": 1280,  # 4:5 비율
    "cfg_scale": 6.5,
    "number_of_images": 1
}

# Negative Prompt
NEGATIVE_PROMPT = """anime, cartoon, illustration, painting, sketch, drawing, 3d render, cgi, unreal engine, fantasy, surreal, low quality, low resolution, blurry, out of focus, noise, overexposed, underexposed, jpeg artifacts, deformed body, distorted face, bad anatomy, extra fingers, missing fingers, fused fingers, extra limbs, missing limbs, overly posed, studio lighting, text, caption, subtitle, watermark, logo, wrong food, wrong animal, substituted items, inaccurate details"""

# Claude 시스템 프롬프트
SYSTEM_PROMPT = """You are an expert at converting Korean diary entries into detailed English image generation prompts for realistic photography.

CRITICAL RULES:
1. Read the Korean diary CAREFULLY and extract ALL visual elements
2. Your output must be ONLY the English prompt - no explanations, no Korean text
3. The prompt must accurately reflect what is described in the diary

MUST INCLUDE if mentioned in diary:
- WEATHER: rainy, sunny, cloudy, snowy, foggy, etc.
- TIME OF DAY: morning light, afternoon, sunset, evening, night
- LOCATION: indoor/outdoor, home, cafe, park, street, window view
- ANIMALS: dog, cat, etc. with specific actions they're doing
- MOOD: cozy, peaceful, melancholic, warm, lonely, happy

CRITICAL - TOGETHERNESS:
- If the diary mentions doing something WITH a pet, the image MUST show BOTH the person AND the animal TOGETHER
- Use phrases like "a person walking together with their dog", "owner and dog side by side"

CRITICAL - ETHNICITY:
- ALL people in the image MUST be Asian/East Asian
- Always include "Asian" or "East Asian" when describing people

PROMPT STRUCTURE:
"A realistic photo of [Asian person and animal together doing activity], [weather conditions], [lighting], [specific details], [mood/atmosphere], natural photography style, high quality"

Keep prompt under 500 characters."""


# ============================================================================
# AWS 클라이언트
# ============================================================================

_bedrock_client = None
_s3_client = None
_db_pool = None


def get_bedrock_client():
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = boto3.client(
            "bedrock-runtime",
            region_name=AWS_REGION
        )
    return _bedrock_client


def get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client("s3", region_name=AWS_REGION)
    return _s3_client


def get_db_connection():
    """PostgreSQL 연결"""
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
        sslmode="require"
    )


# ============================================================================
# 핵심 기능
# ============================================================================

def generate_prompt_with_claude(journal_text: str) -> Dict[str, str]:
    """Claude를 사용하여 한글 일기를 영어 프롬프트로 변환"""
    client = get_bedrock_client()
    
    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "system": SYSTEM_PROMPT,
        "messages": [
            {
                "role": "user",
                "content": f"Convert this Korean diary entry into an English image generation prompt:\n\n{journal_text}"
            }
        ]
    }
    
    try:
        response = client.invoke_model(
            modelId=CLAUDE_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response["body"].read())
        generated_prompt = response_body.get("content", [{}])[0].get("text", "").strip()
        
        # 1024자 제한
        if len(generated_prompt) > 1024:
            generated_prompt = generated_prompt[:1021] + "..."
        
        logger.info(f"[PromptBuilder] Generated prompt: {generated_prompt[:100]}...")
        
        return {
            "positive_prompt": generated_prompt,
            "negative_prompt": NEGATIVE_PROMPT
        }
    except Exception as e:
        logger.error(f"[PromptBuilder] Claude error: {e}")
        # 폴백
        return {
            "positive_prompt": f"A realistic documentary-style photo representing: {journal_text[:200]}",
            "negative_prompt": NEGATIVE_PROMPT
        }


def generate_image_with_nova(positive_prompt: str, negative_prompt: str = None) -> Dict[str, Any]:
    """Nova Canvas로 이미지 생성"""
    client = get_bedrock_client()
    
    seed = random.randint(0, 2147483647)
    
    request_body = {
        "taskType": "TEXT_IMAGE",
        "textToImageParams": {
            "text": positive_prompt,
            "negativeText": negative_prompt or NEGATIVE_PROMPT
        },
        "imageGenerationConfig": {
            "cfgScale": IMAGE_CONFIG["cfg_scale"],
            "seed": seed,
            "width": IMAGE_CONFIG["width"],
            "height": IMAGE_CONFIG["height"],
            "numberOfImages": IMAGE_CONFIG["number_of_images"]
        }
    }
    
    try:
        logger.info(f"[ImageGenerator] Generating image with Nova Canvas (seed: {seed})...")
        
        response = client.invoke_model(
            modelId=NOVA_CANVAS_MODEL_ID,
            contentType="application/json",
            accept="*/*",
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response["body"].read())
        
        if not response_body.get("images"):
            return {"success": False, "error": "No images returned from Nova Canvas"}
        
        image_base64 = response_body["images"][0]
        logger.info("[ImageGenerator] Image generated successfully")
        
        return {
            "success": True,
            "image_base64": image_base64
        }
    except Exception as e:
        logger.error(f"[ImageGenerator] Nova Canvas error: {e}")
        return {"success": False, "error": str(e)}


def upload_to_s3(user_id: str, record_date: datetime, image_base64: str) -> Dict[str, str]:
    """S3에 이미지 업로드"""
    client = get_s3_client()
    
    # 경로 생성: {user_id}/history/{YYYY}/{MM}/{DD}/image_{timestamp}.png
    year = record_date.strftime("%Y")
    month = record_date.strftime("%m")
    day = record_date.strftime("%d")
    timestamp = int(time.time() * 1000)
    
    s3_key = f"{user_id}/history/{year}/{month}/{day}/image_{timestamp}.png"
    
    try:
        image_bytes = base64.b64decode(image_base64)
        
        client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=image_bytes,
            ContentType="image/png"
        )
        
        image_url = f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
        logger.info(f"[S3] Uploaded: {s3_key}")
        
        return {
            "s3_key": s3_key,
            "image_url": image_url
        }
    except Exception as e:
        logger.error(f"[S3] Upload error: {e}")
        raise


def delete_from_s3(s3_key: str):
    """S3에서 파일 삭제"""
    if not s3_key:
        return
    
    try:
        client = get_s3_client()
        client.delete_object(Bucket=S3_BUCKET, Key=s3_key)
        logger.info(f"[S3] Deleted: {s3_key}")
    except Exception as e:
        logger.error(f"[S3] Delete error: {e}")


# ============================================================================
# Tools 클래스
# ============================================================================

class ImageGeneratorTools:
    """Image Generator Agent의 도구 모음 - boto3 직접 호출"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
    
    async def generate_image_from_text(self, text: str) -> Dict[str, Any]:
        """텍스트에서 이미지 생성"""
        try:
            # 1. Claude로 프롬프트 생성
            prompt_result = generate_prompt_with_claude(text)
            
            # 2. Nova Canvas로 이미지 생성
            image_result = generate_image_with_nova(
                prompt_result["positive_prompt"],
                prompt_result["negative_prompt"]
            )
            
            if not image_result["success"]:
                return {"success": False, "error": image_result["error"]}
            
            return {
                "success": True,
                "image_base64": image_result["image_base64"],
                "prompt": {
                    "positive": prompt_result["positive_prompt"],
                    "negative": prompt_result["negative_prompt"]
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def generate_image_for_history(self, history_id: int) -> Dict[str, Any]:
        """히스토리 ID로 이미지 생성 및 S3 업로드"""
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # 히스토리 조회
            cur.execute(
                "SELECT id, user_id, content, record_date, s3_key FROM history WHERE id = %s",
                (history_id,)
            )
            history = cur.fetchone()
            
            if not history:
                return {"success": False, "error": "History not found"}
            
            # 이미 이미지가 있는 경우
            if history["s3_key"]:
                return {
                    "success": True,
                    "history_id": history_id,
                    "user_id": history["user_id"],
                    "image_generated": False,
                    "already_had_image": True,
                    "s3_key": history["s3_key"],
                    "image_url": f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{history['s3_key']}"
                }
            
            # 내용이 없는 경우
            if not history["content"] or not history["content"].strip():
                return {"success": False, "error": "History content is empty"}
            
            # 프롬프트 생성
            prompt_result = generate_prompt_with_claude(history["content"])
            
            # 이미지 생성
            image_result = generate_image_with_nova(
                prompt_result["positive_prompt"],
                prompt_result["negative_prompt"]
            )
            
            if not image_result["success"]:
                return {"success": False, "error": image_result["error"]}
            
            # S3 업로드
            s3_result = upload_to_s3(
                history["user_id"],
                history["record_date"],
                image_result["image_base64"]
            )
            
            # DB 업데이트
            cur.execute(
                "UPDATE history SET s3_key = %s WHERE id = %s",
                (s3_result["s3_key"], history_id)
            )
            conn.commit()
            
            cur.close()
            conn.close()
            
            return {
                "success": True,
                "history_id": history_id,
                "user_id": history["user_id"],
                "image_generated": True,
                "s3_key": s3_result["s3_key"],
                "image_url": s3_result["image_url"]
            }
        except Exception as e:
            logger.error(f"[Tools] generate_image_for_history error: {e}")
            return {"success": False, "error": str(e)}
    
    async def preview_image(self, history_id: int) -> Dict[str, Any]:
        """이미지 미리보기 생성 (S3 업로드 없음)"""
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute(
                "SELECT id, user_id, content FROM history WHERE id = %s",
                (history_id,)
            )
            history = cur.fetchone()
            cur.close()
            conn.close()
            
            if not history:
                return {"success": False, "error": "History not found"}
            
            if not history["content"] or not history["content"].strip():
                return {"success": False, "error": "History content is empty"}
            
            # 프롬프트 생성
            prompt_result = generate_prompt_with_claude(history["content"])
            
            # 이미지 생성
            image_result = generate_image_with_nova(
                prompt_result["positive_prompt"],
                prompt_result["negative_prompt"]
            )
            
            if not image_result["success"]:
                return {"success": False, "error": image_result["error"]}
            
            return {
                "success": True,
                "history_id": history_id,
                "user_id": history["user_id"],
                "image_base64": image_result["image_base64"],
                "prompt": {
                    "positive": prompt_result["positive_prompt"],
                    "negative": prompt_result["negative_prompt"]
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def confirm_and_upload_image(self, history_id: int, image_base64: str) -> Dict[str, Any]:
        """미리보기 확인 후 S3 업로드"""
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute(
                "SELECT id, user_id, record_date, s3_key FROM history WHERE id = %s",
                (history_id,)
            )
            history = cur.fetchone()
            
            if not history:
                cur.close()
                conn.close()
                return {"success": False, "error": "History not found"}
            
            # 이전 이미지 삭제
            if history["s3_key"]:
                delete_from_s3(history["s3_key"])
            
            # S3 업로드
            s3_result = upload_to_s3(
                history["user_id"],
                history["record_date"],
                image_base64
            )
            
            # DB 업데이트
            cur.execute(
                "UPDATE history SET s3_key = %s WHERE id = %s",
                (s3_result["s3_key"], history_id)
            )
            conn.commit()
            
            cur.close()
            conn.close()
            
            return {
                "success": True,
                "history_id": history_id,
                "user_id": history["user_id"],
                "s3_key": s3_result["s3_key"],
                "image_url": s3_result["image_url"]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def batch_generate_images(self, limit: int = 5) -> Dict[str, Any]:
        """배치 이미지 생성"""
        try:
            limit = min(limit, 20)
            
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # 이미지가 없는 히스토리 조회
            cur.execute("""
                SELECT id FROM history 
                WHERE s3_key IS NULL AND content IS NOT NULL AND content != ''
                ORDER BY record_date DESC
                LIMIT %s
            """, (limit,))
            
            histories = cur.fetchall()
            cur.close()
            conn.close()
            
            results = []
            summary = {"total": len(histories), "generated": 0, "skipped": 0, "failed": 0}
            
            for history in histories:
                result = await self.generate_image_for_history(history["id"])
                results.append(result)
                
                if result.get("image_generated"):
                    summary["generated"] += 1
                elif result.get("already_had_image"):
                    summary["skipped"] += 1
                else:
                    summary["failed"] += 1
                
                # Rate limiting
                await asyncio.sleep(1)
            
            return {
                "success": True,
                "summary": summary,
                "results": results
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_histories_without_image(self, limit: int = 10) -> Dict[str, Any]:
        """이미지가 없는 히스토리 조회"""
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("""
                SELECT id, user_id, content, record_date, tags
                FROM history 
                WHERE s3_key IS NULL AND content IS NOT NULL AND content != ''
                ORDER BY record_date DESC
                LIMIT %s
            """, (limit,))
            
            histories = cur.fetchall()
            cur.close()
            conn.close()
            
            return {
                "success": True,
                "count": len(histories),
                "histories": [
                    {
                        "id": h["id"],
                        "user_id": h["user_id"],
                        "content": h["content"],
                        "record_date": h["record_date"].isoformat() if h["record_date"] else None,
                        "tags": h["tags"]
                    }
                    for h in histories
                ]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def build_prompt_from_text(self, text: str) -> Dict[str, Any]:
        """프롬프트만 생성"""
        try:
            prompt_result = generate_prompt_with_claude(text)
            
            return {
                "success": True,
                "positive_prompt": prompt_result["positive_prompt"],
                "negative_prompt": prompt_result["negative_prompt"]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_history_by_id(self, history_id: int) -> Dict[str, Any]:
        """특정 히스토리 조회"""
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("""
                SELECT id, user_id, content, record_date, tags, s3_key
                FROM history WHERE id = %s
            """, (history_id,))
            
            history = cur.fetchone()
            cur.close()
            conn.close()
            
            if not history:
                return {"success": False, "error": "History not found"}
            
            image_url = None
            if history["s3_key"]:
                image_url = f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{history['s3_key']}"
            
            return {
                "success": True,
                "history": {
                    "id": history["id"],
                    "user_id": history["user_id"],
                    "content": history["content"],
                    "record_date": history["record_date"].isoformat() if history["record_date"] else None,
                    "tags": history["tags"],
                    "s3_key": history["s3_key"],
                    "image_url": image_url
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """서비스 상태 확인"""
        try:
            # DB 연결 테스트
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
            conn.close()
            
            return {
                "success": True,
                "status": "ok",
                "service": "image-generator-agent",
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "status": "error",
                "error": str(e)
            }


# asyncio import (batch_generate_images에서 사용)
import asyncio
