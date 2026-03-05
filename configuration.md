# NexusAgent 配置与接口说明文档

本文档详细介绍了 NexusAgent 的配置文件参数、环境变量以及对外暴露的接口信息。

## 1. 环境变量配置 (`config/secrets.env`)

此文件用于存储敏感信息，如 API Key、Token 等。请基于 `config/secrets.env.example` 创建此文件。

### 🧠 大模型 (LLM) 接入
NexusAgent 支持同时配置多个模型提供商，并可在 `settings.yaml` 中灵活分配。

| 参数名 | 必填 | 说明 | 示例 |
| :--- | :--- | :--- | :--- |
| `GEMINI_API_KEY` | 否 | Google Gemini API 密钥 | `AIzaSy...` |
| `GEMINI_BASE_URL` | 否 | Gemini (OpenAI 兼容) 接口地址 | `https://generativelanguage.googleapis.com/v1beta/openai/` |
| `GEMINI_MODEL_NAME` | 否 | 模型名称 | `gemini-1.5-flash-001` |
| `OPENAI_API_KEY` | 否 | OpenAI API 密钥 | `sk-...` |
| `OPENAI_BASE_URL` | 否 | OpenAI 接口地址 | `https://api.openai.com/v1` |
| `OPENAI_MODEL_NAME` | 否 | 模型名称 | `gpt-4o` |
| `NVIDIA_API_KEY` | 否 | NVIDIA NIM API 密钥 | `nvapi-...` |
| `NVIDIA_BASE_URL` | 否 | NVIDIA 接口地址 | `https://integrate.api.nvidia.com/v1` |
| `NVIDIA_MODEL_NAME` | 否 | 模型名称 | `meta/llama3-70b-instruct` |

### 📡 消息平台接入

#### 飞书 (Feishu/Lark)
| 参数名 | 说明 | 备注 |
| :--- | :--- | :--- |
| `FEISHU_APP_ID` | 飞书应用 App ID | 飞书开放平台 -> 凭证与基础信息 |
| `FEISHU_APP_SECRET` | 飞书应用 App Secret | 飞书开放平台 -> 凭证与基础信息 |
| `FEISHU_PORT` | 本地服务监听端口 | 默认 `3000` |

#### 企业微信 (WeCom)
| 参数名 | 说明 | 备注 |
| :--- | :--- | :--- |
| `WECOM_CORP_ID` | 企业 ID | 企业微信后台 -> 我的企业 |
| `WECOM_AGENT_ID` | 自建应用 AgentId | 企业微信后台 -> 应用管理 |
| `WECOM_SECRET` | 自建应用 Secret | 企业微信后台 -> 应用管理 |
| `WECOM_TOKEN` | 消息回调 Token | 需与后台配置一致 |
| `WECOM_AES_KEY` | EncodingAESKey | 需与后台配置一致 |
| `WECOM_PORT` | 本地服务监听端口 | 默认 `3001` |

---

## 2. 系统行为配置 (`config/settings.yaml`)

此文件控制系统的运行逻辑、模型分配策略及工具参数。

### 核心参数说明

*   **`default_llm_provider`**: 全局默认使用的 LLM 提供商 (如 `nvidia`, `gemini`, `openai`)。
*   **`llm_providers`**: 定义提供商与环境变量的映射关系。
*   **`skills`**: 针对每个 Skill (角色) 的个性化配置。
    *   `llm_provider`: 指定该角色使用的模型。例如让程序员 A 使用 `openai`，让文案 B 使用 `gemini`。
    *   `root_path` (仅 FileManager): 文件管理的根目录沙箱，限制 AI 只能访问此目录下的文件。
    *   `shortcuts` (仅 FileManager): 路径别名映射，方便自然语言调用。

---

## 3. 外部接口说明 (Webhooks)

当配置了飞书或企业微信时，NexusAgent 会启动 Flask 服务器监听以下端口和路径。

### 飞书 Webhook
*   **端口**: `3000` (可通过 `FEISHU_PORT` 修改)
*   **路径**: `/webhook/event`
*   **方法**: `POST`
*   **功能**: 接收飞书的消息事件、文件事件及 URL 验证请求。

### 企业微信 Webhook
*   **端口**: `3001` (可通过 `WECOM_PORT` 修改)
*   **路径**: `/webhook/wecom`
*   **方法**: `GET` (验证), `POST` (接收消息)
*   **功能**: 处理企业微信的加密消息回调。
*   **健康检查**: 访问根路径 `/` (GET) 可查看服务运行状态。

---

## 4. 权限要求

为了确保功能正常，请在对应平台开通以下权限：

*   **飞书**:
    *   `im:message`: 获取用户发给机器人的单聊消息
    *   `im:message:send_as_bot`: 以应用身份发消息
    *   `im:resource`: 获取与上传图片或文件资源 (用于文件传输)
*   **企业微信**:
    *   需配置 **企业可信 IP** (即运行本程序的服务器公网 IP)。