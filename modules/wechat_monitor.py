import time
import hashlib
from collections import OrderedDict

import uiautomation as auto
import pyperclip


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


class WeChatMonitor:
    def __init__(self):
        self._processed_messages = LRUCache(1000)
        self._wechat_window: auto.WindowControl | None = None
        self._last_message_count = 0

    def find_wechat_window(self) -> bool:
        # 尝试多种方式查找微信窗口
        search_methods = [
            ("ClassName", {"searchDepth": 1, "ClassName": "WeChatMainWndForPC"}),
            ("ClassName2", {"searchDepth": 1, "ClassName": "WeChat"}),
            ("Name", {"searchDepth": 1, "Name": "微信"}),
        ]

        for method_name, kwargs in search_methods:
            try:
                window = auto.WindowControl(**kwargs)
                if window.Exists(0.5, 0.5):
                    self._wechat_window = window
                    print(f"[WeChat] 找到微信窗口 (via {method_name})")
                    print(f"[WeChat] ClassName: {window.ClassName}")
                    print(f"[WeChat] Name: {window.Name}")
                    return True
            except Exception as e:
                print(f"[WeChat] 方法 {method_name} 失败: {e}")
                continue

        print("[WeChat] 未找到微信窗口")
        print("[WeChat] 请运行 debug_wechat.py 查看实际窗口信息")
        return False

    def get_current_chat_name(self) -> str | None:
        if not self._wechat_window:
            return None
        try:
            # 聊天标题栏
            title = self._wechat_window.TextControl(searchDepth=10)
            if title.Exists(0, 0):
                return title.Name
        except Exception:
            pass
        return None

    def get_messages(self) -> list[tuple[str, str]]:
        if not self._wechat_window:
            return []

        messages: list[tuple[str, str]] = []
        try:
            # 定位消息列表控件
            msg_list = self._wechat_window.ListControl(Name="消息")
            if not msg_list.Exists(0, 0):
                return []

            items = msg_list.GetChildren()
            for item in items:
                try:
                    name = item.Name or ""
                    # 获取消息文本内容
                    texts = item.GetChildren()
                    content = ""
                    for t in texts:
                        if t.Name:
                            content = t.Name
                            break
                    if content:
                        messages.append((name, content))
                except Exception:
                    continue

        except Exception as e:
            print(f"[WeChat] 获取消息失败: {e}")

        return messages

    def get_last_received_message(self) -> tuple[str, str] | None:
        messages = self.get_messages()
        if not messages:
            return None

        # 返回最后一条消息（假设是对方发的）
        # 简单判断：如果消息名称不为空，认为是对方发的
        for name, content in reversed(messages):
            if name and content:
                return (name, content)
        return None

    def _make_message_id(self, sender: str, content: str) -> str:
        timestamp_minute = int(time.time() // 60)
        raw = f"{sender}:{content}:{timestamp_minute}"
        return hashlib.md5(raw.encode()).hexdigest()

    def check_new_message(self) -> tuple[str, str] | None:
        msg = self.get_last_received_message()
        if not msg:
            return None

        sender, content = msg
        msg_id = self._make_message_id(sender, content)

        if self._processed_messages.contains(msg_id):
            return None

        self._processed_messages.add(msg_id)
        return (sender, content)

    def send_message(self, text: str) -> bool:
        if not self._wechat_window:
            return False

        try:
            # 定位输入框
            edit = self._wechat_window.EditControl(Name="输入")
            if not edit.Exists(0, 0):
                print("[WeChat] 未找到输入框")
                return False

            # 点击输入框激活
            edit.Click()
            time.sleep(0.1)

            # 使用剪贴板粘贴内容
            pyperclip.copy(text)
            edit.SendKeys("{Ctrl}v")
            time.sleep(0.1)

            # 发送
            edit.SendKeys("{Enter}")
            print(f"[WeChat] 已发送: {text[:50]}...")
            return True

        except Exception as e:
            print(f"[WeChat] 发送失败: {e}")
            return False
