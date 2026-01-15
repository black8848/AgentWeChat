"""调试脚本：分析微信窗口控件结构"""
import uiautomation as auto


def analyze_wechat_structure():
    print("=== 分析微信窗口控件结构 ===\n")

    # 查找微信窗口
    wechat = auto.WindowControl(searchDepth=1, Name="微信")
    if not wechat.Exists(1, 1):
        print("未找到微信窗口")
        return

    print(f"微信窗口: {wechat.Name} ({wechat.ClassName})\n")

    # 递归打印控件树（限制深度）
    def print_control_tree(control, depth=0, max_depth=4):
        if depth > max_depth:
            return

        indent = "  " * depth
        name = control.Name[:30] if control.Name else ""
        classname = control.ClassName or ""
        control_type = control.ControlTypeName

        # 只打印有意义的控件
        if name or classname:
            print(f"{indent}[{control_type}] Name='{name}' Class='{classname}'")

        try:
            children = control.GetChildren()
            for child in children:
                print_control_tree(child, depth + 1, max_depth)
        except Exception:
            pass

    print("控件树结构 (深度4):\n")
    print_control_tree(wechat)

    # 查找特定控件
    print("\n\n=== 查找关键控件 ===\n")

    # 尝试查找列表控件
    print("ListControl 控件:")
    lists = wechat.GetChildren()
    for ctrl in lists:
        try:
            if ctrl.ControlTypeName == "ListControl":
                print(f"  - Name='{ctrl.Name}' Class='{ctrl.ClassName}'")
        except Exception:
            pass

    # 尝试用不同方式查找消息列表
    test_names = ["消息", "聊天记录", "Message", ""]
    print("\n尝试查找消息列表:")
    for name in test_names:
        try:
            if name:
                lst = wechat.ListControl(Name=name, searchDepth=10)
            else:
                lst = wechat.ListControl(searchDepth=10)
            if lst.Exists(0.5, 0.5):
                print(f"  找到: Name='{lst.Name}' Class='{lst.ClassName}'")
                # 打印子元素
                children = lst.GetChildren()
                print(f"  子元素数量: {len(children)}")
                for i, child in enumerate(children[:3]):
                    print(f"    [{i}] {child.ControlTypeName} Name='{child.Name[:50] if child.Name else ''}'")
                break
        except Exception as e:
            print(f"  Name='{name}' 失败: {e}")

    # 查找输入框
    print("\n尝试查找输入框:")
    test_edit_names = ["输入", "发送消息", ""]
    for name in test_edit_names:
        try:
            if name:
                edit = wechat.EditControl(Name=name, searchDepth=10)
            else:
                edit = wechat.EditControl(searchDepth=10)
            if edit.Exists(0.5, 0.5):
                print(f"  找到: Name='{edit.Name}' Class='{edit.ClassName}'")
                break
        except Exception as e:
            print(f"  Name='{name}' 失败: {e}")


if __name__ == "__main__":
    analyze_wechat_structure()
