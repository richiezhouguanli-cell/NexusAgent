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

    # 2. 配置多 AI 模型 (基于 settings.yaml)
    llm_clients = {}
    llm_providers_config = app_config.get("llm_providers", {})
    
    for provider_name, config in llm_providers_config.items():
        api_key = os.getenv(config.get("api_key_env", ""))
        base_url = os.getenv(config.get("base_url_env", ""))
        model_name = os.getenv(config.get("model_name_env", ""))
        
        if api_key:
             # 简单的有效性检查 (针对 NVIDIA)
             if provider_name == "nvidia" and "nvapi-" not in api_key:
                 continue
             
             client, model = LLMFactory.create_client(api_key, base_url, model_name)
             llm_clients[provider_name] = (client, model)
             SystemLogger.info(f"✅ {provider_name} Client ({model_name}) initialized.")
             print(f"✅ {provider_name} Client ({model_name}) initialized.")

    default_provider = app_config.get("default_llm_provider", "gemini")

    def get_llm(skill_name):
        """根据配置为 Skill 获取对应的 LLM 客户端"""
        skill_conf = skill_configs.get(skill_name, {})
        provider = skill_conf.get("llm_provider", default_provider)
        
        if provider in llm_clients:
            return llm_clients[provider]
        
        # 如果指定的不存在，尝试使用默认的
        if default_provider in llm_clients:
            return llm_clients[default_provider]
            
        # 如果默认的也不存在，使用任意一个可用的
        if llm_clients:
            return list(llm_clients.values())[0]
            
        return None, None
    
    # 3. 初始化 Skills
    # M (Manager)
    client, model = get_llm("M")
    m_config = skill_configs.get("M", {})
    m_mr = ManagerSkill("M", m_config, client, model, bus, scheduler)
    bus.register_skill(m_mr)

    # 员工实例化 (分别配置)
    # 1. A (技术)
    client, model = get_llm("A")
    skill_a = SkillA("A", skill_configs.get("A", {}), client, model, bus)
    bus.register_skill(skill_a)

    # 2. B (文案)
    client, model = get_llm("B")
    skill_b = SkillB("B", skill_configs.get("B", {}), client, model, bus)
    bus.register_skill(skill_b)

    # 3. C (创意)
    client, model = get_llm("C")
    skill_c = SkillC("C", skill_configs.get("C", {}), client, model, bus)
    bus.register_skill(skill_c)

    # 4. D (公关)
    client, model = get_llm("D")
    skill_d = SkillD("D", skill_configs.get("D", {}), client, model, bus)
    bus.register_skill(skill_d)

    # 5. E (财务)
    client, model = get_llm("E")
    skill_e = SkillE("E", skill_configs.get("E", {}), client, model, bus)
    bus.register_skill(skill_e)

    # 6. 通用工具 - 文件对比
    client, model = get_llm("FileDiff")
    tool_diff = SkillToolFileDiff("FileDiff", {}, client, model, bus)
    bus.register_skill(tool_diff)

    # 7. 通用工具 - 文件管理
    client, model = get_llm("FileManager")
    tool_fm = SkillToolFileManager("FileManager", skill_configs.get("FileManager", {}), client, model, bus)
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
