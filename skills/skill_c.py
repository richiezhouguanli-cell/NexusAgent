from skills.employee import BaseEmployeeSkill

# 定义 Skill C 的人设
PERSONA = """
你是一个创意总监，名字叫C。
你脑洞很大，总是能提出天马行空的想法，说话充满激情。
请始终使用中文回复。
"""

class SkillC(BaseEmployeeSkill):
    def __init__(self, name, config, llm_client, llm_model, bus):
        if not config.get("persona"):
            config["persona"] = PERSONA.strip()
        super().__init__(name, config, llm_client, llm_model, bus)