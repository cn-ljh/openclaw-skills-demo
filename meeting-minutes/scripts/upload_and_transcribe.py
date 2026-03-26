#!/usr/bin/env python3
"""
上传音频文件到 S3 并启动 AWS Transcribe 转录任务。
直接调用 AWS API（boto3），不依赖任何中间 Serverless 服务。

用法:
  python3 upload_and_transcribe.py <audio_file_path>

输出 (stdout):
  TASK_ID=<transcribe_job_name>

环境要求:
  - AWS 凭证已配置（IAM role / env vars / ~/.aws/credentials）
  - 权限: s3:PutObject, transcribe:StartTranscriptionJob
  - 配置: 编辑 config.py 中的 S3_BUCKET, AWS_REGION 等
"""
import sys
import os
import uuid
import boto3
from datetime import datetime, timezone

# 导入配置
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (
    S3_BUCKET, S3_PREFIX, AWS_REGION,
    LANGUAGE_CODE, MAX_SPEAKER_LABELS,
    SUPPORTED_EXTENSIONS, MEDIA_FORMAT_MAP,
)


def validate_config():
    """检查配置是否已填写"""
    if S3_BUCKET.startswith('<') or not S3_BUCKET:
        print("ERROR: Please configure S3_BUCKET in scripts/config.py", file=sys.stderr)
        print("  1. Create a bucket: aws s3 mb s3://your-bucket --region us-west-2", file=sys.stderr)
        print("  2. Edit scripts/config.py and set S3_BUCKET", file=sys.stderr)
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 upload_and_transcribe.py <audio_file_path>", file=sys.stderr)
        sys.exit(1)

    validate_config()

    file_path = sys.argv[1]

    if not os.path.exists(file_path):
        print(f"ERROR: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    file_size = os.path.getsize(file_path)
    filename = os.path.basename(file_path)
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

    if ext not in SUPPORTED_EXTENSIONS:
        print(f"WARNING: Extension '.{ext}' may not be supported by Transcribe.", file=sys.stderr)

    print(f"File: {filename} ({file_size / 1024 / 1024:.1f} MB)", file=sys.stderr)

    # Generate unique job name
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    job_name = f"mm-{timestamp}-{uuid.uuid4().hex[:8]}"
    s3_key = f"{S3_PREFIX}/{job_name}/{filename}"

    # Upload to S3
    print(f"Uploading to s3://{S3_BUCKET}/{s3_key} ...", file=sys.stderr)
    s3 = boto3.client('s3', region_name=AWS_REGION)
    s3.upload_file(file_path, S3_BUCKET, s3_key)
    print("Upload complete.", file=sys.stderr)

    s3_uri = f"s3://{S3_BUCKET}/{s3_key}"
    media_format = MEDIA_FORMAT_MAP.get(ext, 'mp4')

    # Start Transcribe job
    print(f"Starting Transcribe job: {job_name} ...", file=sys.stderr)
    transcribe = boto3.client('transcribe', region_name=AWS_REGION)

    params = {
        'TranscriptionJobName': job_name,
        'LanguageCode': LANGUAGE_CODE,
        'MediaFormat': media_format,
        'Media': {'MediaFileUri': s3_uri},
        'OutputBucketName': S3_BUCKET,
        'OutputKey': f"transcripts/{job_name}.json",
        'Settings': {
            'ShowSpeakerLabels': True,
            'MaxSpeakerLabels': MAX_SPEAKER_LABELS,
        },
    }

    transcribe.start_transcription_job(**params)
    print(f"Transcribe job started: {job_name}", file=sys.stderr)

    # Machine-readable output on stdout
    print(f"TASK_ID={job_name}")


if __name__ == '__main__':
    main()
