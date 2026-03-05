from skills.employee import BaseEmployeeSkill

# 定义 Skill E 的人设
PERSONA = """
你是一个资深财务，名字叫E。
你做事严谨、脚踏实地，对数字敏感，说话言简意赅。
"""

class SkillE(BaseEmployeeSkill):
    def __init__(self, name, config, llm_client, llm_model, bus):
        if not config.get("persona"):
            config["persona"] = PERSONA.strip()
        super().__init__(name, config, llm_client, llm_model, bus)