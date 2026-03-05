import requests
import json
import time
import threading
import os
import re
import datetime
from flask import Flask, request, jsonify
from core.logger import SystemLogger

class FeishuConnector:
    def __init__(self, app_id, app_secret, bus, port=3000):
        self.app_id = app_id
        self.app_secret = app_secret
        self.bus = bus
        self.port = port
        self.app = Flask(__name__)
        self.token = ""
        self.token_expire_time = 0
        self.last_chat_id = None  # 记住最后对话的群/人，用于主动推送定时任务结果

        # 注册路由
        self.app.route("/webhook/event", methods=["POST"])(self.handle_event)

    def _get_token(self):
        """获取飞书 Tenant Access Token"""
        if time.time() < self.token_expire_time:
            return self.token
        
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json; charset=utf-8"}
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        try:
            response = requests.post(url, headers=headers, json=payload)
            try:
                resp = response.json()
            except Exception:
                print(f"[Feishu Error] Invalid JSON response from auth: {response.text}")
                SystemLogger.error(f"[Feishu] Auth 响应解析失败: {response.text}")
                return ""

            if resp.get("code") == 0:
                self.token = resp.get("tenant_access_token")
                self.token_expire_time = time.time() + resp.get("expire", 7200) - 60
                return self.token
            else:
                print(f"[Feishu Error] Get token failed: {resp}")
                SystemLogger.error(f"[Feishu] 获取 Token 失败: {resp}")
                return ""
        except Exception as e:
            print(f"[Feishu Error] {e}")
            SystemLogger.error(f"[Feishu] 获取 Token 异常: {e}", exc_info=True)
            return ""

    def send_text(self, text, chat_id=None):
        """发送文本消息"""
        target_id = chat_id or self.last_chat_id
        if not target_id:
            print("[Feishu] No chat_id available to send message.")
            return

        token = self._get_token()
        if not token:
            print("[Feishu] Failed to get token, cannot send message.")
            return

        url = f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        payload = {
            "receive_id": target_id,
            "msg_type": "text",
            "content": json.dumps({"text": text})
        }
        try:
            requests.post(url, headers=headers, json=payload)
        except Exception as e:
            print(f"[Feishu Send Error] {e}")
            SystemLogger.error(f"[Feishu] 发送消息失败: {e}", exc_info=True)

    def upload_file(self, file_path):
        """上传文件到飞书，获取 file_key"""
        token = self._get_token()
        if not token: return None
        
        url = "https://open.feishu.cn/open-apis/im/v1/files"
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            file_name = os.path.basename(file_path)
            with open(file_path, "rb") as f:
                files = {"file": (file_name, f)}
                data = {"file_type": "stream", "file_name": file_name}
                resp = requests.post(url, headers=headers, files=files, data=data)
                resp_json = resp.json()
                
                if resp_json.get("code") == 0:
                    return resp_json["data"]["file_key"]
                else:
                    SystemLogger.error(f"[Feishu] 文件上传失败: {resp_json}")
                    return None
        except Exception as e:
            SystemLogger.error(f"[Feishu] 文件上传异常: {e}", exc_info=True)
            return None

    def send_file(self, file_key, chat_id=None):
        """发送文件消息"""
        target_id = chat_id or self.last_chat_id
        if not target_id: return
        
        token = self._get_token()
        url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"}
        
        payload = {
            "receive_id": target_id,
            "msg_type": "file",
            "content": json.dumps({"file_key": file_key})
        }
        try:
            requests.post(url, headers=headers, json=payload)
        except Exception as e:
            SystemLogger.error(f"[Feishu] 发送文件消息失败: {e}", exc_info=True)

    def handle_response(self, response, chat_id=None):
        """智能处理回复 (文本或文件)"""
        match = re.search(r"\[FILE_SEND:\s*(.*?)\]", response)
        if match:
            file_path = match.group(1).strip()
            self.send_text(f"正在上传文件: {os.path.basename(file_path)} ...", chat_id)
            file_key = self.upload_file(file_path)
            if file_key:
                self.send_file(file_key, chat_id)
            else:
                self.send_text(f"❌ 文件上传失败，请检查日志。", chat_id)
        else:
            self.send_text(response, chat_id)

    def download_file(self, message_id, file_key, file_name):
        """下载文件并保存"""
        token = self._get_token()
        if not token: return None
        
        # 使用获取消息资源接口，而非通用文件下载接口 (修复 234008 错误)
        url = f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/resources/{file_key}"
        headers = {"Authorization": f"Bearer {token}"}
        params = {"type": "file"}
        
        try:
            resp = requests.get(url, headers=headers, params=params, stream=True)
            if resp.status_code == 200:
                # 创建存储目录 downloads/YYYY-MM-DD
                today = datetime.datetime.now().strftime("%Y-%m-%d")
                save_dir = os.path.join("downloads", today)
                if not os.path.exists(save_dir):
                    os.makedirs(save_dir)
                
                # 处理文件名冲突 (保留副本)
                file_path = os.path.join(save_dir, file_name)
                if os.path.exists(file_path):
                    name, ext = os.path.splitext(file_name)
                    timestamp = int(time.time())
                    file_path = os.path.join(save_dir, f"{name}_{timestamp}{ext}")
                
                with open(file_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                SystemLogger.info(f"[Feishu] 文件已保存: {file_path}")
                return file_path
            else:
                SystemLogger.error(f"[Feishu] 下载文件失败: {resp.text}")
                return None
        except Exception as e:
            SystemLogger.error(f"[Feishu] 下载文件异常: {e}", exc_info=True)
            return None

    def _process_file(self, message_id, file_key, file_name, chat_id):
        """处理接收到的文件"""
        self.send_text(f"正在接收文件: {file_name} ...", chat_id)
        saved_path = self.download_file(message_id, file_key, file_name)
        if saved_path:
            # 获取绝对路径以便显示
            abs_path = os.path.abspath(saved_path)
            self.send_text(f"✅ 文件已保存。\n路径: {abs_path}", chat_id)
            
            # 关键修改：将文件信息同步给 M，让他知道文件在哪里
            m_skill = self.bus.get_skill("M")
            if m_skill:
                m_skill.history.append({"role": "system", "content": f"系统通知：用户上传了文件 {file_name}，已保存至 {abs_path}"})
        else:
            self.send_text(f"❌ 文件接收失败，请检查日志。", chat_id)

    def handle_event(self):
        """处理飞书回调事件"""
        # 增加容错：使用 silent=True 防止解析失败抛出 400/500 错误
        data = request.get_json(silent=True)
        if not data:
            print("[Feishu] 收到无效请求 (非 JSON)")
            SystemLogger.error("[Feishu] 收到无效 Webhook 请求 (非 JSON)")
            return jsonify({})
        
        print(f"[Feishu Event] {json.dumps(data)}")
        # SystemLogger.info(f"[Feishu] 收到事件: {json.dumps(data)}") # 可选：记录详细事件日志
        
        # 1. URL 验证 (首次配置时飞书会发送此请求)
        if data.get("type") == "url_verification":
            return jsonify({"challenge": data.get("challenge")})
        
        # 2. 消息事件
        if data.get("header", {}).get("event_type") == "im.message.receive_v1":
            event = data.get("event", {})
            message = event.get("message", {})
            
            chat_id = message.get("chat_id")
            self.last_chat_id = chat_id # 更新活跃会话ID，以便定时任务知道发给谁
            
            msg_type = message.get("message_type")
            if msg_type == "text":
                content = json.loads(message.get("content", "{}"))
                text = content.get("text", "")
                
                # 异步处理，避免阻塞 Webhook 返回导致飞书重试
                t = threading.Thread(target=self._process_message, args=(text, chat_id))
                t.start()
            
            elif msg_type == "file":
                content = json.loads(message.get("content", "{}"))
                file_key = content.get("file_key")
                file_name = content.get("file_name", f"unknown_{int(time.time())}")
                message_id = message.get("message_id")
                
                t = threading.Thread(target=self._process_file, args=(message_id, file_key, file_name, chat_id))
                t.start()
        
        return jsonify({})

    def _process_message(self, text, chat_id):
        """处理消息逻辑 (复用 main.py 的路由逻辑)"""
        target_name = "M"
        msg_content = text

        # 简单的 @ 路由逻辑 (例如 "@A 写代码")
        if text.startswith("@"):
            parts = text.split(" ", 1)
            if len(parts) == 2:
                target_name = parts[0][1:]
                msg_content = parts[1]
        
        skill = self.bus.get_skill(target_name)
        if skill:
            response = skill.handle_message(msg_content, "FeishuUser")
            self.handle_response(f"[{target_name}] {response}", chat_id)
        else:
            self.send_text(f"系统: 找不到 Skill {target_name}", chat_id)

    def start(self):
        print(f"🚀 Feishu Connector listening on port {self.port}...")
        SystemLogger.info(f"启动 Feishu Connector, 监听端口 {self.port}")
        self.app.run(host="0.0.0.0", port=self.port)