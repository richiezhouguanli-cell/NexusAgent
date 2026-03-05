import os
import sys

# 定义项目结构和文件内容
project_structure = {
    "requirements.txt": """openai
python-dotenv
apscheduler
requests
colorama
""",
    ".gitignore": """__pycache__/
*.pyc
.env
.DS_Store
venv/
.idea/
""",
    "config/secrets.env": """# 在这里填入你的 API Key
OPENAI_API_KEY=sk-your-api-key-here
# 如果使用其他模型（如 DeepSeek/Moonshot），修改 Base URL
OPENAI_BASE_URL=https://api.openai.com/v1
""",
    "config/settings.yaml": """# 预留配置文件
system:
  name: NexusAgent
""",
    "core/__init__.py": "",
    "core/llm.py": """import os
from openai import OpenAI

class LLMFactory:
    \"\"\"
    LLM 工厂，用于根据配置生成不同的 AI 客户端。
    \"\"\"
    @staticmethod
    def create_client(api_key: str, base_url: str, model_name: str):
        if not api_key or "sk-" not in api_key:
            print(f"警告: API Key ({api_key}) 可能无效，请检查 config/secrets.env")
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
            return f"[AI Error] 调用失败: {str(e)}"
""",
    "core/bus.py": """class EventBus:
    \"\"\"简单的消息总线，用于 Skill 查找和通信\"\"\"
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
""",
    "core/skill.py": """from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseSkill(ABC):
    def __init__(self, name: str, config: Dict[str, Any], llm_client=None, llm_model=None, bus=None):
        self.name = name
        self.config = config
        self.llm_client = llm_client
        self.llm_model = llm_model
        self.bus = bus

    def ask_ai(self, prompt: str) -> str:
        \"\"\"调用该 Skill 绑定的特定 AI 模型\"\"\"
        if not self.llm_client:
            return "我没有配置 AI 大脑。"
        from core.llm import LLMFactory
        system_prompt = self.config.get("persona", "你是一个有用的助手。")
        return LLMFactory.simple_chat(self.llm_client, self.llm_model, system_prompt, prompt)

    @abstractmethod
    def handle_message(self, message: str, sender: str) -> str:
        \"\"\"处理接收到的消息\"\"\"
        pass

    def execute_task(self, task_name: str, **kwargs) -> str:
        \"\"\"被调度器或其他 Skill 调用执行特定任务\"\"\"
        return f"{self.name} 收到任务: {task_name}"
""",
    "core/scheduler.py": """from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import datetime
import logging

# 关闭 apscheduler 的繁琐日志
logging.getLogger('apscheduler').setLevel(logging.WARNING)

class TaskScheduler:
    def __init__(self, bus):
        self.scheduler = BackgroundScheduler()
        self.bus = bus
        self.scheduler.start()

    def add_job(self, skill_name: str, task_instruction: str, seconds: int):
        \"\"\"添加一个定时任务\"\"\"
        def job_function():
            skill = self.bus.get_skill(skill_name)
            if skill:
                print(f"\\n[⏰ 定时任务触发] {skill_name} 执行: {task_instruction}")
                result = skill.handle_message(task_instruction, "Scheduler")
                print(f"[✅ 任务结果] {result}\\n[用户] >>> ", end="", flush=True)
        
        job_id = f"{skill_name}_{datetime.datetime.now().timestamp()}"
        self.scheduler.add_job(
            job_function, 
            trigger=IntervalTrigger(seconds=seconds),
            id=job_id
        )
        return f"任务已创建：每 {seconds} 秒让 {skill_name} 执行 '{task_instruction}'"
""",
    "connectors/__init__.py": "",
    "connectors/console.py": """# 这里可以放置控制台交互逻辑的封装，目前直接写在 main.py 中方便调试
""",
    "skills/__init__.py": "",
    "skills/manager.py": """from core.skill import BaseSkill
import time

class ManagerSkill(BaseSkill):
    def handle_message(self, message: str, sender: str) -> str:
        # 场景1: M先生让5个员工依次报数
        if "报数" in message:
            return self.orchestrate_roll_call()
        
        # 场景: 指派任务 "让 小甲 写首诗"
        if message.startswith("让"):
            parts = message.split(" ")
            if len(parts) >= 3:
                target_name = parts[1]
                instruction = " ".join(parts[2:])
                target_skill = self.bus.get_skill(target_name)
                if target_skill:
                    res = target_skill.handle_message(instruction, self.name)
                    return f"我已指派 {target_name}。\\n反馈: {res}"
        
        # 默认 AI 回复
        return self.ask_ai(message)

    def orchestrate_roll_call(self):
        \"\"\"编排逻辑：联动其他 Skill\"\"\"
        employees = ["小甲", "小乙", "小丙", "小丁", "小戊"]
        results = ["\\n=== 开始报数 ==="]
        
        for emp_name in employees:
            emp = self.bus.get_skill(emp_name)
            if emp:
                # M先生直接调用员工 Skill
                response = emp.handle_message("报数", self.name)
                results.append(f"{response}")
                time.sleep(0.2) # 模拟间隔
            else:
                results.append(f"{emp_name} 缺勤")
        
        results.append("=== 报数完毕 ===")
        return "\\n".join(results)
""",
    "skills/employee.py": """from core.skill import BaseSkill

class EmployeeSkill(BaseSkill):
    def handle_message(self, message: str, sender: str) -> str:
        # 场景2: 单独当小丁说“你好”
        if self.name == "小丁" and "你好" in message:
            return self.ask_ai(f"有人对我打招呼：{message}。请热情回复。")
        
        # 场景1: 报数逻辑
        if "报数" in message:
            return f"[{self.name}] 到！"
        
        # 默认逻辑
        if sender == "M先生":
            return self.ask_ai(f"老板(M先生)对我说：{message}。请简短专业的回复。")
        
        return self.ask_ai(message)
""",
    "main.py": """import os
import sys
from dotenv import load_dotenv
from core.bus import EventBus
from core.llm import LLMFactory
from core.scheduler import TaskScheduler
from skills.manager import ManagerSkill
from skills.employee import EmployeeSkill

# 加载环境变量
load_dotenv("config/secrets.env")

def main():
    print("正在初始化 NexusAgent...")
    
    # 1. 初始化总线和调度器
    bus = EventBus()
    scheduler = TaskScheduler(bus)

    # 2. 配置 AI
    api_key = os.getenv("OPENAI_API_KEY", "sk-xxxx") 
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    
    # 这里使用 gpt-3.5-turbo 作为示例，你可以改为 gpt-4 或其他
    client, model = LLMFactory.create_client(api_key, base_url, "gpt-3.5-turbo")

    # 3. 初始化 Skills
    # M先生
    m_config = {"persona": "你是一个严厉但高效的管理者，名字叫M先生。"}
    m_mr = ManagerSkill("M先生", m_config, client, model, bus)
    bus.register_skill(m_mr)

    # 员工 (小甲到小戊)
    employees = ["小甲", "小乙", "小丙", "小丁", "小戊"]
    for name in employees:
        e_config = {"persona": f"你是一个勤奋的员工，名字叫{name}。"}
        emp = EmployeeSkill(name, e_config, client, model, bus)
        bus.register_skill(emp)

    print("\\n" + "="*40)
    print("🚀 NexusAgent 框架已启动")
    print("="*40)
    print("可用指令示例:")
    print("1. @M先生 所有人报数")
    print("2. @小丁 你好 (触发特定逻辑)")
    print("3. @M先生 让 小甲 写一首关于Python的诗 (Skill联动)")
    print("4. /schedule 小甲 报数 5 (每5秒执行一次)")
    print("5. exit (退出)")
    print("="*40)

    # 4. 主循环 (模拟通讯软件)
    while True:
        try:
            user_input = input("\\n[用户] >>> ").strip()
            if not user_input: continue
            if user_input.lower() in ["exit", "quit"]:
                print("再见！")
                break
            
            # 定时任务指令
            if user_input.startswith("/schedule"):
                parts = user_input.split()
                if len(parts) == 4:
                    _, target, task, sec = parts
                    print(scheduler.add_job(target, task, int(sec)))
                else:
                    print("格式错误。正确格式: /schedule [姓名] [任务] [秒数]")
                continue

            # 对话指令 (@某人 消息)
            if user_input.startswith("@"):
                parts = user_input.split(" ", 1)
                if len(parts) == 2:
                    target_name = parts[0][1:] # 去掉 @
                    msg = parts[1]
                    
                    skill = bus.get_skill(target_name)
                    if skill:
                        print(f"({target_name} 正在思考...)")
                        response = skill.handle_message(msg, "User")
                        print(f"[{target_name}] >>> {response}")
                    else:
                        print(f"❌ 系统: 找不到名为 {target_name} 的 Skill")
                else:
                    print("格式错误。请包含消息内容。")
            else:
                print("系统: 请指定对话对象，例如 '@M先生 报数'")

        except KeyboardInterrupt:
            print("\\n程序已停止。")
            break
        except Exception as e:
            print(f"发生错误: {e}")

if __name__ == "__main__":
    main()
"""
}

def create_project():
    base_dir = os.getcwd()
    print(f"正在当前目录 '{base_dir}' 生成 NexusAgent 项目结构...")

    for file_path, content in project_structure.items():
        full_path = os.path.join(base_dir, file_path)
        dir_name = os.path.dirname(full_path)
        
        # 创建目录
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name)
            print(f"  + 创建目录: {dir_name}")
        
        # 写入文件
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  - 生成文件: {file_path}")

    print("\n✅ 项目生成完毕！")
    print("\n接下来请执行以下命令开始使用：")
    print("1. pip3 install -r requirements.txt")
    print("2. 编辑 config/secrets.env 填入你的 API Key")
    print("3. python main.py")

if __name__ == "__main__":
    create_project()
