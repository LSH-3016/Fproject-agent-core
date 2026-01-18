#!/bin/bash

# Agent Core Runtime 로그 확인 스크립트

LOG_GROUP="/aws/bedrock-agentcore/runtimes/diary_orchestrator_agent-90S9ctAFht-DEFAULT"
REGION="us-east-1"

echo "=========================================="
echo "Agent Core Runtime 로그 확인"
echo "=========================================="
echo "Log Group: $LOG_GROUP"
echo ""

# 최근 10분간의 로그 확인
echo "최근 10분간의 로그를 가져오는 중..."
aws logs tail $LOG_GROUP \
  --since 10m \
  --format short \
  --region $REGION \
  --follow
