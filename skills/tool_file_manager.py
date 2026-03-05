from skills.base_file_skill import BaseFileSkill
import os

class SkillToolFileManager(BaseFileSkill):
    """
    文件管理工具 Skill
    能力: 列出目录, 读取文件
    限制: 严禁删除或修改文件
    """
    def __init__(self, name, config, llm_client, llm_model, bus):
        if not config.get("persona"):
            shortcuts = config.get("shortcuts", {})
            root_path = config.get("root_path", ".")
            persona_text = f"你是一个文件管理工具。默认工作目录是：{root_path}。你可以列出目录内容和读取文件内容。你严禁执行任何删除、修改或移动文件的操作。"
            if shortcuts:
                shortcut_list = ", ".join([f"'{k}'" for k in shortcuts.keys()])
                persona_text += f"已知快捷路径：{shortcut_list}"
            config["persona"] = persona_text
        super().__init__(name, config, llm_client, llm_model, bus)

    def handle_message(self, message: str, sender: str) -> str:
        self.log(f"收到消息 (Sender: {sender})", message)

        # 安全熔断：严禁删除
        if any(k in message.lower() for k in ["删除", "delete", "rm ", "remove", "unlink", "修改", "overwrite"]):
            res = "❌ 安全警告：我被禁止执行任何删除或修改操作。"
            self.log("安全拦截", res)
            return res

        msg = message.strip()

        # 1. 发送文件 (传输文件实体) - 优先处理
        # 指令格式: 发送文件 [路径]
        if msg.startswith("发送文件"):
            try:
                # 使用切片去除指令前缀，避免 replace 误伤文件名
                raw_path = msg[4:].strip().strip("。.")
                path = self._resolve_path(raw_path)
                
                if not os.path.exists(path):
                    # 尝试自动搜索同名文件
                    found_path = self._find_file(os.path.basename(raw_path))
                    if found_path:
                        self.log("自动搜索成功", f"原路径未找到，已自动定位到子目录文件: {found_path}")
                        path = found_path
                    else:
                        msg = f"❌ 文件不存在: {path}"
                        self.log("发送文件失败", msg)
                        return msg
                
                if not os.path.isfile(path):
                    msg = f"❌ 这不是一个文件: {path}"
                    self.log("发送文件失败", msg)
                    return msg
                
                # 返回特殊协议指令，由 Connector 拦截处理
                return f"[FILE_SEND: {path}]"
            except Exception as e:
                return f"❌ 发送文件请求失败: {str(e)}"

        # 2. 读取文件 - 优先处理
        # 指令格式: 读取文件 [路径]
        elif msg.startswith("读取文件") or msg.startswith("cat"):
            try:
                if msg.startswith("读取文件"):
                    raw_path = msg[4:].strip().strip("。.")
                else:
                    raw_path = msg[3:].strip().strip("。.")
                
                path = self._resolve_path(raw_path)
                
                if not os.path.exists(path):
                    # 尝试自动搜索同名文件
                    found_path = self._find_file(os.path.basename(raw_path))
                    if found_path:
                        self.log("自动搜索成功", f"原路径未找到，已自动定位到子目录文件: {found_path}")
                        path = found_path
                    else:
                        msg = f"❌ 文件不存在: {path}"
                        self.log("读取文件失败", msg)
                        return msg
                
                if not os.path.isfile(path):
                    msg = f"❌ 这不是一个文件: {path}"
                    self.log("读取文件失败", msg)
                    return msg

                # 限制读取大小 (1MB)
                file_size = os.path.getsize(path)
                if file_size > 1024 * 1024:
                    return f"❌ 文件过大 ({file_size/1024:.2f} KB)，为了安全禁止读取超过 1MB 的文件。"

                with open(path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                
                res = f"📄 文件 {os.path.basename(path)} 内容如下:\n```\n{content}\n```"
                self.log("读取文件成功", f"文件: {path}\n大小: {len(content)} 字符")
                return res
            except Exception as e:
                error_msg = f"❌ 读取文件失败: {str(e)}"
                self.log("读取文件出错", error_msg)
                return error_msg

        # 3. 列出目录 (最后处理)
        # 指令格式: 列出目录 [路径]
        # 优化匹配: 避免 "ls" 误匹配到文件名 (如 .xlsx)
        elif msg.startswith("列出") or msg.startswith("ls ") or msg == "ls":
            try:
                if msg.startswith("列出目录"):
                    raw_path = msg[4:].strip().strip("。.")
                elif msg.startswith("列出"):
                    raw_path = msg[2:].strip().strip("。.")
                else:
                    # ls
                    raw_path = msg[2:].strip().strip("。.")
                
                path = self._resolve_path(raw_path)
                
                if not os.path.exists(path):
                    msg = f"❌ 路径不存在: {path}"
                    self.log("列出目录失败", msg)
                    return msg
                
                if not os.path.isdir(path):
                    msg = f"❌ 这不是一个目录: {path}"
                    self.log("列出目录失败", msg)
                    return msg

                files = os.listdir(path)
                # 过滤隐藏文件
                files = [f for f in files if not f.startswith('.')]
                files.sort()
                
                abs_path = os.path.abspath(path)
                result = f"📂 目录 {abs_path} 的内容:\n" + "\n".join(files)
                self.log("列出目录成功", result)
                return result
            except Exception as e:
                error_msg = f"❌ 列出目录失败: {str(e)}"
                self.log("列出目录出错", error_msg)
                return error_msg

        return "我是文件管理工具。请使用以下标准格式指令：\n" \
               "1. 下载文件：`发送文件 [文件名]` (例如: `发送文件 报告.xlsx`)\n" \
               "2. 读取内容：`读取文件 [文件名]` (例如: `读取文件 笔记.txt`)\n" \
               "3. 列出目录：`列出目录 [路径]` (例如: `列出目录 .`)"