#!/bin/bash
# Agent Core Runtime CloudWatch Logs 확인 스크립트

LOG_GROUP="/aws/bedrock-agentcore/runtimes/diary_orchestrator_agent-90S9ctAFht-DEFAULT"

echo "🔍 Agent Core Runtime 로그 확인 중..."
echo "Log Group: $LOG_GROUP"
echo ""

# 최근 10분간의 로그 확인
START_TIME=$(date -u -d '10 minutes ago' +%s)000

echo "📋 최근 로그 스트림:"
aws logs describe-log-streams \
  --log-group-name "$LOG_GROUP" \
  --order-by LastEventTime \
  --descending \
  --max-items 3 \
  --query 'logStreams[*].[logStreamName,lastEventTime]' \
  --output table

echo ""
echo "📄 최근 로그 내용:"
aws logs tail "$LOG_GROUP" --since 10m --format short

echo ""
echo "🔍 에러 로그 검색:"
aws logs filter-log-events \
  --log-group-name "$LOG_GROUP" \
  --filter-pattern "ERROR" \
  --start-time $START_TIME \
  --query 'events[*].message' \
  --output text

echo ""
echo "🔍 CRITICAL 로그 검색:"
aws logs filter-log-events \
  --log-group-name "$LOG_GROUP" \
  --filter-pattern "CRITICAL" \
  --start-time $START_TIME \
  --query 'events[*].message' \
  --output text
