"""
Agent Core Runtime 로그 확인 스크립트
"""
import boto3
import sys
from datetime import datetime, timedelta

def get_recent_logs(minutes=10):
    """최근 N분간의 로그를 가져옵니다"""
    
    logs_client = boto3.client('logs', region_name='us-east-1')
    
    # 로그 그룹 찾기
    print("로그 그룹 검색 중...")
    log_groups = logs_client.describe_log_groups()
    
    agent_log_groups = []
    for lg in log_groups['logGroups']:
        name = lg['logGroupName']
        if 'diary' in name.lower() or 'agent' in name.lower() or 'bedrock' in name.lower():
            agent_log_groups.append(name)
            print(f"  - {name}")
    
    if not agent_log_groups:
        print("❌ Agent 관련 로그 그룹을 찾을 수 없습니다.")
        return
    
    # 각 로그 그룹에서 최근 로그 가져오기
    start_time = int((datetime.now() - timedelta(minutes=minutes)).timestamp() * 1000)
    end_time = int(datetime.now().timestamp() * 1000)
    
    for log_group in agent_log_groups:
        print(f"\n{'='*80}")
        print(f"로그 그룹: {log_group}")
        print(f"{'='*80}")
        
        try:
            # 로그 스트림 가져오기
            streams = logs_client.describe_log_streams(
                logGroupName=log_group,
                orderBy='LastEventTime',
                descending=True,
                limit=5
            )
            
            if not streams['logStreams']:
                print("  (로그 스트림 없음)")
                continue
            
            # 최근 로그 이벤트 가져오기
            for stream in streams['logStreams'][:2]:  # 최근 2개 스트림만
                stream_name = stream['logStreamName']
                print(f"\n로그 스트림: {stream_name}")
                print("-" * 80)
                
                try:
                    events = logs_client.get_log_events(
                        logGroupName=log_group,
                        logStreamName=stream_name,
                        startTime=start_time,
                        endTime=end_time,
                        limit=100
                    )
                    
                    if not events['events']:
                        print("  (최근 로그 없음)")
                        continue
                    
                    for event in events['events']:
                        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                        message = event['message']
                        print(f"[{timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {message}")
                        
                except Exception as e:
                    print(f"  로그 이벤트 가져오기 실패: {str(e)}")
                    
        except Exception as e:
            print(f"  로그 스트림 가져오기 실패: {str(e)}")

if __name__ == "__main__":
    minutes = 10
    if len(sys.argv) > 1:
        try:
            minutes = int(sys.argv[1])
        except:
            pass
    
    print(f"최근 {minutes}분간의 로그를 확인합니다...\n")
    get_recent_logs(minutes)
