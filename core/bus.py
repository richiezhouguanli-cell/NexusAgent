class EventBus:
    """简单的消息总线，用于 Skill 查找和通信"""
    def __init__(self):
        self.skills = {}

    def register_skill(self, skill):
        self.skills[skill.name] = skill

    def get_skill(self, name: str):
        return self.skills.get(name)

    def broadcast(self, message: str, sender: str):
        results = {}
        for name, skill in self.skills.items():
            if name != sender:
                results[name] = skill.handle_message(message, sender)
        return results
