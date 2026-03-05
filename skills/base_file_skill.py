from core.skill import BaseSkill
import os

class BaseFileSkill(BaseSkill):
    """文件操作通用基类，统一处理路径解析和文件搜索"""
    
    def __init__(self, name, config, llm_client, llm_model, bus):
        super().__init__(name, config, llm_client, llm_model, bus)
        # 统一获取配置
        self.root_path = os.path.abspath(config.get("root_path", "."))
        self.shortcuts = config.get("shortcuts", {})

    def _resolve_path(self, path_str):
        """解析路径，支持别名，并优先保证 root_path 下的访问"""
        # 0. 如果路径为空，返回配置的根目录
        if not path_str or path_str == ".":
            return self.root_path
        
        resolved_path = path_str
        
        # 1. 尝试解析快捷方式
        if path_str in self.shortcuts:
            resolved_path = self.shortcuts[path_str]
        elif path_str.strip("/. ") in self.shortcuts:
            resolved_path = self.shortcuts[path_str.strip("/. ")]
        elif not os.path.isabs(path_str):
            # os.sep is important for cross-platform
            parts = path_str.split(os.sep, 1)
            first_part_cleaned = parts[0].strip("/. ")
            
            if first_part_cleaned in self.shortcuts:
                resolved_first = self.shortcuts[first_part_cleaned]
                if len(parts) > 1:
                    resolved_path = os.path.join(resolved_first, parts[1])
                else:
                    resolved_path = resolved_first
            else:
                resolved_path = os.path.join(self.root_path, path_str)
        
        # --- 安全沙箱检查 (新增) ---
        # 允许的范围：配置的 root_path 和 当前项目目录
        abs_root = os.path.abspath(self.root_path)
        abs_project = os.path.abspath(os.getcwd())
        abs_resolved = os.path.abspath(resolved_path)
        
        is_safe = False
        for safe_path in [abs_root, abs_project]:
            # 检查解析后的路径是否以安全路径开头
            if abs_resolved.startswith(safe_path):
                is_safe = True
                break
        
        if not is_safe:
            # 如果路径跑出了安全范围，强制重置为 root_path (或者可以返回错误信息，这里选择安全回退)
            return self.root_path
        
        # 2. 智能回退逻辑 (修复 M 的幻觉)
        if not os.path.exists(resolved_path):
            clean_input = path_str
            for key in self.shortcuts:
                if path_str.startswith(key) and (len(path_str) == len(key) or path_str[len(key)] in [os.sep, '/']):
                     clean_input = path_str[len(key):].lstrip(os.sep + '/')
                     break
            
            fallback_path = os.path.join(self.root_path, clean_input)
            if os.path.exists(fallback_path):
                return fallback_path
        
        # 3. 终极回退：检查路径的最后一部分是否直接存在于 root_path 下
        if not os.path.exists(resolved_path):
            basename = os.path.basename(path_str.strip("/. "))
            if basename:
                direct_child_path = os.path.join(self.root_path, basename)
                if os.path.exists(direct_child_path):
                    return direct_child_path

        return resolved_path

    def _find_file(self, filename):
        """在 root_path 下递归查找文件"""
        for root, dirs, files in os.walk(self.root_path):
            if filename in files:
                return os.path.join(root, filename)
        return None