import os
import datetime
import traceback

class SystemLogger:
    """全局系统日志记录器"""
    
    LOG_DIR = "logs"
    
    @staticmethod
    def _write(filename_prefix, level, message):
        if not os.path.exists(SystemLogger.LOG_DIR):
            os.makedirs(SystemLogger.LOG_DIR)
            
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        filename = os.path.join(SystemLogger.LOG_DIR, f"{filename_prefix}_{today}.log")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        
        try:
            with open(filename, "a", encoding="utf-8") as f:
                f.write(log_entry)
            # 同时打印到控制台，方便调试
            print(log_entry.strip())
        except Exception as e:
            print(f"系统日志写入失败: {e}")

    @staticmethod
    def info(message: str):
        """记录普通系统信息 (system_YYYY-MM-DD.log)"""
        SystemLogger._write("system", "INFO", message)

    @staticmethod
    def error(message: str, exc_info=None):
        """记录错误信息 (error_YYYY-MM-DD.log)"""
        content = message
        if exc_info:
            # 获取堆栈跟踪
            tb = traceback.format_exc()
            content += f"\nTraceback:\n{tb}"
            
        SystemLogger._write("error", "ERROR", content)