# NexusAgent

NexusAgent 是一个模块化、可扩展的 AI Agent 基础框架。它模拟了一个数字化团队，包含一名核心管理者（M）和多名拥有不同专长的员工（Skill A-E）。

框架支持多模型（Gemini, NVIDIA, OpenAI）、多渠道（命令行, 飞书/Lark），并具备强大的任务调度、后台执行和全链路日志记录能力。

## 🌟 核心能力

### 1. 多角色协同 (Multi-Agent Collaboration)
系统预设了清晰的上下级关系和角色分工：
*   **管理者 (M)**: 你的专属执行经理。负责接收指令、拆解任务、指派员工、并监督任务进度。
*   **专业员工**:
    *   **A (技术极客)**: 擅长代码与技术实现。
    *   **B (文案专家)**: 擅长写作与润色。
    *   **C (创意总监)**: 提供脑洞与创意。
    *   **D (公关达人)**: 负责对外沟通与氛围。
    *   **E (资深财务)**: 处理数据与严谨逻辑。

### 2. 智能任务编排与执行
*   **长耗时任务后台执行**: 员工可以在后台线程中执行耗时任务（如写代码、查数据），不阻塞主对话。
    *   *指令示例*: "让 A 写一个贪吃蛇游戏，需要 30 秒"
*   **循环与周期任务**: 支持 "每隔X秒执行一次，共Y次" 的循环逻辑，支持实时记录中间结果。
    *   *指令示例*: "让 E 每隔 3 秒记录一次数据，执行 5 次"
*   **自动进度监控**: M 指派任务后，会自动创建定时监视器，定期询问员工进度并反馈给用户。当任务完成后，监控自动停止。

### 3. 多模型支持 (Multi-LLM)
框架内置 `LLMFactory`，支持无缝切换底层大模型，并支持配置回退策略：
*   **NVIDIA AI Foundation Models**: 支持 Llama 3 等高性能开源模型（推荐）。
*   **Google Gemini**: 性价比高，作为默认或回退模型。
*   **OpenAI**: 支持原生 GPT 接口。

### 4. 多渠道接入
*   **命令行 (Console)**: 开发调试模式，直接在终端交互。
*   **飞书 (Feishu/Lark)**: 集成 Webhook 和发消息 API。
    *   支持接收飞书消息（私聊/群聊）。
    *   支持将定时任务进度和最终结果主动推送到飞书。

### 5. 全链路日志 (Logging)
所有操作（用户指令、AI 思考、后台任务结果、定时汇报）都会自动记录到 `logs/` 目录下，按日期和角色归档，确保工作有据可查。

## 🚀 快速开始

### 1. 环境准备
*   Python 3.8+
*   API Key (建议申请 NVIDIA 或 Gemini Key)

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