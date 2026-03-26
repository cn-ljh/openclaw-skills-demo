#!/usr/bin/env python3
"""
轮询 AWS Transcribe 任务状态，完成后下载转录结果并输出 JSON。
直接调用 AWS API（boto3），不依赖任何中间服务。

用法:
  python3 poll_task.py <job_name> [--once] [--timeout 900] [--interval 30]

--once    只查一次就退出（不轮询）
--timeout 最大等待秒数（默认 900 = 15 分钟）
--interval 轮询间隔秒数（默认 30）

输出（stdout，JSON）:
  {
    "status": "completed" | "processing" | "failed",
    "task_id": "...",
    "transcript": "完整转录文本（带说话人标记）",
    "filename": "原始文件名"
  }

环境要求:
  - AWS 凭证已配置
  - 权限: transcribe:GetTranscriptionJob, s3:GetObject
  - 配置: 编辑 config.py 中的 S3_BUCKET, AWS_REGION
"""
import sys
import os
import time
import json
import argparse
import boto3

# 导入配置
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import S3_BUCKET, AWS_REGION


def get_job_status(transcribe, job_name):
    """查询 Transcribe 任务状态"""
    resp = transcribe.get_transcription_job(TranscriptionJobName=job_name)
    return resp['TranscriptionJob']


def parse_transcript(transcript_json):
    """
    从 Transcribe JSON 结果中提取带说话人标记的文本。
    返回格式化后的字符串。

    策略：从顶层 items 按 speaker_label 分组（segment items 只有时间没有文字）。
    """
    results = transcript_json.get('results', {})
    items = results.get('items', [])

    if not items:
        # fallback: 直接取 transcript 文本
        transcripts = results.get('transcripts', [])
        if transcripts:
            return transcripts[0].get('transcript', '')
        return ''

    # 检查是否有 speaker_label
    has_speakers = any(item.get('speaker_label') for item in items)

    if has_speakers:
        # 按 speaker_label 连续分组
        lines = []
        current_speaker = None
        current_words = []

        for item in items:
            speaker = item.get('speaker_label', current_speaker)
            content = item.get('alternatives', [{}])[0].get('content', '')
            item_type = item.get('type', '')

            if speaker != current_speaker and current_speaker is not None:
                # Speaker changed, flush
                text = ''.join(current_words).strip()
                if text:
                    lines.append(f"**{current_speaker}**: {text}")
                current_words = []

            current_speaker = speaker

            if item_type == 'punctuation':
                current_words.append(content)
            else:
                current_words.append(content)

        # Flush last speaker
        if current_words and current_speaker:
            text = ''.join(current_words).strip()
            if text:
                lines.append(f"**{current_speaker}**: {text}")

        return '\n\n'.join(lines)
    else:
        # No speaker labels, use plain transcript
        transcripts = results.get('transcripts', [])
        if transcripts:
            return transcripts[0].get('transcript', '')
        return ''


def main():
    parser = argparse.ArgumentParser(description='Poll AWS Transcribe job and output transcript as JSON')
    parser.add_argument('job_name', help='Transcribe job name (from upload_and_transcribe.py output)')
    parser.add_argument('--once', action='store_true', help='Query once and exit')
    parser.add_argument('--timeout', type=int, default=900, help='Max wait seconds (default 900)')
    parser.add_argument('--interval', type=int, default=30, help='Poll interval seconds (default 30)')
    args = parser.parse_args()

    transcribe = boto3.client('transcribe', region_name=AWS_REGION)
    s3 = boto3.client('s3', region_name=AWS_REGION)
    start = time.time()

    while True:
        try:
            job = get_job_status(transcribe, args.job_name)
        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
            print(json.dumps({"status": "error", "task_id": args.job_name, "message": str(e)}))
            sys.exit(1)

        status = job['TranscriptionJobStatus']
        print(f"[{time.strftime('%H:%M:%S')}] Status: {status}", file=sys.stderr)

        if status == 'COMPLETED':
            # Download transcript from S3
            transcript_key = f"transcripts/{args.job_name}.json"
            print(f"Downloading transcript from s3://{S3_BUCKET}/{transcript_key} ...", file=sys.stderr)

            try:
                obj = s3.get_object(Bucket=S3_BUCKET, Key=transcript_key)
                transcript_json = json.loads(obj['Body'].read().decode('utf-8'))
            except Exception as e:
                # Fallback: try the URI from job output
                transcript_uri = job.get('Transcript', {}).get('TranscriptFileUri', '')
                print(f"S3 direct read failed ({e}), trying URI...", file=sys.stderr)
                import requests
                resp = requests.get(transcript_uri, timeout=30)
                transcript_json = resp.json()

            # Extract original filename from media URI
            media_uri = job.get('Media', {}).get('MediaFileUri', '')
            filename = media_uri.split('/')[-1] if media_uri else ''

            # Parse transcript
            transcript_text = parse_transcript(transcript_json)

            output = {
                "status": "completed",
                "task_id": args.job_name,
                "transcript": transcript_text,
                "filename": filename,
            }
            print(json.dumps(output, ensure_ascii=False))
            sys.exit(0)

        if status == 'FAILED':
            reason = job.get('FailureReason', 'Unknown')
            output = {
                "status": "failed",
                "task_id": args.job_name,
                "message": reason,
            }
            print(json.dumps(output, ensure_ascii=False))
            sys.exit(1)

        # Still IN_PROGRESS or QUEUED
        if args.once:
            output = {
                "status": "processing",
                "task_id": args.job_name,
            }
            print(json.dumps(output, ensure_ascii=False))
            sys.exit(0)

        elapsed = time.time() - start
        if elapsed > args.timeout:
            print(f"Timeout after {args.timeout}s", file=sys.stderr)
            output = {
                "status": "processing",
                "task_id": args.job_name,
                "message": f"Still processing after {args.timeout}s",
            }
            print(json.dumps(output, ensure_ascii=False))
            sys.exit(0)

        remaining = args.timeout - elapsed
        wait = min(args.interval, remaining)
        print(f"Waiting {int(wait)}s... ({int(elapsed)}s/{args.timeout}s)", file=sys.stderr)
        time.sleep(wait)


if __name__ == '__main__':
    main()
