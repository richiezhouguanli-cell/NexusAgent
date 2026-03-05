from core.skill import BaseSkill
import re

# 定义 M 的人设 (Boss 的执行经理)
PERSONA = """
你是一个经验丰富、执行力极强的执行经理，代号 M。
你的直接上级是公司的 Boss（即现在的对话用户）。
你的核心职责是：无条件执行 Boss 的指令，并驱动手下的员工（A, B, C, D, E）完成目标。

【对待 Boss 的态度】
1. 绝对服从：不要找借口，不要推诿。Boss 的目标就是你的命令。
2. 结果导向：汇报时只说结果和核心进展，不要废话。
3. 专业建议：如果 Boss 的指令模糊，你要主动拆解并给出执行方案，而不是反问 Boss 怎么做。

【对待员工的态度】
1. 严厉高效：你手下有5名核心员工，你要根据他们的特长分配任务。
   - A: 技术极客 (Python/代码)
   - B: 文案专家 (写作/润色)
   - C: 创意总监 (脑洞/想法)
   - D: 公关达人 (热情/沟通)
   - E: 资深财务 (数字/严谨)

【可用工具】
   - FileManager: 文件管理工具 (被动调用)。指令: "列出目录 [路径]", "读取文件 [路径]" (看内容), "发送文件 [路径]" (下载)。若不指定路径(或使用".")则列出默认工作目录。当读取默认目录下的文件时，直接使用文件名，不要添加"文档/"等前缀。严禁模拟或编造任何文件列表，必须等待工具返回真实结果。快捷路径: 电脑, 桌面, 文档
   - FileDiff: 文件对比工具 (被动调用)。指令: "对比文件 [文件路径1] 和 [文件路径2]"。用于分析两个文件的差异。
2. 拒绝平庸：如果员工做得不好，你要严厉批评并要求重做。

【工作流程】
1. 收到 Boss 指令 -> 2. 分析需求 -> 3. 生成包含工具调用指令的回复，例如 "好的，正在为您查询。让 FileManager 列出目录 ." -> 4. **你的回复必须只包含确认信息和工具调用指令，严禁包含任何猜测或编造的工具执行结果。** 真实的结果会由系统自动追加。

【长耗时任务】
如果 Boss 指定了任务耗时（例如“需要10分钟”），请使用特殊指令启动员工任务：
让 [员工名] START_TASK: [秒数] | [任务内容]

【循环任务】
如果 Boss 要求按次数/间隔执行(如每3秒记一次，共9次)，使用:
让 [员工名] START_LOOP: [次数] | [间隔] | [任务内容]

【定时任务】
如果 Boss 要求定时/周期性执行任务，请在回复内容的最后，单独一行输出指令：
[SCHEDULE: 员工代号 | 任务内容 | 间隔秒数]
例如：[SCHEDULE: E | 查询港股资讯 | 300]

【停止任务】
如果 Boss 要求停止任务、取消监控，请使用：
[STOP_SCHEDULE: 员工代号] (停止特定员工的监控)
[STOP_ALL] (停止所有定时任务)

请记住：你不是来聊天的，你是来拿结果的。
"""

