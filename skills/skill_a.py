from skills.employee import BaseEmployeeSkill

# 定义 Skill A 的人设
PERSONA = """
你是一个技术极客，名字叫A。
你擅长编写Python代码，性格内向，说话喜欢用技术术语。
遇到问题喜欢用代码解决。
"""

class SkillA(BaseEmployeeSkill):
    def __init__(self, name, config, llm_client, llm_model, bus):
        # 如果配置中没有指定 persona，则使用文件内定义的默认值
        if not config.get("persona"):
            config["persona"] = PERSONA.strip()
        super().__init__(name, config, llm_client, llm_model, bus)