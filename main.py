import os
import sys
import yaml
import threading
import time
from dotenv import load_dotenv
from core.bus import EventBus
from core.llm import LLMFactory
from core.scheduler import TaskScheduler
from skills.manager import ManagerSkill
from skills.skill_a import SkillA
from skills.skill_b import SkillB
from skills.skill_c import SkillC
from skills.skill_d import SkillD
from skills.skill_e import SkillE
from skills.tool_file_diff import SkillToolFileDiff
from skills.tool_file_manager import SkillToolFileManager
from connectors.feishu import FeishuConnector
from connectors.wecom import WeComConnector
from core.logger import SystemLogger

# 加载环境变量
load_dotenv("config/secrets.env")

def main():
    print("正在初始化 NexusAgent...")
    SystemLogger.info("NexusAgent 正在启动...")

    # 加载 Skill 配置 (Prompt/Persona)
    with open("config/settings.yaml", "r", encoding="utf-8") as f:
        app_config = yaml.safe_load(f)
    skill_configs = app_config.get("skills", {})
    
    # 检查代理设置
    if os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY"):
        SystemLogger.info(f"检测到代理配置: {os.getenv('HTTP_PROXY')}")
        print(f"📡 检测到代理配置: {os.getenv('HTTP_PROXY')}")
    
    # 1. 初始化总线和调度器
    bus = EventBus()
    
    # 初始化连接器列表
    active_connectors = []

    # 1. 飞书连接器
    feishu_app_id = os.getenv("FEISHU_APP_ID")
    if feishu_app_id:
        feishu_port = int(os.getenv("FEISHU_PORT", 3000))
        feishu_connector = FeishuConnector(feishu_app_id, os.getenv("FEISHU_APP_SECRET"), bus, port=feishu_port)
        active_connectors.append(feishu_connector)

    # 2. 企业微信连接器
    wecom_corp_id = os.getenv("WECOM_CORP_ID")
    if wecom_corp_id:
        wecom_port = int(os.getenv("WECOM_PORT", 3001))
        wecom_connector = WeComConnector(wecom_corp_id, os.getenv("WECOM_AGENT_ID"), os.getenv("WECOM_SECRET"), os.getenv("WECOM_TOKEN"), os.getenv("WECOM_AES_KEY"), bus, port=wecom_port)
        active_connectors.append(wecom_connector)
    
    # 调度器输出广播 (同时发给所有活跃连接器)
    def broadcast_output(msg):
        for connector in active_connectors:
            if hasattr(connector, 'handle_response'):
                connector.handle_response(msg)

    # 如果有连接器，使用广播回调；否则不配置回调
    scheduler = TaskScheduler(bus, output_handler=broadcast_output if active_connectors else None)

    # 2. 配置多 AI 模型
    # --- Gemini Client (默认) ---
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    gemini_base_url = os.getenv("GEMINI_BASE_URL")
    gemini_model_name = os.getenv("GEMINI_MODEL_NAME")
    
    gemini_client, gemini_model = LLMFactory.create_client(gemini_api_key, gemini_base_url, gemini_model_name)
    print(f"✅ Gemini Client ({gemini_model_name}) initialized.")
    SystemLogger.info(f"Gemini Client ({gemini_model_name}) initialized.")

    # --- NVIDIA Client (可选) ---
    nvidia_api_key = os.getenv("NVIDIA_API_KEY")
    nvidia_base_url = os.getenv("NVIDIA_BASE_URL")
    nvidia_model_name = os.getenv("NVIDIA_MODEL_NAME")
    
    if nvidia_api_key and "nvapi-" in nvidia_api_key:
        nvidia_client, nvidia_model = LLMFactory.create_client(nvidia_api_key, nvidia_base_url, nvidia_model_name)
        print(f"✅ NVIDIA Client ({nvidia_model_name}) initialized.")
        SystemLogger.info(f"NVIDIA Client ({nvidia_model_name}) initialized.")
    else:
        print(f"⚠️ NVIDIA Client 未配置或 Key 无效，所有 Skill 将回退使用 Gemini。")
        SystemLogger.info("NVIDIA Client 未配置，回退使用 Gemini。")
        # 如果 NVIDIA key 未配置，则回退到使用 Gemini
        nvidia_client, nvidia_model = gemini_client, gemini_model

    # 3. 初始化 Skills
    # M (Manager) - 使用 NVIDIA
    m_config = skill_configs.get("M", {})
    m_mr = ManagerSkill("M", m_config, nvidia_client, nvidia_model, bus, scheduler)
    bus.register_skill(m_mr)

    # 员工实例化 (分别配置)
    # 1. A (技术) - 使用 NVIDIA
    skill_a = SkillA("A", skill_configs.get("A", {}), nvidia_client, nvidia_model, bus)
    bus.register_skill(skill_a)

    # 2. B (文案) - 使用 NVIDIA
    skill_b = SkillB("B", skill_configs.get("B", {}), nvidia_client, nvidia_model, bus)
    bus.register_skill(skill_b)

    # 3. C (创意) - 使用 NVIDIA
    skill_c = SkillC("C", skill_configs.get("C", {}), nvidia_client, nvidia_model, bus)
    bus.register_skill(skill_c)

    # 4. D (公关) - 使用 NVIDIA
    skill_d = SkillD("D", skill_configs.get("D", {}), nvidia_client, nvidia_model, bus)
    bus.register_skill(skill_d)

    # 5. E (财务) - 使用 NVIDIA
    skill_e = SkillE("E", skill_configs.get("E", {}), nvidia_client, nvidia_model, bus)
    bus.register_skill(skill_e)

    # 6. 通用工具 - 文件对比
    tool_diff = SkillToolFileDiff("FileDiff", {}, nvidia_client, nvidia_model, bus)
    bus.register_skill(tool_diff)

    # 7. 通用工具 - 文件管理
    tool_fm = SkillToolFileManager("FileManager", skill_configs.get("FileManager", {}), nvidia_client, nvidia_model, bus)
    bus.register_skill(tool_fm)

    print("\n" + "="*40)
    print("🚀 NexusAgent 框架已启动")
    print("="*40)
    print("可用指令示例:")
    print("1. 让 A 写一首关于Python的诗 (直接对M下指令)")
    print("2. 帮我写个文案 (M会自行判断或回复)")
    print("3. @D 你好 (仍然可以用 @ 指定其他人)")
    print("4. /schedule A 汇报工作 10 (每10秒执行一次)")
    print("5. exit (退出)")
    print("="*40)
    SystemLogger.info("NexusAgent 启动完成，进入主循环。")

    # 4. 启动连接器
    if active_connectors:
        print(f"📡 正在启动 {len(active_connectors)} 个连接器模式...")
        SystemLogger.info(f"启动 {len(active_connectors)} 个连接器模式...")
        
        for connector in active_connectors:
            t = threading.Thread(target=connector.start)
            t.daemon = True
            t.start()
            
        # 进入阻塞循环，防止主线程退出
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n程序已停止。")
            SystemLogger.info("程序被用户中断 (KeyboardInterrupt)。")
        return

    # 4. 主循环 (模拟通讯软件)
    while True:
        try:
            user_input = input("\n[用户] >>> ").strip()
            if not user_input: continue
            if user_input.lower() in ["exit", "quit"]:
                print("再见！")
                SystemLogger.info("用户请求退出程序。")
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
                        print(f"❌ 系统: 找不到名为 {target_name} 的 Skill (可用: M, A, B, C, D, E)")
                else:
                    print("格式错误。请包含消息内容。")
            else:
                # 默认发送给 M
                target_name = "M"
                skill = bus.get_skill(target_name)
                if skill:
                    print(f"({target_name} 正在思考...)")
                    response = skill.handle_message(user_input, "User")
                    
                    if "[FILE_SEND:" in response:
                        print(f"[{target_name}] >>> (请求发送文件: {response})")
                    else:
                        print(f"[{target_name}] >>> {response}")

        except KeyboardInterrupt:
            print("\n程序已停止。")
            SystemLogger.info("程序被用户中断 (KeyboardInterrupt)。")
            break
        except Exception as e:
            print(f"发生错误: {e}")
            SystemLogger.error(f"主循环发生未捕获异常: {e}", exc_info=True)

if __name__ == "__main__":
    main()
