# OpenClaw Skills Demo

A collection of [OpenClaw](https://github.com/openclaw/openclaw) skills for common automation tasks.

## Skills

### 📝 meeting-minutes

**会议纪要助手** — 音频/视频转录 + AI 会议纪要生成 + 邮件发送

将录音文件自动转录为文字，通过 AI 生成结构化会议纪要，并将纪要和原文发送到指定邮箱。

**工作流程：**

```
用户发送音频文件 → 上传 S3 → AWS Transcribe 转录 → AI 生成会议纪要 → 邮件发送
```

**特性：**
- 🎙️ 支持多种音频格式（mp3, m4a, wav, flac, ogg, webm, amr, aac）
- 👥 自动识别多个说话人（最多 10 人）
- 🤖 AI 生成结构化纪要（摘要、讨论点、决策、待办事项）
- 📧 自动邮件发送（纪要 + 完整转录原文）
- ☁️ 直接调用 AWS API（boto3），无中间服务
- 🇨🇳 默认支持中文，可配置其他语言

**前置条件：**
- AWS 账号（需要 S3 + Transcribe 权限）
- Python 3 + boto3
- [imap-smtp-email skill](https://clawhub.com) — 从 ClawHub 安装：`clawhub install imap-smtp-email`

**快速开始：**

```bash
# 1. 复制到 OpenClaw workspace
cp -r meeting-minutes ~/.openclaw/workspace/skills/

# 2. 配置
vim ~/.openclaw/workspace/skills/meeting-minutes/scripts/config.py
# 填写: S3_BUCKET, AWS_REGION, EMAIL_TO

# 3. 创建 S3 Bucket
aws s3 mb s3://your-meeting-minutes-bucket --region us-west-2

# 4. 安装 Python 依赖
pip install boto3 requests

# 5. 使用
# 在飞书/微信中发送音频文件给 OpenClaw，自动触发
# 或手动运行：
python3 scripts/upload_and_transcribe.py /path/to/audio.m4a
python3 scripts/poll_task.py <task_id>
```

详细文档见 [meeting-minutes/SKILL.md](meeting-minutes/SKILL.md)

## 安装

将需要的 skill 目录复制到你的 OpenClaw workspace：

```bash
git clone https://github.com/cn-ljh/openclaw-skills-demo.git
cp -r openclaw-skills-demo/<skill-name> ~/.openclaw/workspace/skills/
```

## 配置说明

每个 skill 都有独立的配置文件，**首次使用前必须根据你的环境修改配置**。配置文件中以 `<YOUR_...>` 开头的值是占位符，需要替换为实际值。

## 📖 如何从零构建 Skill

想了解这个 Skill 是怎么通过与 AI 对话、从零构建出来的？

👉 [从零构建 OpenClaw Skill：以 meeting-minutes 为例](docs/building-meeting-minutes-skill.md)

涵盖完整的对话过程、设计决策、Bug 修复、测试验证和开源发布流程。

## License

MIT
