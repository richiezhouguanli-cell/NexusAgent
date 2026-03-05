from core.skill import BaseSkill
import re
import os
import difflib

class SkillToolFileDiff(BaseSkill):
    """
    通用文件对比工具 Skill
    用法: 发送包含 "对比文件 [路径1] 和 [路径2]" 的消息
    """
    def __init__(self, name, config, llm_client, llm_model, bus):
        # 工具类 Skill 通常不需要复杂的人设，给个简单说明即可
        if not config.get("persona"):
            config["persona"] = "你是一个文件分析工具，负责读取文件内容并进行对比分析。"
        super().__init__(name, config, llm_client, llm_model, bus)

    def _find_file(self, path_str):
        """递归查找文件 (主要用于查找上传的文件)"""
        # 1. 如果是绝对路径且存在，直接返回
        if os.path.exists(path_str):
            return path_str
            
        target_name = os.path.basename(path_str)
        # 2. 在当前目录(含downloads)递归搜索
        for root, dirs, files in os.walk("."):
            if target_name in files:
                return os.path.join(root, target_name)
        return None

    def _read_file_content(self, file_path):
        """读取文件内容，支持 docx 和文本，并进行截断"""
        try:
            ext = os.path.splitext(file_path)[1].lower()
            content = ""
            
            if ext == ".docx":
                try:
                    import docx
                    doc = docx.Document(file_path)
                    content = "\n".join([para.text for para in doc.paragraphs])
                except ImportError:
                    return "【系统提示】缺少 python-docx 库，无法解析 .docx 文件。请运行 pip install python-docx 安装。"
                except Exception as e:
                    return f"【系统提示】解析 .docx 文件失败: {str(e)}"
            else:
                # 默认尝试以文本方式读取
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
            
            # 移除强制截断，以便 difflib 能对比全量内容
            return content
        except Exception as e:
            return f"读取文件失败: {str(e)}"

    def handle_message(self, message: str, sender: str) -> str:
        self.log(f"收到消息 (Sender: {sender})", message)

        # 检查是否是文件对比任务
        if "对比文件" in message:
            # 使用正则表达式从指令中提取文件路径
            # 格式: "对比文件 /path/to/file1 和 /path/to/file2"
            match = re.search(r"对比文件\s+(.*?)\s+和\s+(.*)", message)
            if match:
                raw_path1 = match.group(1).strip().strip('"\'')
                raw_path2 = match.group(2).strip().strip("。.").strip('"\'')
                
                # 自动搜索文件 (优先查找 downloads 等子目录)
                # 如果找不到，就保留原始路径，后续读取时会报错
                file_path1 = self._find_file(raw_path1) or raw_path1
                file_path2 = self._find_file(raw_path2) or raw_path2
                
                self.log("文件对比任务", f"文件1: {file_path1}\n文件2: {file_path2}")

                content1 = self._read_file_content(file_path1)
                content2 = self._read_file_content(file_path2)

                # 检查读取是否出错
                if content1.startswith("读取文件失败") or content1.startswith("【系统提示】"):
                    return content1
                if content2.startswith("读取文件失败") or content2.startswith("【系统提示】"):
                    return content2

                # 1. 预检查：完全一致
                if content1 == content2:
                    return f"【对比结果】\n文件 `{os.path.basename(file_path1)}` 和 `{os.path.basename(file_path2)}` 内容完全一致，没有发现差异。"

                # 策略选择：如果文件内容较短，直接交给 AI 对比（语义分析更强）；如果太长，先用 difflib 提取差异（更精准且省 Token）
                # 设定阈值：例如 30000 字符 (Gemini/GPT-4 都能轻松处理)
                total_len = len(content1) + len(content2)
                
                if total_len < 30000:
                    # 方案 A: 全文 AI 对比 (语义分析)
                    comparison_prompt = f"""请对比以下两个文件的内容，找出它们的不同之处。

--- 文件 1: {os.path.basename(file_path1)} ---
{content1}

--- 文件 2: {os.path.basename(file_path2)} ---
{content2}

请总结：
1. 具体的修改点。
2. 修改前后的语义或逻辑差异。
"""
                else:
                    # 方案 B: Difflib + AI 分析 (针对大文件)
                    try:
                        diff = list(difflib.unified_diff(
                            content1.splitlines(),
                            content2.splitlines(),
                            fromfile=os.path.basename(file_path1),
                            tofile=os.path.basename(file_path2),
                            lineterm=''
                        ))
                        diff_text = "\n".join(diff)
                        
                        # 截断差异
                        max_diff_len = 15000
                        if len(diff_text) > max_diff_len:
                            diff_text = diff_text[:max_diff_len] + f"\n... (差异过长，仅显示前 {max_diff_len} 字符) ..."

                        comparison_prompt = f"""请根据以下的差异对比结果（Unified Diff格式），详细分析两个文件的区别。

```diff
{diff_text}
```

请总结：
1. 概括主要的修改点。
2. 分析这些修改可能带来的影响或意图。
"""
                    except Exception as e:
                        error_msg = f"对比分析时发生错误: {str(e)}"
                        self.log("文件对比失败", error_msg)
                        return error_msg

                # 调用 AI 进行分析 (统一执行)
                res = self.ask_ai(comparison_prompt)
                self.log("文件对比完成", res)
                return res
            else:
                return "指令格式错误。正确格式：对比文件 [路径1] 和 [路径2]"
        
        return "我是文件对比工具，请发送 '对比文件 A 和 B' 指令。"