"""
meeting-minutes skill 配置文件。
首次使用前请根据你的环境修改以下配置。
"""

# ============================================================
# AWS 配置
# ============================================================

# S3 存储桶名称（需提前创建）
# 示例: aws s3 mb s3://my-meeting-minutes --region us-west-2
S3_BUCKET = '<YOUR_S3_BUCKET>'

# S3 中音频文件的前缀
S3_PREFIX = 'audio'

# AWS 区域
AWS_REGION = 'us-west-2'

# ============================================================
# Transcribe 配置
# ============================================================

# 语言代码（zh-CN=中文, en-US=英文, ja-JP=日文 等）
# 完整列表: https://docs.aws.amazon.com/transcribe/latest/dg/supported-languages.html
LANGUAGE_CODE = 'zh-CN'

# 最大说话人数量（1-10）
MAX_SPEAKER_LABELS = 10

# ============================================================
# 邮件配置
# ============================================================

# 会议纪要邮件收件人
EMAIL_TO = '<YOUR_EMAIL>'

# imap-smtp-email skill 路径（相对于 workspace）
IMAP_SMTP_SKILL_PATH = 'skills/imap-smtp-email'

# ============================================================
# 文件限制
# ============================================================

# 支持的音频/视频格式
SUPPORTED_EXTENSIONS = {'mp3', 'mp4', 'wav', 'm4a', 'flac', 'ogg', 'webm', 'amr', 'aac'}

# 格式映射（文件扩展名 → Transcribe MediaFormat）
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
