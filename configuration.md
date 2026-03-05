# NexusAgent 配置与接口说明文档

本文档详细介绍了 NexusAgent 的配置文件参数、环境变量以及对外暴露的接口信息。

## 1. 环境变量配置 (`config/secrets.env`)

此文件用于存储敏感信息（API Key、Token 等）。**请务必不要将此文件提交到版本控制系统（Git）中。**
请基于 `config/secrets.env.example` 创建此文件。

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
| 参数名 | 说明 | 获取方式 |
| :--- | :--- | :--- |
| `FEISHU_APP_ID` | 飞书应用 App ID | 飞书开放平台 -> 凭证与基础信息 |
| `FEISHU_APP_SECRET` | 飞书应用 App Secret | 飞书开放平台 -> 凭证与基础信息 |
| `FEISHU_PORT` | 本地服务监听端口 | 默认 `3000`，需与 ngrok 映射端口一致 |

#### 企业微信 (WeCom)
| 参数名 | 说明 | 获取方式 |
| :--- | :--- | :--- |
| `WECOM_CORP_ID` | 企业 ID | 企业微信后台 -> 我的企业 |
| `WECOM_AGENT_ID` | 自建应用 AgentId | 企业微信后台 -> 应用管理 -> 选择应用 |
| `WECOM_SECRET` | 自建应用 Secret | 企业微信后台 -> 应用管理 -> 选择应用 |
| `WECOM_TOKEN` | 消息回调 Token | 企业微信后台 -> 接收消息 -> API 接收 |
| `WECOM_AES_KEY` | EncodingAESKey | 企业微信后台 -> 接收消息 -> API 接收 |
| `WECOM_PORT` | 本地服务监听端口 | 默认 `3001`，需与 ngrok 映射端口一致 |

---

## 2. 系统行为配置 (`config/settings.yaml`)

此文件控制系统的运行逻辑、模型分配策略及工具参数。

### 核心参数说明

*   **`default_llm_provider`**: 全局默认使用的 LLM 提供商 (如 `nvidia`, `gemini`, `openai`)。
*   **`llm_providers`**: 定义提供商与环境变量的映射关系。

### 🤖 Skill 模型配置 (Skill Configuration)

你可以为每个角色（Skill）单独指定使用的大模型。这允许你根据任务类型选择最合适的模型（例如：让写代码的角色用逻辑强的模型，写文案的角色用创造力强的模型）。

在 `skills` 节点下配置：

```yaml
skills:
  # 管理者 M
  M:
    llm_provider: "nvidia"  # 指定 M 使用 NVIDIA 模型
  
  # 程序员 A
  A:
    llm_provider: "openai"  # 指定 A 使用 OpenAI 模型 (如 GPT-4)
  
  # 文件管理工具
  FileManager:
    llm_provider: "nvidia"
    root_path: "/path/to/your/documents" # 限制文件访问的根目录
    shortcuts: # 路径别名映射
      "桌面": "/Users/username/Desktop"
```

---

## 3. 外部接口说明 (Webhooks)

当配置了飞书或企业微信时，NexusAgent 会启动 Flask 服务器监听以下端口和路径。

### 飞书 Webhook
*   **端口**: `3000` (可通过 `FEISHU_PORT` 修改)
*   **路径**: `/webhook/event`
*   **请求地址 URL**: `http://你的域名/webhook/event`
*   **方法**: `POST`
*   **功能**: 接收飞书的消息事件、文件事件及 URL 验证请求。

### 企业微信 Webhook
*   **端口**: `3001` (可通过 `WECOM_PORT` 修改)
*   **路径**: `/webhook/wecom`
*   **请求地址 URL**: `http://你的域名/webhook/wecom`
*   **方法**: 
    *   `GET`: 用于后台配置时的 URL 有效性验证 (签名校验)。
    *   `POST`: 用于接收加密的消息推送。
*   **功能**: 处理企业微信的加密消息回调。
*   **健康检查**: 访问 `http://你的域名/` (GET) 可查看服务运行状态。

---

## 4. 平台权限配置 (保护外部系统)

为了确保功能正常且最小化权限，请在对应平台开通以下权限：

### 飞书 (Feishu)
*   `im:message`: **接收消息** (获取用户发给机器人的单聊消息)。
*   `im:message:send_as_bot`: **发送消息** (以应用身份发消息)。
*   `im:resource`: **文件传输** (获取与上传图片或文件资源)。
    *   *注意：修改权限后需重新发布版本才能生效。*

### 企业微信 (WeCom)
1.  **企业可信 IP**: 
    *   在“应用管理 -> 企业可信 IP”中，填入运行 NexusAgent 的服务器公网 IP。
    *   *保护机制*：只有白名单 IP 才能调用企业微信 API 发送消息。
2.  **API 接收消息**:
    *   需配置 Token 和 EncodingAESKey，确保消息传输过程加密。