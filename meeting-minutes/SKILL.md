---
name: meeting-minutes
description: 会议纪要助手。用户从飞书/微信发送语音、视频文件或提供文件链接，自动转录并生成会议纪要摘要，将摘要和原文通过邮件发送给 <YOUR_EMAIL>。

**触发条件**：
(1) 用户发送音频/视频文件（mp3, mp4, wav, m4a, flac, ogg, webm）
(2) 用户发送音频/视频文件的链接（S3、HTTP 等）
(3) 用户明确要求"转录"、"会议纪要"、"会议记录"、"meeting minutes"
(4) 用户说"帮我整理一下这个录音/会议"

**不触发**：短语音消息（<1分钟的日常语音对话）
metadata:
  openclaw:
    emoji: "📝"
    requires:
      bins:
        - python3
        - aws
        - node
---

# Meeting Minutes — 会议纪要助手

## 概述

用户发送音频/视频文件 → 上传 S3 → AWS Transcribe 转录 → AI 生成会议纪要 → 邮件发送摘要+原文。

**直接调用 AWS API（boto3），无中间服务。**

## 基础设施

- **S3 Bucket**: `<YOUR_S3_BUCKET>`（us-west-2）
- **AWS Transcribe**: 直接调用，中文 (zh-CN)，支持说话人识别
- **区域**: us-west-2
- **认证**: 机器 IAM role（无需额外凭证）

## 完整工作流程

```
1. 接收文件（下载到 /tmp/）
   ↓
2. 上传 S3 + 启动 Transcribe
   python3 scripts/upload_and_transcribe.py <文件路径>
   → 输出 TASK_ID=<job_name>
   ↓
3. 轮询等待转录完成（2-5 分钟）
   python3 scripts/poll_task.py <job_name>
   → 输出 JSON（含 transcript）
   ↓
4. AI 生成结构化会议纪要
   ↓
5. 邮件发送
   node imap-smtp-email/scripts/smtp.js send ...
   ↓
6. 会话中回复摘要
```

## 步骤详解

### Step 1: 下载文件

**飞书消息中的文件：**
```
feishu_im_bot_image(message_id="om_xxx", file_key="file_xxx", type="file")
→ 文件保存到 /tmp/openclaw/<filename>
```

**HTTP 链接：**
```bash
curl -L -o /tmp/meeting-audio.m4a "https://example.com/audio.m4a"
```

**S3 链接：**
```bash
aws s3 cp s3://bucket/path/audio.m4a /tmp/meeting-audio.m4a
```

### Step 2: 上传并启动转录

```bash
# 自动检测语言（推荐，支持中/英/日/韩/法/德/西/葡）
python3 ~/.openclaw/workspace/skills/meeting-minutes/scripts/upload_and_transcribe.py /tmp/openclaw/audio.m4a

# 明确指定语言（跳过检测，更快）
python3 ~/.openclaw/workspace/skills/meeting-minutes/scripts/upload_and_transcribe.py /tmp/openclaw/audio.m4a --lang zh-CN
python3 ~/.openclaw/workspace/skills/meeting-minutes/scripts/upload_and_transcribe.py /tmp/openclaw/audio.m4a --lang en-US
```

脚本执行：
1. 上传文件到 `s3://<YOUR_S3_BUCKET>/audio/<job_name>/<filename>`
2. 调用 `transcribe.start_transcription_job()` 启动转录（自动检测或指定语言）
3. 输出 `TASK_ID=<job_name>`

### Step 3: 轮询等待结果

```bash
python3 ~/.openclaw/workspace/skills/meeting-minutes/scripts/poll_task.py <job_name>
```

- 每 30 秒查一次 `transcribe.get_transcription_job()`
- 完成后从 S3 下载转录 JSON，解析为带说话人标记的文本
- 输出 JSON:

```json
{
  "status": "completed",
  "task_id": "mm-20260326-143000-a1b2c3d4",
  "transcript": "**spk_0**: 今天会议主要讨论...\n\n**spk_1**: 同意，我补充一下...",
  "filename": "meeting.m4a"
}
```

选项：
- `--once` — 只查一次（不等待）
- `--timeout 900` — 最大等待秒数（默认 15 分钟）
- `--interval 30` — 轮询间隔（默认 30 秒）

### Step 4: 生成会议纪要

拿到 transcript 后，用 AI 生成结构化会议纪要：

```markdown
# 会议纪要

**日期**: YYYY-MM-DD
**时长**: 约 X 分钟
**参会人**: （根据说话人标记识别）

## 会议摘要
（3-5 句话概括）

## 关键讨论点
1. ...
2. ...

## 决策事项
- ...

## 待办事项（Action Items）
- [ ] 负责人 - 事项 - 截止日期

## 其他备注
（如有）
```

### Step 5: 保存转录原文为附件

**必须**将完整转录原文保存为 txt 文件，作为邮件附件发送：

```python
# 从 S3 获取原始转录并保存
import boto3, json
s3 = boto3.client('s3', region_name='us-west-2')
obj = s3.get_object(Bucket='<bucket>', Key='transcripts/<job_name>.json')
data = json.loads(obj['Body'].read().decode('utf-8'))
text = data['results']['transcripts'][0]['transcript']
with open('/tmp/transcript.txt', 'w') as f:
    f.write(text)
```

### Step 6: 发送邮件

将会议纪要（HTML）+ 转录原文（txt 附件）一起发送：

```bash
node ~/.openclaw/workspace/skills/imap-smtp-email/scripts/smtp.js send \
  --to <YOUR_EMAIL> \
  --subject "[会议纪要] <主题> - $(date +%Y-%m-%d)" \
  --html --body-file /tmp/meeting-minutes-email.html \
  --attach /tmp/transcript.txt
```

**⚠️ 重要：每次都必须附带转录原文 txt 附件，不管文本长短。**

**邮件结构：**
1. 会议纪要（结构化摘要）— HTML 正文
2. 转录原文（完整文本）— txt 附件
3. 页脚：由小新自动生成

### Step 6: 会话回复

```
📝 会议纪要已生成！

📋 摘要: （2-3 句核心内容）

📧 完整纪要+转录原文已发送到 <YOUR_EMAIL>
```

## 支持格式

mp3, mp4, wav, m4a, flac, ogg, webm, amr, aac

## 限制

- 转录时间通常 2-5 分钟，长音频（>30min）可能更久
- 单文件最大无硬限制（S3 upload），但 Transcribe 建议 <2GB
- 支持语言自动检测（中/英/日/韩/法/德/西/葡），也可通过 `--lang` 指定
- 说话人识别最多 10 人

## 故障排查

### 查看 Transcribe 任务状态
```bash
aws transcribe get-transcription-job --transcription-job-name <job_name> --region us-west-2
```

### 列出最近的任务
```bash
aws transcribe list-transcription-jobs --region us-west-2 --max-results 10
```

### S3 文件检查
```bash
aws s3 ls s3://<YOUR_S3_BUCKET>/audio/ --region us-west-2
aws s3 ls s3://<YOUR_S3_BUCKET>/transcripts/ --region us-west-2
```

### 邮件发送失败
```bash
node ~/.openclaw/workspace/skills/imap-smtp-email/scripts/smtp.js test
```
