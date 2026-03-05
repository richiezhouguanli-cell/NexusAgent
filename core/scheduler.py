from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import datetime
import logging
from core.logger import SystemLogger

# 关闭 apscheduler 的繁琐日志
logging.getLogger('apscheduler').setLevel(logging.WARNING)

class TaskScheduler:
    def __init__(self, bus, output_handler=None):
        self.scheduler = BackgroundScheduler()
        self.bus = bus
        self.last_results = {} # 用于记录上一次的执行结果
        self.output_handler = output_handler # 输出回调函数 (用于发消息给飞书)
        self.scheduler.start()

    def add_job(self, skill_name: str, task_instruction: str, seconds: int):
        """添加一个定时任务"""
        # 1. 提前生成 job_id，以便在内部函数中使用
        job_id = f"{skill_name}_{datetime.datetime.now().timestamp()}"

        def job_function():
            skill = self.bus.get_skill(skill_name)
            if skill:
                print(f"\n[⏰ 定时任务触发] {skill_name} 执行: {task_instruction}")
                SystemLogger.info(f"[Scheduler] 触发任务: {skill_name} -> {task_instruction}")
                result = skill.handle_message(task_instruction, "Scheduler")
                print(f"[✅ 任务结果] {result}\n[用户] >>> ", end="", flush=True)
                
                # 如果配置了输出回调 (例如飞书)，则发送通知
                if self.output_handler:
                    self.output_handler(f"⏰ [定时任务] {skill_name}:\n{result}")
                
                # 检查是否与上次结果相同 (去重停止)
                last_res = self.last_results.get(job_id)
                if last_res and last_res == result:
                    try:
                        self.scheduler.remove_job(job_id)
                        print(f"\n[系统] 检测到反馈内容无变化(或任务已停止)，自动停止监控。")
                        SystemLogger.info(f"[Scheduler] 任务停止 (内容无变化): {job_id}")
                        return
                    except Exception:
                        pass
                self.last_results[job_id] = result

                # 2. 自动停止逻辑：如果检测到任务完成，移除定时器
                if "【任务已完成】" in result:
                    try:
                        self.scheduler.remove_job(job_id)
                        print(f"\n[系统] 检测到任务结束，自动停止定时监控。")
                        SystemLogger.info(f"[Scheduler] 任务停止 (任务已完成): {job_id}")
                    except Exception:
                        pass
        
        self.scheduler.add_job(
            job_function, 
            trigger=IntervalTrigger(seconds=seconds),
            id=job_id,
            next_run_time=datetime.datetime.now() # 立即触发第一次执行
        )
        SystemLogger.info(f"[Scheduler] 创建新任务: {skill_name} 每 {seconds}s 执行 '{task_instruction}'")
        return f"任务已创建：每 {seconds} 秒让 {skill_name} 执行 '{task_instruction}'"

    def stop_all_jobs(self):
        """停止所有定时任务"""
        self.scheduler.remove_all_jobs()
        self.last_results.clear()
        SystemLogger.info("[Scheduler] 已停止所有定时任务")
        return "已停止所有定时任务。"

    def stop_target_jobs(self, target_name: str):
        """停止指定目标的定时任务"""
        count = 0
        for job in self.scheduler.get_jobs():
            if job.id.startswith(f"{target_name}_"):
                self.scheduler.remove_job(job.id)
                count += 1
        SystemLogger.info(f"[Scheduler] 已停止 {target_name} 的 {count} 个任务")
        return f"已停止 {target_name} 的 {count} 个定时任务。"
