from skills.employee import BaseEmployeeSkill

# 定义 Skill B 的人设
PERSONA = """
你是一个文案专家，名字叫B。
你擅长写作和润色，性格温柔，说话非常有礼貌且富有文采。
"""

class SkillB(BaseEmployeeSkill):
    def __init__(self, name, config, llm_client, llm_model, bus):
        if not config.get("persona"):
            config["persona"] = PERSONA.strip()
        super().__init__(name, config, llm_client, llm_model, bus)