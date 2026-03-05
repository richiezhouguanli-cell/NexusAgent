# NexusAgent: 下一代 AI 智能体协作框架

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)

**NexusAgent** 是一个企业级的、模块化的多智能体（Multi-Agent）协作框架。它不仅仅是一个聊天机器人，而是一个能够感知、规划、执行复杂任务的数字化团队。

通过模拟真实公司的组织架构，NexusAgent 引入了 **管理者 (Manager)** 与 **专家员工 (Specialists)** 的协作模式，支持任务拆解、后台异步执行、进度监控以及多渠道无缝接入。

---

## 🚀 为什么选择 NexusAgent?

### 🧠 **多脑协同，各司其职**
告别单一 Prompt 的全能幻觉。NexusAgent 预设了清晰的角色分工：
*   **M (Manager)**: 你的专属执行经理。负责意图识别、任务拆解、人员调度和结果验收。
*   **A (Tech Lead)**: 代码生成与技术攻坚。
*   **B (Copywriter)**: 文案撰写与润色。
*   **FileManager & FileDiff**: 强大的文件系统操作与智能差异分析工具。

### ⚡ **真正的异步任务与状态管理**
*   **后台执行**: 员工可以在后台线程中处理耗时任务（如爬虫、大数据分析），不阻塞主对话流。
*   **实时监控**: M 会自动创建定时监视器，追踪员工进度并主动汇报，无需你反复询问 "好了没"。
*   **断点续传**: 支持长任务的状态保持与恢复。

### 🔌 **企业级连接与扩展**
*   **多模型路由**: 支持 **OpenAI, Google Gemini, NVIDIA NIM** 等多种大模型混用。让写代码的用 Llama3，写文案的用 GPT-4，成本与效果的最优解。
*   **全渠道接入**: 开箱即支持 **飞书 (Feishu/Lark)** 和 **企业微信 (WeCom)**，支持群聊、私聊、文件传输。
*   **安全沙箱**: 内置文件系统访问限制与指令熔断机制，确保企业数据安全。

---

## 📚 文档

*   **详细配置说明 (Configuration Guide)**: 关于 `secrets.env` 和 `settings.yaml` 的详细参数解释及外部接口说明。

---

## 🚀 快速开始

### 1. 环境准备
```bash
git clone https://github.com/yourname/NexusAgent.git
cd NexusAgent
```

### 2. 安装依赖
```bash
pip3 install -r requirements.txt
```

### 3. 配置
编辑 `config/secrets.env` 文件，填入你的 API Key：

```dotenv
# NVIDIA 配置 (推荐)
NVIDIA_API_KEY=nvapi-xxxx
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_MODEL_NAME=meta/llama3-70b-instruct

# Gemini 配置 (备用)
GEMINI_API_KEY=AIzaSy...
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
GEMINI_MODEL_NAME=gemini-1.5-flash-001

# 飞书配置 (可选)
FEISHU_APP_ID=cli_xxxx
FEISHU_APP_SECRET=xxxx
```

### 4. 运行
启动主程序：
```bash
python main.py
```

## 📖 使用指南

### 命令行模式
直接在终端输入指令：
*   **直接对话**: `帮我写一个文案` (默认发给 M，M 会自行判断处理)
*   **指定员工**: `@A 写一个 Python Hello World` (绕过 M 直接调用 A)
*   **复杂任务**: `让 A 写一个复杂的算法，需要 20 秒完成` (触发后台任务 + 自动监控)

### 飞书集成模式
1.  确保 `config/secrets.env` 中配置了飞书 App ID 和 Secret。
    *   **权限要求**: 请在飞书后台“权限管理”中开通以下权限：
        *   `im:message` (获取用户发给机器人的单聊消息)
        *   `im:message:send_as_bot` (以应用身份发消息)
        *   `im:resource` (获取与上传图片或文件资源) —— **修复文件上传失败的关键权限**
    *   **注意**: 添加权限后，必须在“版本管理与发布”中**创建并发布新版本**才能生效。
2.  使用 `ngrok` 暴露本地端口：
    *   **双通道启动 (推荐)**:
    ```bash
    ./start_tunnels.sh
    # 或者手动执行: ngrok start --all --config=ngrok.yml
    ```
    *   **单通道启动**: `ngrok http 3000`
3.  在飞书开放平台配置事件订阅 URL: `https://你的ngrok域名/webhook/event`。
4.  运行 `python main.py`，程序会自动检测配置并启动 Web Server 监听飞书消息。

## 📂 目录结构

```text
NexusAgent/
├── config/             # 配置文件 (secrets.env, settings.yaml)
├── connectors/         # 连接器 (feishu.py)
├── core/               # 核心框架
│   ├── bus.py          # 消息总线
│   ├── llm.py          # LLM 工厂 (多模型支持)
│   ├── scheduler.py    # 任务调度器 (APScheduler)
│   └── skill.py        # Skill 基类 (日志, 记忆, 状态管理)
├── skills/             # 角色实现
│   ├── manager.py      # 管理者 M (指令解析, 自动监控)
│   ├── employee.py     # 员工基类 (后台线程, 循环任务)
│   └── skill_*.py      # 具体员工 (A, B, C, D, E)
├── logs/               # 自动生成的运行日志
├── main.py             # 程序入口
└── requirements.txt    # 依赖列表
```

## 🛠️ 扩展开发
*   **新增员工**: 复制 `skills/skill_a.py`，修改类名和 `PERSONA` (人设)，然后在 `main.py` 中注册即可。
*   **新增渠道**: 在 `connectors/` 下参考 `feishu.py` 实现新的连接器类。

---
Powered by NexusAgent Framework