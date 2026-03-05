import threading
import os
import re
import requests
from flask import Flask, request, send_from_directory
from wechatpy.enterprise.crypto import WeChatCrypto
from wechatpy.exceptions import InvalidSignatureException
from wechatpy.enterprise import WeChatClient
from wechatpy import parse_message
from core.logger import SystemLogger

class WeComConnector:
    def __init__(self, corp_id, agent_id, secret, token, aes_key, bus, port=3001):
        self.corp_id = corp_id
        self.agent_id = agent_id
        self.secret = secret
        self.token = token
        self.aes_key = aes_key
        self.bus = bus
        self.port = port
        self.app = Flask(__name__)
        
        # 增加全局请求日志，确保任何打到服务的请求都被记录
        @self.app.before_request
        def log_request_info():
            if request.path != '/favicon.ico':
                SystemLogger.info(f"[WeCom Net] 收到请求: {request.method} {request.path}")

        # 初始化 API 客户端和加密器
        self.client = WeChatClient(corp_id, secret)
        self.crypto = WeChatCrypto(token, aes_key, corp_id)
        self.last_user = None

        # 注册路由
        self.app.route("/webhook/wecom", methods=["GET", "POST"])(self.handle_request)
        # 注册域名验证文件路由 (处理 WW_verify_xxx.txt)
        self.app.route("/<path:filename>", methods=["GET"])(self.handle_domain_verify)
        # 注册根路由，方便浏览器测试连通性
        self.app.route("/", methods=["GET"])(self.handle_health_check)

    def handle_health_check(self):
        """健康检查接口"""
        return f"NexusAgent WeCom Connector is running on port {self.port}!", 200

    def handle_domain_verify(self, filename):
        """处理域名归属权验证文件 (如果企业微信要求验证域名)"""
        # 安全检查：只允许访问 WW_verify_ 开头的 txt 文件
        if filename.startswith("WW_verify_") and filename.endswith(".txt") and "/" not in filename:
            if os.path.exists(filename):
                return send_from_directory(".", filename)
        return "Not Found", 404

    def handle_request(self):
        """处理企业微信回调"""
        signature = request.args.get("msg_signature", "")
        timestamp = request.args.get("timestamp", "")
        nonce = request.args.get("nonce", "")

        # 1. URL 验证 (GET)
        if request.method == "GET":
            echo_str = request.args.get("echostr", "")
            SystemLogger.info(f"[WeCom] 收到 URL 验证请求: signature={signature}, timestamp={timestamp}, nonce={nonce}, echostr={echo_str}")
            
            try:
                echo_str = self.crypto.check_signature(signature, timestamp, nonce, echo_str)
            except InvalidSignatureException:
                SystemLogger.error("[WeCom] 签名验证失败 (Invalid Signature)。请检查 Token 和 EncodingAESKey 是否与后台一致。")
                return "Invalid Signature", 403
            except Exception as e:
                SystemLogger.error(f"[WeCom] 验证过程发生异常: {e}", exc_info=True)
                return "Internal Server Error", 500
            
            SystemLogger.info(f"[WeCom] 验证成功，返回解密后的 echostr")
            return echo_str

        # 2. 消息接收 (POST)
        if request.method == "POST":
            try:
                decrypted_xml = self.crypto.decrypt_message(
                    request.data, signature, timestamp, nonce
                )
            except InvalidSignatureException:
                return "Invalid Signature", 403

            msg = parse_message(decrypted_xml)
            if msg.type == "text":
                self.last_user = msg.source
                content = msg.content
                # 异步处理
                t = threading.Thread(target=self._process_message, args=(content, msg.source))
                t.start()
            
            return "success"

    def _process_message(self, text, user_id):
        """处理消息逻辑"""
        target_name = "M"
        msg_content = text

        if text.startswith("@"):
            parts = text.split(" ", 1)
            if len(parts) == 2:
                target_name = parts[0][1:]
                msg_content = parts[1]
        
        skill = self.bus.get_skill(target_name)
        if skill:
            response = skill.handle_message(msg_content, "WeComUser")
            self.handle_response(f"[{target_name}] {response}", user_id)
        else:
            self.send_text(f"系统: 找不到 Skill {target_name}", user_id)

    def send_text(self, text, user_id=None):
        target = user_id or self.last_user
        if not target: return
        try:
            self.client.message.send_text(self.agent_id, target, text)
        except Exception as e:
            SystemLogger.error(f"[WeCom] Send failed: {e}")

    def upload_file(self, file_path):
        """上传文件到企业微信临时素材"""
        try:
            with open(file_path, 'rb') as f:
                res = self.client.media.upload('file', f)
                return res['media_id']
        except Exception as e:
            SystemLogger.error(f"[WeCom] 文件上传失败: {e}", exc_info=True)
            return None

    def send_file(self, media_id, user_id=None):
        target = user_id or self.last_user
        if not target: return
        try:
            self.client.message.send_file(self.agent_id, target, media_id)
        except Exception as e:
            SystemLogger.error(f"[WeCom] 发送文件消息失败: {e}", exc_info=True)

    def handle_response(self, response, user_id=None):
        """智能处理回复 (文本或文件)"""
        match = re.search(r"\[FILE_SEND:\s*(.*?)\]", response)
        if match:
            file_path = match.group(1).strip()
            self.send_text(f"正在上传文件: {os.path.basename(file_path)} ...", user_id)
            media_id = self.upload_file(file_path)
            if media_id:
                self.send_file(media_id, user_id)
            else:
                self.send_text(f"❌ 文件上传失败，请检查日志。", user_id)
        else:
            self.send_text(response, user_id)

    def start(self):
        print(f"🚀 WeCom Connector listening on port {self.port}...")
        SystemLogger.info(f"启动 WeCom Connector, 监听端口 {self.port}")
        
        # 辅助功能：自动获取并打印当前公网 IP
        try:
            ip = requests.get('https://ifconfig.me/ip', timeout=5).text.strip()
            print(f"🌐 检测到当前公网 IP: {ip}")
            print(f"👉 请务必将此 IP 填入企业微信后台 [应用管理 -> 你的应用 -> 企业可信IP]，否则无法发送消息。")
        except Exception:
            print("⚠️ 无法自动获取公网 IP，请手动查询 (curl ifconfig.me)")
            
        self.app.run(host="0.0.0.0", port=self.port)