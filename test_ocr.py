"""OCR测试脚本：验证百度OCR识别微信消息效果"""
import os
import base64

import mss
import mss.tools
import requests
import pygetwindow as gw
import yaml


class BaiduOCR:
    TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
    OCR_URL = "https://aip.baidubce.com/rest/2.0/ocr/v1/accurate"

    def __init__(self, api_key: str, secret_key: str):
        self._api_key = api_key
        self._secret_key = secret_key
        self._access_token = None

    def _get_access_token(self) -> str:
        if self._access_token:
            return self._access_token

        params = {
            "grant_type": "client_credentials",
            "client_id": self._api_key,
            "client_secret": self._secret_key,
        }
        resp = requests.post(self.TOKEN_URL, params=params)
        resp.raise_for_status()
        self._access_token = resp.json()["access_token"]
        return self._access_token

    def recognize(self, image_path: str) -> list[dict]:
        """识别图片中的文字，返回带位置信息的结果"""
        token = self._get_access_token()

        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()

        resp = requests.post(
            f"{self.OCR_URL}?access_token={token}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={"image": image_data},
        )
        resp.raise_for_status()
        result = resp.json()

        if "error_code" in result:
            raise Exception(f"OCR错误: {result['error_msg']}")

        return result.get("words_result", [])


def find_wechat_window():
    """查找微信窗口"""
    windows = gw.getWindowsWithTitle("微信")
    for win in windows:
        if win.title == "微信":
            return win
    return None


def capture_window(window, output_path: str):
    """截取窗口图像"""
    with mss.mss() as sct:
        region = {
            "left": window.left,
            "top": window.top,
            "width": window.width,
            "height": window.height,
        }
        screenshot = sct.grab(region)
        mss.tools.to_png(screenshot.rgb, screenshot.size, output=output_path)
    return output_path


def load_ocr_config():
    """加载OCR配置"""
    config_path = "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    ocr_config = data.get("baidu_ocr", {})
    api_key = os.environ.get("BAIDU_OCR_API_KEY") or ocr_config.get("api_key", "")
    secret_key = os.environ.get("BAIDU_OCR_SECRET_KEY") or ocr_config.get("secret_key", "")

    return api_key, secret_key


def main():
    print("=== 百度OCR 微信消息识别测试 ===\n")

    # 加载配置
    print("[1] 加载配置...")
    api_key, secret_key = load_ocr_config()
    if not api_key or not secret_key:
        print("    错误: 请在config.yaml或环境变量中配置百度OCR的api_key和secret_key")
        return
    print("    配置加载完成\n")

    # 查找微信窗口
    print("[2] 查找微信窗口...")
    window = find_wechat_window()
    if not window:
        print("    未找到微信窗口，请确保微信已打开")
        return

    print(f"    找到窗口: {window.title}")
    print(f"    位置: ({window.left}, {window.top})")
    print(f"    大小: {window.width} x {window.height}\n")

    # 截图
    print("[3] 截取微信窗口...")
    img_path = "wechat_screenshot.png"
    capture_window(window, img_path)
    print(f"    截图已保存: {img_path}\n")

    # OCR识别
    print("[4] 调用百度OCR识别...")
    ocr = BaiduOCR(api_key, secret_key)
    try:
        results = ocr.recognize(img_path)
    except Exception as e:
        print(f"    OCR识别失败: {e}")
        return
    print(f"    识别完成，共 {len(results)} 条结果\n")

    # 打印识别结果
    print("[5] 识别结果:\n")
    print("-" * 60)

    if results:
        for idx, item in enumerate(results):
            text = item.get("words", "")
            location = item.get("location", {})
            left = location.get("left", 0)
            top = location.get("top", 0)
            width = location.get("width", 0)

            # 计算文字中心位置，判断左右
            x_center = left + width / 2
            position = "左侧(对方)" if x_center < window.width / 2 else "右侧(自己)"

            print(f"[{idx+1}] {text}")
            print(f"    位置: {position}, x={left}, y={top}")
            print()
    else:
        print("未识别到文字")

    print("-" * 60)
    print("\n测试完成。")
    print("- 查看 wechat_screenshot.png 确认截图区域")
    print("- '左侧'通常是对方消息，'右侧'是自己消息")


if __name__ == "__main__":
    main()