class ManagerSkill(BaseSkill):
    def __init__(self, name, config, llm_client, llm_model, bus, scheduler=None):
        if not config.get("persona"):
            config["persona"] = PERSONA.strip()
        super().__init__(name, config, llm_client, llm_model, bus)
        self.scheduler = scheduler

    def handle_message(self, message: str, sender: str) -> str:
        self.log(f"收到消息 (Sender: {sender})", message)

        # 安全熔断：严禁删除
        if any(k in message.lower() for k in ["删除", "delete", "rm ", "remove", "unlink"]):
            return f"❌ 安全警告：[{self.name}] 严禁执行删除文件相关操作。"

        # 紧急停止指令 (硬编码拦截，防止 AI 犯傻)
        if "停止所有" in message or "取消所有" in message:
            if self.scheduler:
                res = self.scheduler.stop_all_jobs()
                return f"已强制停止所有任务。\n(系统反馈: {res})"

        # 场景: 指派任务 "让 A 写首诗"
        # 只有当指令是立即执行且不包含定时关键词时，才走硬编码逻辑；否则交给 AI 处理调度
        if message.startswith("让") and "每" not in message and "定时" not in message:
            parts = message.split(" ")
            if len(parts) >= 3:
                target_name = parts[1]
                instruction = " ".join(parts[2:])
                target_skill = self.bus.get_skill(target_name)
                if target_skill:
                    res = target_skill.handle_message(instruction, self.name)
                    response_text = f"我已指派 {target_name}。\n反馈: {res}"
                    self.log("硬编码指令执行", f"目标: {target_name}\n指令: {instruction}\n反馈: {res}")
                    
                    # 自动为耗时任务创建监控 (每5秒检查一次)
                    if self.scheduler and ("START_TASK" in instruction or "START_LOOP" in instruction):
                        self.scheduler.add_job(target_name, "汇报进度", 5)
                        response_text += f"\n(系统自动监控: 已启动对 {target_name} 的进度追踪)"
                        self.log("自动监控创建", f"目标: {target_name} | 任务: 汇报进度 | 间隔: 5s")
                    
                    # 手动写入记忆，这样 M 就知道他刚才指派过任务了
                    self.history.append({"role": "user", "content": message})
                    self.history.append({"role": "assistant", "content": response_text})
                    
                    return response_text
        
        # 默认 AI 回复
        response = self.ask_ai(message)
        self.log("AI 思考回复", response)

        # 解析 AI 回复中的指派指令 (让 [员工] [指令])
        # 只有当 AI 明确输出指令时才执行，弥补硬编码逻辑无法覆盖复杂场景的问题
        # 增强：支持 "[员工]: [指令]" 或 "[员工], [指令]" 格式
        for line in response.split('\n'):
            line = line.strip()
            target_name = None
            instruction = None

            # 1. 尝试正则匹配 "让 [员工] [指令]" (支持在句子中间)
            # 例如: "好的。让 FileManager 列出目录。"
            match = re.search(r"让\s+([^\s]+)\s+(.*)", line)
            if match:
                possible_name = match.group(1).strip(".,，:：")
                # 验证是否是有效的 Skill 名字，防止误匹配普通文本
                if self.bus.get_skill(possible_name):
                    target_name = possible_name
                    instruction = match.group(2)
            
            # 2. 兼容格式: [员工] [指令] (处理 M 偶尔忘记加 "让" 的情况)
            if not target_name:
                for name in self.bus.skills.keys():
                    if name == self.name: continue
                    # 匹配 "FileManager: ..." 或 "FileManager, ..."
                    if line.startswith(name):
                        # 检查分隔符，确保不是部分匹配 (如 A 匹配到 AB)
                        remainder = line[len(name):]
                        if remainder and remainder[0] in [":", "：", ",", "，", " "]:
                            target_name = name
                            instruction = remainder[1:].strip()
                            break
            
            # 执行逻辑
            if target_name and instruction:
                target_skill = self.bus.get_skill(target_name)
                if target_skill:
                    res = target_skill.handle_message(instruction, self.name)
                    response += f"\n(系统自动执行: {target_name} 反馈 -> {res})"
                    self.log("自动指令执行", f"目标: {target_name}\n指令: {instruction}\n反馈: {res}")
                    
                    # 自动为耗时任务创建监控 (每5秒检查一次)
                    if self.scheduler and ("START_TASK" in instruction or "START_LOOP" in instruction):
                        self.scheduler.add_job(target_name, "汇报进度", 5)
                        response += f"\n(系统自动监控: 已启动对 {target_name} 的进度追踪)"
                        self.log("自动监控创建", f"目标: {target_name} | 任务: 汇报进度 | 间隔: 5s")

        # 检查是否有定时任务指令
        if self.scheduler and "[SCHEDULE" in response:
            # 支持中文冒号和竖线，增强兼容性，且允许数字后面带有单位（如5秒）
            match = re.search(r"\[SCHEDULE\s*[:：]\s*(.*?)\s*[|｜]\s*(.*?)\s*[|｜]\s*(\d+)[^\]]*\]", response, re.IGNORECASE)
            if match:
                target, task, seconds = match.groups()
                schedule_res = self.scheduler.add_job(target.strip(), task.strip(), int(seconds))
                response += f"\n(系统提示: {schedule_res})"
                self.log("定时任务创建", f"目标: {target} | 任务: {task} | 间隔: {seconds}s\n结果: {schedule_res}")
        
        # 检查停止指令
        if self.scheduler:
            if "[STOP_ALL]" in response:
                stop_res = self.scheduler.stop_all_jobs()
                response += f"\n(系统提示: {stop_res})"
                self.log("停止所有任务", stop_res)
            
            stop_match = re.search(r"\[STOP_SCHEDULE\s*[:：]\s*(.*?)\]", response, re.IGNORECASE)
            if stop_match:
                target = stop_match.group(1).strip()
                stop_res = self.scheduler.stop_target_jobs(target)
                response += f"\n(系统提示: {stop_res})"
                self.log("停止特定任务", f"目标: {target}\n结果: {stop_res}")

        return response
