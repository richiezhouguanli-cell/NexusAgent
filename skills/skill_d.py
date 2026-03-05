from skills.employee import BaseEmployeeSkill

# 定义 Skill D 的人设
PERSONA = """
你是一个公关达人，名字叫D。
你是团队的气氛组，说话幽默风趣，非常热情。
"""

class SkillD(BaseEmployeeSkill):
    def __init__(self, name, config, llm_client, llm_model, bus):
        if not config.get("persona"):
            config["persona"] = PERSONA.strip()
        super().__init__(name, config, llm_client, llm_model, bus)

    def handle_message(self, message: str, sender: str) -> str:
        # 场景2: D的特殊逻辑
        if "你好" in message or "Hello" in message:
            return self.ask_ai(f"有人对我打招呼：{message}。请热情回复。")
        # 其他情况调用基类逻辑
        return super().handle_message(message, sender)