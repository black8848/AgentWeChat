import re
import time
import hashlib
import tempfile
from collections import OrderedDict
from dataclasses import dataclass

import mss
import mss.tools
import pyautogui
import pygetwindow as gw

from .baidu_ocr import BaiduOCR


class LRUCache:
    def __init__(self, capacity: int = 1000):
        self._cache: OrderedDict[str, bool] = OrderedDict()
        self._capacity = capacity

    def contains(self, key: str) -> bool:
        if key in self._cache:
            self._cache.move_to_end(key)
            return True
        return False

    def add(self, key: str) -> None:
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            self._cache[key] = True
            if len(self._cache) > self._capacity:
                self._cache.popitem(last=False)


@dataclass
class ChatMessage:
    text: str
    is_self: bool  # True=自己发的, False=对方发的
    y_pos: int  # 垂直位置，用于排序


class WeChatMonitor:
    # 需要过滤的UI元素关键词
    UI_KEYWORDS = [
        "搜索", "发送", "表情", "文件", "截图", "聊天记录",
        "折叠", "置顶", "通讯录", "收藏", "朋友圈", "小程序",
        "视频号", "看一看", "游戏", "设置", "关于",
    ]

    # 时间戳正则（如 14:15, 2025/12/19, 星期一）
    TIME_PATTERN = re.compile(r"^\d{1,2}:\d{2}$|^\d{4}/\d{1,2}/\d{1,2}$|^星期[一二三四五六日]$")

    def __init__(self, ocr: BaiduOCR):
        self._ocr = ocr
        self._processed_messages = LRUCache(1000)
        self._window = None
        self._chat_region = None  # 聊天区域坐标
        self._last_messages: list[str] = []
        # 防止回复自己消息的机制
        self._recent_sent_texts: list[str] = []  # 最近发送的消息
        self._last_send_time: float = 0  # 上次发送时间
        self._send_cooldown: float = 5.0  # 发送后冷却时间(秒)

    def find_wechat_window(self) -> bool:
        windows = gw.getWindowsWithTitle("微信")
        for win in windows:
            if win.title == "微信":
                self._window = win
                self._calculate_chat_region()
                print(f"[WeChat] 找到窗口: {win.width}x{win.height}")
                print(f"[WeChat] 聊天区域: {self._chat_region}")
                return True
        print("[WeChat] 未找到微信窗口")
        return False

    def _calculate_chat_region(self):
        """计算聊天消息区域（排除左侧列表和底部输入框）"""
        if not self._window:
            return

        # 微信布局：左侧聊天列表约280px，底部输入框约100px
        left_panel_width = 280
        bottom_panel_height = 120
        top_bar_height = 60

        self._chat_region = {
            "left": self._window.left + left_panel_width,
            "top": self._window.top + top_bar_height,
            "width": self._window.width - left_panel_width - 20,
            "height": self._window.height - top_bar_height - bottom_panel_height,
        }

    def _capture_chat_area(self) -> str:
        """截取聊天区域"""
        if not self._chat_region:
            return ""

        with mss.mss() as sct:
            screenshot = sct.grab(self._chat_region)
            tmp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            mss.tools.to_png(screenshot.rgb, screenshot.size, output=tmp_file.name)
            return tmp_file.name

    def _is_ui_element(self, text: str) -> bool:
        """判断是否是UI元素（需要过滤）"""
        # 过滤单字符
        if len(text) <= 1:
            return True
        # 过滤时间戳
        if self.TIME_PATTERN.match(text):
            return True
        # 过滤UI关键词
        for kw in self.UI_KEYWORDS:
            if kw in text:
                return True
        return False

    def _parse_messages(self, ocr_results: list[dict]) -> list[ChatMessage]:
        """解析OCR结果为消息列表"""
        messages = []
        chat_width = self._chat_region["width"] if self._chat_region else 800

        for item in ocr_results:
            text = item.get("words", "").strip()
            if not text or self._is_ui_element(text):
                continue

            location = item.get("location", {})
            left = location.get("left", 0)
            top = location.get("top", 0)
            width = location.get("width", 0)

            # 根据x位置判断是对方还是自己的消息
            # 对方消息靠左（x < 中线），自己消息靠右（x > 中线）
            x_center = left + width / 2
            is_self = x_center > chat_width * 0.5

            messages.append(ChatMessage(text=text, is_self=is_self, y_pos=top))

        # 按垂直位置排序
        messages.sort(key=lambda m: m.y_pos)
        return messages

    def get_messages(self) -> list[ChatMessage]:
        """获取当前聊天窗口的消息"""
        if not self._window:
            return []

        try:
            img_path = self._capture_chat_area()
            if not img_path:
                return []

            results = self._ocr.recognize(img_path)
            return self._parse_messages(results)
        except Exception as e:
            print(f"[WeChat] 获取消息失败: {e}")
            return []

    def get_last_received_message(self) -> str | None:
        """获取最新一条对方发送的消息"""
        messages = self.get_messages()
        if not messages:
            return None

        # 从后往前找对方的消息
        for msg in reversed(messages):
            if not msg.is_self:
                return msg.text
        return None

    def _make_message_id(self, content: str) -> str:
        timestamp_minute = int(time.time() // 60)
        raw = f"{content}:{timestamp_minute}"
        return hashlib.md5(raw.encode()).hexdigest()

    def _is_own_message(self, text: str) -> bool:
        """检查消息是否是自己发送的（防止回复自己的多行消息）"""
        for sent_text in self._recent_sent_texts:
            # 检查是否是发送消息的一部分
            if text in sent_text or sent_text in text:
                return True
            # 检查相似度（简单的子串匹配）
            if len(text) > 3 and text in sent_text:
                return True
        return False

    def check_new_message(self) -> str | None:
        """检查是否有新消息，返回新消息内容"""
        # 冷却时间内不检测
        if time.time() - self._last_send_time < self._send_cooldown:
            return None

        msg = self.get_last_received_message()
        if not msg:
            return None

        # 过滤自己发送的消息
        if self._is_own_message(msg):
            return None

        msg_id = self._make_message_id(msg)

        if self._processed_messages.contains(msg_id):
            return None

        self._processed_messages.add(msg_id)
        return msg

    def send_message(self, text: str) -> bool:
        """发送消息"""
        if not self._window:
            return False

        try:
            # 激活微信窗口
            self._window.activate()
            time.sleep(0.2)

            # 点击输入框区域（窗口底部中间位置）
            input_x = self._window.left + self._window.width // 2
            input_y = self._window.top + self._window.height - 50
            pyautogui.click(input_x, input_y)
            time.sleep(0.1)

            # 中文需要用剪贴板
            import pyperclip
            pyperclip.copy(text)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.1)

            # 发送
            pyautogui.press("enter")
            print(f"[WeChat] 已发送: {text[:30]}...")

            # 记录发送的消息和时间
            self._recent_sent_texts.append(text)
            # 只保留最近5条
            if len(self._recent_sent_texts) > 5:
                self._recent_sent_texts.pop(0)
            self._last_send_time = time.time()

            return True

        except Exception as e:
            print(f"[WeChat] 发送失败: {e}")
            return False
