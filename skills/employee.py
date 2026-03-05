from core.skill import BaseSkill
import time
import threading
import os
import datetime

class BaseEmployeeSkill(BaseSkill):
    """员工通用基类"""
    
    def _run_task_background(self, task_prompt):
        """后台运行实际的 AI 任务 (线程函数)"""
        try:
            # 这里真正调用 AI，会消耗实际的时间
            result = self.ask_ai(f"请完成这项任务：{task_prompt}")
            # 任务完成后，将结果写入状态字典 (相当于写在文档里)
            self.task_state["status"] = "done"
            self.task_state["result"] = result
            
            # 记录日志
            self.log("反馈消息 (后台任务完成)", f"任务: {task_prompt}\n结果: {result}")
            
        except Exception as e:
            error_msg = str(e)
            self.task_state["status"] = "error"
            self.task_state["result"] = error_msg
            self.log("反馈消息 (后台任务出错)", f"任务: {task_prompt}\n错误: {error_msg}")

    def _run_loop_background(self, count, interval, task_prompt):
        """后台运行循环任务"""
        try:
            results = []
            for i in range(count):
                # 执行单次任务
                # 为了演示效果，这里我们让 AI 生成，或者你可以直接用 Python 生成
                # 这里使用 ask_ai 保持 Agent 特性
                step_res = self.ask_ai(f"请执行第 {i+1}/{count} 次操作: {task_prompt}。请严格按要求格式输出，不要废话。")
                
                # 记录结果
                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                # 如果 AI 没有返回时间戳，我们手动加一个方便观察
                if "[" not in step_res: 
                    step_res = f"[{timestamp}] {step_res}"
                
                results.append(step_res)
                self.task_state["intermediate_results"] = results # 实时更新中间结果
                self.log(f"反馈消息 (循环任务 {i+1}/{count})", f"任务: {task_prompt}\n结果: {step_res}")
                
                if i < count - 1:
                    time.sleep(interval)
            
            self.task_state["status"] = "done"
            self.task_state["result"] = "\n".join(results)
        except Exception as e:
            self.task_state["status"] = "error"
            self.task_state["result"] = str(e)

    def handle_message(self, message: str, sender: str) -> str:
        self.log(f"接收消息 (Sender: {sender})", message)

        # 安全熔断：严禁删除
        if any(k in message.lower() for k in ["删除", "delete", "rm ", "remove", "unlink"]):
            res = f"❌ 安全警告：[{self.name}] 严禁执行删除文件相关操作。"
            self.log("反馈消息 (安全拦截)", res)
            return res

        # --- 1. 处理任务启动指令 ---
        # 格式: START_TASK: [秒数] | [任务内容]
        if message.startswith("START_TASK:"):
            try:
                _, params = message.split(":", 1)
                # 兼容旧格式，虽然秒数不再决定执行时间，但为了不破坏 M 的指令格式，我们还是解析它
                if "|" in params:
                    _, task_content = params.split("|", 1)
                else:
                    task_content = params
                
                task_content = task_content.strip()
                
                # 初始化任务状态 (相当于创建了一个空白文档)
                self.task_state = {
                    "status": "running",
                    "task": task_content,
                    "start_time": time.time(),
                    "result": None
                }
                
                # 启动后台线程 (真正的并行工作)
                t = threading.Thread(target=self._run_task_background, args=(task_content,))
                t.daemon = True # 设置为守护线程，防止主程序退出时卡死
                t.start()
                
                res = f"已在后台启动任务: '{task_content}'。我正在处理中..."
                self.log("反馈消息 (启动后台任务)", res)
                return res
            except Exception as e:
                res = f"任务启动失败: 格式错误 ({str(e)})"
                self.log("反馈消息 (启动失败)", res)
                return res

        # 格式: START_LOOP: [次数] | [间隔] | [任务内容]
        if message.startswith("START_LOOP:"):
            try:
                _, params = message.split(":", 1)
                count_str, interval_str, task_content = params.split("|", 2)
                
                self.task_state = {
                    "status": "running",
                    "task": task_content.strip(),
                    "start_time": time.time(),
                    "intermediate_results": [],
                    "result": None
                }
                
                t = threading.Thread(target=self._run_loop_background, args=(int(count_str), int(interval_str), task_content.strip()))
                t.daemon = True
                t.start()
                
                res = f"已启动循环任务: 执行 {count_str} 次，间隔 {interval_str} 秒。"
                self.log("反馈消息 (启动循环任务)", res)
                return res
            except Exception as e:
                res = f"循环任务启动失败: {str(e)}"
                self.log("反馈消息 (启动失败)", res)
                return res

        # --- 2. 处理进度查询 ---
        if "汇报进度" in message or "查询进度" in message:
            if not self.task_state:
                return "目前处于空闲状态，没有正在执行的任务。"
            
            status = self.task_state.get("status")
            elapsed = time.time() - self.task_state["start_time"]
            
            if status == "running":
                # 如果有中间结果，展示最新的几条
                intermediate = self.task_state.get("intermediate_results", [])
                if intermediate:
                    latest_logs = "\n".join(intermediate[-3:]) # 只显示最后3条避免刷屏
                    res = f"正在执行 (已耗时 {int(elapsed)}s)...\n最新记录:\n{latest_logs}"
                else:
                    res = f"正在执行: {self.task_state['task']}...\n已耗时: {int(elapsed)} 秒 (准备中)"
                self.log("反馈消息 (汇报进度)", res)
                return res
            
            elif status == "done":
                result = self.task_state.get("result")
                # 必须包含此关键词以便调度器停止
                response = f"【任务已完成】\n耗时: {int(elapsed)} 秒\n结果如下：\n{result}"
                self.task_state = None # 汇报完毕，销毁记录
                self.log("反馈消息 (任务完成)", response)
                return response
                
            elif status == "error":
                result = self.task_state.get("result")
                self.task_state = None
                res = f"【任务已完成】(出错)\n错误: {result}"
                self.log("反馈消息 (任务出错)", res)
                return res

        # 默认逻辑
        if sender == "M":
            res = self.ask_ai(f"老板(M)对我说：{message}。请简短专业的回复。")
            self.log("反馈消息 (回复老板)", res)
            return res
        
        res = self.ask_ai(message)
        self.log("反馈消息 (普通回复)", res)
        return res
