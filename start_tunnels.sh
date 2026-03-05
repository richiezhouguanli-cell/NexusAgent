#!/bin/bash

# 自动检测 ngrok 命令位置
NGROK_CMD="ngrok"
if ! command -v ngrok &> /dev/null; then
    if [ -f "./ngrok" ]; then
        NGROK_CMD="./ngrok"
    else
        echo "❌ 错误: 未在 PATH 或当前目录找到 ngrok。"
        echo "请确保已安装 ngrok，或将 ngrok 可执行文件复制到此目录下。"
        exit 1
    fi
fi

echo "🛑 正在清理旧的 ngrok 进程..."
# 强制杀死所有 ngrok 进程，防止端口冲突
pkill ngrok || killall ngrok || true
sleep 1

echo "🚀 正在启动双通道 ngrok (飞书:3000, 企微:3001)..."
echo "👉 请确保你已在 ngrok.yml 中配置了 authtoken (或全局配置过)"

# 使用配置文件启动所有定义的隧道
# 注意：使用了 --config 参数后，ngrok 可能不会读取默认位置的配置，建议将 token 填入 ngrok.yml
$NGROK_CMD start --all --config=ngrok.yml