import sys
import time
import random
import signal

from modules.config_loader import load_config
from modules.ai_client import AIClient
from modules.baidu_ocr import BaiduOCR
from modules.wechat_monitor import WeChatMonitor


def main():
    print("=== 微信智能自动回复系统 ===")

    # 加载配置
    try:
        config = load_config()
        print(f"[Config] 已加载配置")
        print(f"[Config] AI: {config.api.provider}")
        print(f"[Config] 风格: {config.style.default}")
    except Exception as e:
        print(f"[Error] 配置加载失败: {e}")
        sys.exit(1)

    # 检查API Key
    if not config.api.api_key:
        print("[Error] 未设置AI API Key")
        sys.exit(1)

    if not config.baidu_ocr.api_key or not config.baidu_ocr.secret_key:
        print("[Error] 未设置百度OCR API Key")
        sys.exit(1)

    # 初始化模块
    ai_client = AIClient(config.api)
    ocr = BaiduOCR(config.baidu_ocr.api_key, config.baidu_ocr.secret_key)
    monitor = WeChatMonitor(ocr)

    # 查找微信窗口
    if not monitor.find_wechat_window():
        print("[Error] 请先打开微信客户端")
        sys.exit(1)

    # 设置退出信号处理
    running = True

    def signal_handler(sig, frame):
        nonlocal running
        print("\n[System] 正在退出...")
        running = False

    signal.signal(signal.SIGINT, signal_handler)

    print(f"[System] 开始监控，每 {config.monitor.check_interval} 秒检查一次")
    print("[System] 按 Ctrl+C 退出")

    # 主循环
    while running:
        try:
            # 检查新消息
            new_msg = monitor.check_new_message()

            if new_msg:
                print(f"\n[收到] {new_msg}")

                # 生成回复
                reply = ai_client.generate_reply(
                    new_msg,
                    config.style.default,
                    config.style.custom_prompt,
                )

                if reply:
                    print(f"[回复] {reply}")

                    # 随机延迟
                    delay = random.uniform(
                        config.monitor.reply_delay_min,
                        config.monitor.reply_delay_max,
                    )
                    time.sleep(delay)

                    # 发送回复
                    monitor.send_message(reply)
                else:
                    print("[Warning] AI生成回复为空")

            time.sleep(config.monitor.check_interval)

        except Exception as e:
            print(f"[Error] {e}")
            time.sleep(config.monitor.check_interval)

    print("[System] 已退出")


if __name__ == "__main__":
    main()
