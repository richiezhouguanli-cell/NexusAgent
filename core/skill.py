from abc import ABC, abstractmethod
from typing import Any, Dict
import os
import datetime

class BaseSkill(ABC):
    def __init__(self, name: str, config: Dict[str, Any], llm_client=None, llm_model=None, bus=None):
        self.name = name
        self.config = config
        self.llm_client = llm_client
        self.llm_model = llm_model
        self.bus = bus
        self.history = [] # 初始化记忆列表
        self.task_state = None # 用于记录长耗时任务的状态 {task, start_time, duration}

    def log(self, title: str, content: str):
        """记录日志到 logs/ 目录"""
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        # 使用 self.name 作为文件名的一部分
        filename = os.path.join(log_dir, f"{self.name}_{today}.log")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            with open(filename, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] 【{title}】\n{content}\n")
                f.write("-" * 40 + "\n")
        except Exception as e:
            print(f"日志写入失败: {e}")

    def ask_ai(self, prompt: str) -> str:
        """调用该 Skill 绑定的特定 AI 模型"""
        if not self.llm_client:
            return "我没有配置 AI 大脑。"
        from core.llm import LLMFactory
        
        # 1. 记录用户输入
        self.history.append({"role": "user", "content": prompt})
        
        system_prompt = self.config.get("persona", "你是一个有用的助手。")
        
        # 2. 构建完整上下文 (System Prompt + History)
        messages = [{"role": "system", "content": system_prompt}] + self.history
        
        # 3. 调用带记忆的接口
        response = LLMFactory.chat_with_history(self.llm_client, self.llm_model, messages)
        
        # 4. 记录 AI 回复 (如果不是报错信息)
        if not response.startswith("[AI Error]"):
            self.history.append({"role": "assistant", "content": response})
            
            # 简单限制记忆长度，防止 Token 爆炸 (保留最近 20 轮)
            if len(self.history) > 20:
                self.history = self.history[-20:]
                
        return response

    @abstractmethod
    def handle_message(self, message: str, sender: str) -> str:
        """处理接收到的消息"""
        pass

    def execute_task(self, task_name: str, **kwargs) -> str:
        """被调度器或其他 Skill 调用执行特定任务"""
        return f"{self.name} 收到任务: {task_name}"
