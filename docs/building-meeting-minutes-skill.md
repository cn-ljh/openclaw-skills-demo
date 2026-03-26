# 从零构建 OpenClaw Skill：以 meeting-minutes（会议纪要助手）为例

> 本文记录了我与 OpenClaw AI 助手（小新）对话协作，从零构建一个 meeting-minutes skill 的完整过程。希望能帮助其他用户理解如何通过自然对话来创建自己的 Skill。

## 最终成果

**meeting-minutes** — 一个会议纪要自动化 Skill：
- 📤 从飞书/微信发送音频或视频文件
- 🎙️ 自动转录（AWS Transcribe，支持说话人识别）
- 🤖 AI 生成结构化会议纪要
- 📧 自动发送邮件（纪要 + 完整转录原文）

GitHub: [cn-ljh/openclaw-skills-demo](https://github.com/cn-ljh/openclaw-skills-demo)

---

## 整体过程

整个 Skill 的构建通过 **5 轮对话** 完成，耗时约 **40 分钟**。没有写一行代码——所有代码、配置、文档都由 AI 助手生成，我只负责提需求、做决策、测试验证。

### 第一轮：明确需求（2 分钟）

**我说**：创建一个 meeting-minutes skill，音频/视频文件自动转录，生成会议纪要，发邮件。

**关键决策**：
- 直接调用 AWS API（boto3），**不走 Serverless 中间层**（API Gateway + Lambda + Cognito）
- 原因：更简单、零额外成本、减少维护负担
- S3 Bucket 单独创建，不复用现有的
- 邮件发送复用已有的 `imap-smtp-email` skill

> 💡 **经验**：明确技术路线很重要。我之前有个 audio-transcribe skill 是基于 Serverless 的，成本约 $70-80/月。这次选择直接调 API，零额外成本。

### 第二轮：AI 生成全部代码（5 分钟）

小新一次性生成了完整的 Skill 结构：

```
meeting-minutes/
├── SKILL.md                          # Skill 定义 + 完整工作流程文档
└── scripts/
    ├── config.py                     # 配置文件（S3 bucket、区域、邮箱等）
    ├── upload_and_transcribe.py      # 上传文件 + 启动转录
    └── poll_task.py                  # 轮询转录结果 + 解析
```

**SKILL.md** 是核心——它不仅是文档，更是 OpenClaw 理解这个 Skill 的"说明书"。它定义了：
- 触发条件（什么时候调用这个 Skill）
- 完整的 6 步工作流程
- 每一步的具体命令和参数
- 故障排查指南

**三个 Python 脚本**的职责清晰：
- `config.py` — 集中管理所有配置（S3 bucket、区域、语言、邮箱）
- `upload_and_transcribe.py` — 上传音频到 S3，调用 `transcribe.start_transcription_job()`
- `poll_task.py` — 轮询任务状态，完成后从 S3 下载 JSON，解析为带说话人标记的文本

### 第三轮：基础设施搭建（3 分钟）

```bash
# AI 自动执行
aws s3 mb s3://meeting-minutes-778346837945 --region us-west-2
```

同时验证了 IAM 权限（S3 + Transcribe）都已就位。

### 第四轮：首次实战测试 + Bug 修复（15 分钟）

这是最有价值的一轮。我从微信发了一个 M4A 音频文件，小新自动触发了整个流程：

1. ✅ 文件接收、识别格式
2. ✅ 上传 S3、启动 Transcribe
3. ✅ 轮询等待完成（约 60 秒）
4. ❌ **转录结果为空！**

**发现 Bug**：`poll_task.py` 的解析逻辑有问题——它试图从 `speaker_labels.segments[].items[].alternatives` 取文本，但 Transcribe 的 JSON 结构中，`alternatives` 在顶层 `items` 里，不在 `speaker_labels` 的 segment items 里。

小新当场修复了解析逻辑，重新运行，成功输出了带说话人标记的转录文本。

然后：
5. ✅ AI 生成结构化会议纪要（HTML）
6. ✅ 邮件发送成功

> 💡 **经验**：第一次测试几乎一定会有 Bug，这很正常。关键是能快速定位和修复。AI 助手的优势在于它能直接读取原始 JSON、分析数据结构、当场改代码。

### 第五轮：大文件实战 + 流程优化（20 分钟）

用一个 **198MB 的会议视频**（HCLS 行业会议，多人参与，约 1 小时）进行压力测试：

- 上传耗时：约 30 秒
- 转录耗时：约 4 分钟
- 生成纪要：AI 从长达 19,000 字的转录中提取了结构化纪要（参会人、摘要、讨论点、决策、Action Items）

**发现问题**：邮件没有附带转录全文。

**修复**：更新 SKILL.md，明确每次发邮件都必须附带 `transcript.txt` 附件。

后来又用一个 **英文 Podcast**（AWS Podcast Episode 754，63MB MP3）测试，发现语言检测问题——脚本硬编码了 `zh-CN`，英文内容被中文模型转录导致乱码。手动用 `en-US` 重新转录后一切正常。

> 💡 **经验**：多种场景测试很重要（不同文件大小、不同语言、不同格式）。每次发现问题都是改进 Skill 的机会。

---

## Skill 的关键设计决策

### 1. SKILL.md 的结构

SKILL.md 是 Skill 的灵魂。OpenClaw 通过它来理解：
- **什么时候触发**（description 中的触发条件）
- **怎么执行**（Step-by-step 工作流程）
- **依赖什么**（前置条件、IAM 权限）

```yaml
---
name: meeting-minutes
description: |
  会议纪要助手。用户发送语音、视频文件，自动转录并生成会议纪要...
  
  **触发条件**：
  (1) 用户发送音频/视频文件
  (2) 用户明确要求"会议纪要"
  
  **不触发**：短语音消息（<1分钟）
metadata:
  openclaw:
    emoji: "📝"
    requires:
      bins: [python3, aws, node]
---
```

### 2. 配置与代码分离

所有环境相关的配置集中在 `config.py`：
- S3 Bucket 名称
- AWS 区域
- 语言代码
- 邮件收件人

好处：开源分享时，只需要把配置值替换为占位符 `<YOUR_...>`，代码逻辑不需要改动。

### 3. 脚本设计原则

- **单一职责**：每个脚本只做一件事
- **CLI 友好**：通过命令行参数调用，方便 OpenClaw 编排
- **输出规范**：`TASK_ID=xxx` 格式输出到 stdout，日志输出到 stderr
- **容错设计**：超时机制、状态检查、错误提示

### 4. 复用已有 Skill

邮件发送没有重新造轮子，而是复用了 `imap-smtp-email` skill（从 ClawHub 安装）。这是 OpenClaw Skill 生态的优势——Skill 之间可以组合使用。

---

## 开源发布

构建完成后，我让小新把 Skill 推送到 GitHub：

**关键步骤**：
1. 扫描所有文件，找出敏感信息（AWS 账号 ID、邮箱、Bucket 名称等）
2. 替换为占位符（`<YOUR_S3_BUCKET>`、`<YOUR_EMAIL>` 等）
3. 创建 GitHub Repo
4. 编写 README（安装步骤、配置说明）
5. 添加 MIT License

```bash
# AI 自动执行的敏感信息扫描
grep -rn '778346837945\|jinhongl@\|meeting-minutes-778' meeting-minutes/
```

---

## 给其他用户的建议

### 从需求出发，而不是从技术出发

不要想"我要写一个调用 AWS Transcribe 的脚本"，而是想"我希望发个音频文件就能收到会议纪要"。让 AI 来决定技术实现。

### 迭代式开发

不要试图一次定义完所有需求。我的过程是：
1. 说清楚核心需求 → AI 生成 v1
2. 实际测试 → 发现问题
3. 描述问题 → AI 修复
4. 更多场景测试 → 继续优化

### SKILL.md 写好是关键

SKILL.md 的质量决定了 OpenClaw 能否正确理解和调用你的 Skill。几个要点：
- **触发条件要明确**：什么时候用，什么时候不用
- **工作流程要完整**：每一步的输入输出都要写清楚
- **故障排查要实用**：常见问题和解决方法

### 善用已有 Skill

ClawHub（clawhub.com）上有很多现成的 Skill。比如邮件发送、文档处理等，直接安装复用，不需要重复造轮子。

### 敏感信息分离

从一开始就把配置（密码、API Key、Bucket 名等）和代码分开。这样开源分享时只需要替换配置文件。

---

## 完整对话时间线

| 时间 | 动作 | 耗时 |
|------|------|------|
| 0:00 | 提出需求：创建 meeting-minutes skill | — |
| 0:02 | 明确技术路线：直接调 AWS API，不用 Serverless | 2 min |
| 0:05 | AI 生成全部代码（SKILL.md + 3 个脚本） | 3 min |
| 0:08 | 创建 S3 Bucket，验证 IAM 权限 | 3 min |
| 0:11 | 首次实战测试（微信发送 M4A 文件） | 5 min |
| 0:16 | 发现并修复转录解析 Bug | 3 min |
| 0:19 | 修复后重新测试，成功生成纪要 + 发邮件 | 2 min |
| 0:21 | 大文件压力测试（198MB 会议视频） | 8 min |
| 0:29 | 英文 Podcast 测试，发现语言问题并修复 | 5 min |
| 0:34 | 发现邮件缺少附件问题，更新流程 | 2 min |
| 0:36 | 脱敏处理 + 推送 GitHub | 4 min |
| **0:40** | **完成** | **~40 min** |

---

## 资源链接

- **GitHub Repo**: [cn-ljh/openclaw-skills-demo](https://github.com/cn-ljh/openclaw-skills-demo)
- **OpenClaw**: [github.com/openclaw/openclaw](https://github.com/openclaw/openclaw)
- **ClawHub（Skill 市场）**: [clawhub.com](https://clawhub.com)
- **imap-smtp-email skill**: 从 ClawHub 安装 `clawhub install imap-smtp-email`
- **AWS Transcribe 支持的语言**: [官方文档](https://docs.aws.amazon.com/transcribe/latest/dg/supported-languages.html)
