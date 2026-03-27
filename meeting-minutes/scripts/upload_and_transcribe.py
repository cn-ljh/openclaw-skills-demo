#!/usr/bin/env python3
"""
上传音频文件到 S3 并启动 AWS Transcribe 转录任务。
直接调用 AWS API（boto3），不依赖任何中间 Serverless 服务。

用法:
  python3 upload_and_transcribe.py <audio_file_path> [--lang <code>]

  --lang <code>  指定语言代码（如 en-US, zh-CN, ja-JP）
                 不指定时自动检测语言（Transcribe IdentifyLanguage）

输出 (stdout):
  TASK_ID=<transcribe_job_name>

环境要求:
  - AWS 凭证已配置（IAM role / env vars / ~/.aws/credentials）
  - 权限: s3:PutObject, transcribe:StartTranscriptionJob
"""
import sys
import os
import uuid
import argparse
import boto3
from datetime import datetime, timezone

S3_BUCKET = '<YOUR_S3_BUCKET>'
S3_PREFIX = 'audio'
AWS_REGION = 'us-west-2'
MAX_SPEAKER_LABELS = 10

SUPPORTED_EXTENSIONS = {'mp3', 'mp4', 'wav', 'm4a', 'flac', 'ogg', 'webm', 'amr', 'aac'}
MEDIA_FORMAT_MAP = {
    'mp3': 'mp3',
    'mp4': 'mp4',
    'wav': 'wav',
    'm4a': 'mp4',
    'flac': 'flac',
    'ogg': 'ogg',
    'webm': 'webm',
    'amr': 'amr',
    'aac': 'mp4',
}


def main():
    parser = argparse.ArgumentParser(description='Upload audio and start AWS Transcribe job')
    parser.add_argument('file_path', help='Path to audio file')
    parser.add_argument('--lang', default=None,
                        help='Language code (e.g. en-US, zh-CN, ja-JP). '
                             'Omit for automatic language detection.')
    args = parser.parse_args()

    file_path = args.file_path
    lang_code = args.lang

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
    transcribe = boto3.client('transcribe', region_name=AWS_REGION)

    params = {
        'TranscriptionJobName': job_name,
        'MediaFormat': media_format,
        'Media': {'MediaFileUri': s3_uri},
        'OutputBucketName': S3_BUCKET,
        'OutputKey': f"transcripts/{job_name}.json",
        'Settings': {
            'ShowSpeakerLabels': True,
            'MaxSpeakerLabels': MAX_SPEAKER_LABELS,
        },
    }

    if lang_code:
        # 指定语言
        params['LanguageCode'] = lang_code
        print(f"Starting Transcribe job: {job_name} (language: {lang_code}) ...", file=sys.stderr)
    else:
        # 自动语言检测 — 支持中英日韩法德西等常见语言
        params['IdentifyLanguage'] = True
        params['LanguageOptions'] = [
            'zh-CN', 'en-US', 'ja-JP', 'ko-KR',
            'fr-FR', 'de-DE', 'es-ES', 'pt-BR',
        ]
        print(f"Starting Transcribe job: {job_name} (auto-detect language) ...", file=sys.stderr)

    transcribe.start_transcription_job(**params)
    print(f"Transcribe job started: {job_name}", file=sys.stderr)

    # Machine-readable output
    print(f"TASK_ID={job_name}")


if __name__ == '__main__':
    main()
