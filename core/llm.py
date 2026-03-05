import os
from openai import OpenAI

class LLMFactory:
    """
    LLM 工厂，用于根据配置生成不同的 AI 客户端。
    """
    @staticmethod
    def create_client(api_key: str, base_url: str, model_name: str):
        if not api_key:
            print(f"警告: API Key 为空，请检查 config/secrets.env")
        return OpenAI(api_key=api_key, base_url=base_url), model_name

    @staticmethod
    def simple_chat(client, model_name: str, system_prompt: str, user_input: str) -> str:
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            error_msg = str(e)
            if "unsupported_country_region_territory" in error_msg:
                return "[AI Error] 您的网络环境(IP)不被 OpenAI 支持(403)。请开启全局 VPN 或在 secrets.env 中更换国内大模型 Base URL。"
            if "429" in error_msg:
                return "[AI Error] 触发频率限制或配额不足 (429)。请稍后再试，或检查 API Key 配额。"
            return f"[AI Error] 调用失败: {error_msg}"

    @staticmethod
    def chat_with_history(client, model_name: str, messages: list) -> str:
        """支持上下文记忆的对话接口"""
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages
            )
            return response.choices[0].message.content
        except Exception as e:
            # 复用错误处理逻辑
            # 这里简单起见直接调用 simple_chat 里的逻辑，或者复制一份
            error_msg = str(e)
            if "unsupported_country_region_territory" in error_msg:
                return "[AI Error] 您的网络环境(IP)不被 OpenAI 支持(403)。请开启全局 VPN 或在 secrets.env 中更换国内大模型 Base URL。"
            if "429" in error_msg:
                return "[AI Error] 触发频率限制或配额不足 (429)。请稍后再试，或检查 API Key 配额。"
            return f"[AI Error] 调用失败: {error_msg}"
