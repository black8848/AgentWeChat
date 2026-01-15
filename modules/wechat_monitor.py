import time
import hashlib
from collections import OrderedDict

from wxauto import WeChat


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
        self._wx: WeChat | None = None
        self._current_chat: str | None = None

    def find_wechat_window(self) -> bool:
        try:
            self._wx = WeChat()
            print(f"[WeChat] 已连接微信")
            return True
        except Exception as e:
            print(f"[WeChat] 连接微信失败: {e}")
            return False

    def get_current_chat_name(self) -> str | None:
        if not self._wx:
            return None
        try:
            return self._wx.CurrentChat()
        except Exception:
            return None

    def get_messages(self, count: int = 5) -> list[tuple[str, str]]:
        if not self._wx:
            return []

        messages: list[tuple[str, str]] = []
        try:
            # 获取最近的消息
            msg_list = self._wx.GetAllMessage()
            if not msg_list:
                return []

            # 取最后count条
            for msg in msg_list[-count:]:
                sender = getattr(msg, "sender", "") or ""
                content = getattr(msg, "content", "") or ""
                msg_type = getattr(msg, "type", "")

                # 只处理文本消息
                if msg_type == "friend" and content:
                    messages.append((sender, content))

        except Exception as e:
            print(f"[WeChat] 获取消息失败: {e}")

        return messages

    def get_last_received_message(self) -> tuple[str, str] | None:
        messages = self.get_messages(5)
        if not messages:
            return None

        # 返回最后一条非自己发送的消息
        for sender, content in reversed(messages):
            if sender and content:
                return (sender, content)
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
        if not self._wx:
            return False

        try:
            self._wx.SendMsg(text)
            print(f"[WeChat] 已发送: {text[:50]}...")
            return True
        except Exception as e:
            print(f"[WeChat] 发送失败: {e}")
            return False
