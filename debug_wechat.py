"""调试脚本：检测微信窗口信息"""
import uiautomation as auto


def find_wechat_windows():
    print("=== 正在搜索微信相关窗口 ===\n")

    # 搜索所有顶层窗口
    desktop = auto.GetRootControl()
    windows = desktop.GetChildren()

    wechat_windows = []
    for win in windows:
        try:
            name = win.Name or ""
            classname = win.ClassName or ""
            # 查找包含"微信"或"WeChat"的窗口
            if "微信" in name or "WeChat" in name.lower() or "wechat" in classname.lower():
                wechat_windows.append({
                    "Name": name,
                    "ClassName": classname,
                    "ControlType": win.ControlTypeName,
                })
        except Exception:
            continue

    if wechat_windows:
        print(f"找到 {len(wechat_windows)} 个微信相关窗口:\n")
        for i, w in enumerate(wechat_windows, 1):
            print(f"[{i}] Name: {w['Name']}")
            print(f"    ClassName: {w['ClassName']}")
            print(f"    ControlType: {w['ControlType']}")
            print()
    else:
        print("未找到微信窗口，请确保微信已打开且未最小化到托盘")
        print("\n列出所有顶层窗口供参考:")
        for win in windows[:20]:
            try:
                if win.Name:
                    print(f"  - {win.Name} ({win.ClassName})")
            except Exception:
                continue


if __name__ == "__main__":
    find_wechat_windows()
