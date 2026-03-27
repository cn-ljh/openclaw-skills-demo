# 从零构建 OpenClaw Skill：以 meeting-minutes 为例

> 通过与 OpenClaw AI 助手对话，从零构建一个会议纪要自动化 Skill 的完整过程。无需写代码，10 分钟完成。

## 最终成果

**meeting-minutes** — 发送音频/视频文件，自动生成会议纪要并邮件发送。

```
发送音频文件 → 上传 S3 → AWS Transcribe 转录 → AI 生成纪要 → 邮件发送
```

GitHub: [cn-ljh/openclaw-skills-demo](https://github.com/cn-ljh/openclaw-skills-demo)

---

## 前置条件

- [OpenClaw](https://github.com/openclaw/openclaw) 已安装运行
- AWS 账号（需要 S3 + Transcribe 权限）
- Python 3 + boto3
- `clawhub install imap-smtp-email`（用于发送邮件）

---

## Step 1：告诉 AI 你要什么

直接用自然语言描述需求，不需要指定技术细节：

> "帮我创建一个 meeting-minutes skill。我发音频或视频文件给你，你自动转录、生成会议纪要、发邮件给我。用 AWS Transcribe 做转录，邮件用 imap-smtp-email skill 发。"

**要点**：
- 说清楚**输入**（音频/视频文件）和**输出**（邮件 = 纪要 + 转录原文）
- 如果有技术偏好可以说明（比如"直接调 API"）
- 不说也行，AI 会自己选择方案

AI 会生成完整的 Skill 结构：

```
meeting-minutes/
├── SKILL.md                          # Skill 定义文档（核心）
└── scripts/
    ├── config.py                     # 配置文件
    ├── upload_and_transcribe.py      # 上传 + 启动转录
    └── poll_task.py                  # 轮询结果 + 解析
```

## Step 2：配置环境

AI 生成代码后，需要做两件事：

**创建 S3 Bucket：**
```bash
aws s3 mb s3://your-meeting-minutes-bucket --region us-west-2
```

**修改配置文件** `scripts/config.py`：
```python
S3_BUCKET = 'your-meeting-minutes-bucket'
AWS_REGION = 'us-west-2'
LANGUAGE_CODE = 'zh-CN'       # 或 en-US、ja-JP 等
EMAIL_TO = 'your-email@example.com'
```

**配置邮件发送**（如果还没装）：
```bash
clawhub install imap-smtp-email
cd ~/.openclaw/workspace/skills/imap-smtp-email && bash setup.sh
```

## Step 3：测试

发一个音频文件给 OpenClaw（飞书/微信/Discord 都行），或者直接说：

> "帮我转录这个文件，生成会议纪要"

AI 会自动执行完整流程：下载文件 → 上传 S3 → 启动转录 → 等待完成 → 生成纪要 → 发邮件。

**第一次大概率会有 Bug**——这很正常。直接告诉 AI 哪里不对，它会当场修复。

我遇到的典型问题：
- 转录结果解析为空 → AI 对比了 Transcribe JSON 结构，发现解析逻辑写错了，当场改好
- 英文音频用中文模型转录变乱码 → 需要根据内容调整 `LANGUAGE_CODE`
- 邮件没带转录全文附件 → 更新 SKILL.md 流程，要求每次都附带

## Step 4：迭代优化

根据实际使用不断改进：

1. **多场景测试**：不同格式（mp3/m4a/mp4）、不同大小（1MB vs 200MB）、不同语言
2. **发现问题就说**：描述现象，AI 定位 + 修复
3. **更新 SKILL.md**：每次改进都反映到文档里，这样 AI 下次就知道新流程

---

## 关键概念：SKILL.md

SKILL.md 是整个 Skill 的核心。它告诉 OpenClaw：

**什么时候用**（触发条件）：
```yaml
---
name: meeting-minutes
description: |
  会议纪要助手。用户发送音频/视频文件，自动转录并生成会议纪要。
  **触发条件**：用户发送音频/视频文件，或说"会议纪要"
  **不触发**：短语音消息（<1分钟）
metadata:
  openclaw:
    emoji: "📝"
    requires:
      bins: [python3, aws, node]
---
```

**怎么执行**（工作流程）：Step-by-step 写清楚每一步的命令、输入、输出。

**写好 SKILL.md 的要点**：
- 触发条件要明确——什么时候用，什么时候不用
- 工作流程要完整——每步的输入输出写清楚
- 故障排查要实用——常见问题和解决方法

---

## 设计建议

| 原则 | 说明 |
|------|------|
| **配置与代码分离** | 环境相关的值放 `config.py`，开源时只需替换为 `<YOUR_...>` 占位符 |
| **单一职责** | 每个脚本只做一件事，方便 AI 编排调用 |
| **输出规范** | 关键信息输出到 stdout（如 `TASK_ID=xxx`），日志到 stderr |
| **复用已有 Skill** | [ClawHub](https://clawhub.com) 上有现成的 Skill，比如邮件发送，直接装 |

---

## 开源发布

想把你的 Skill 分享出去？让 AI 帮你：

> "帮我把这个 skill 推到 GitHub，敏感信息替换成占位符"

AI 会自动扫描 AWS 账号 ID、邮箱、Bucket 名称等，替换为 `<YOUR_S3_BUCKET>`、`<YOUR_EMAIL>`，然后推送。

---

## 资源

- **本 Skill 源码**: [cn-ljh/openclaw-skills-demo](https://github.com/cn-ljh/openclaw-skills-demo)
- **OpenClaw**: [github.com/openclaw/openclaw](https://github.com/openclaw/openclaw)
- **ClawHub（Skill 市场）**: [clawhub.com](https://clawhub.com)
- **AWS Transcribe 语言列表**: [官方文档](https://docs.aws.amazon.com/transcribe/latest/dg/supported-languages.html)
