import json
import ctypes
import subprocess
import time
import winreg
from pathlib import Path

import win32gui
import win32process


class WeChatDoubleApp:
    def __init__(self, count=2):
        self.count = count
        self.wechat_path = self._detect_wechat_path()
        self.before_hwnds = self._find_wechat_windows()

    def _detect_wechat_path(self):
        REGISTRY_KEY = r"SOFTWARE\Tencent\Weixin"
        REGISTRY_VALUE = "InstallPath"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY) as key:
                install_path, _ = winreg.QueryValueEx(key, REGISTRY_VALUE)
                wechat_path = Path(install_path) / "Weixin.exe"
                return str(wechat_path) if wechat_path.exists() else None
        except Exception:
            return None

    @staticmethod
    def _find_wechat_windows():
        hwnds = []
        def callback(hwnd, extra):
            if not win32gui.IsWindowVisible(hwnd):
                return True
            title = win32gui.GetWindowText(hwnd)
            if title == "微信":
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                hwnds.append({"hwnd": hwnd, "pid": pid})
            return True
        win32gui.EnumWindows(callback, None)
        return hwnds

    @staticmethod
    def _get_screen_size():
        user32 = ctypes.windll.user32
        return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

    def _arrange_windows(self, windows):
        if not windows:
            return
        screen_width, screen_height = self._get_screen_size()
        left, top, right, bottom = win32gui.GetWindowRect(windows[0]["hwnd"])
        window_width = right - left
        window_height = bottom - top
        spacing = 10
        num_windows = len(windows)
        rows = 2 if num_windows >= 3 else 1
        windows_per_row = [num_windows // 2 + num_windows % 2, num_windows // 2] if rows > 1 else [num_windows]
        start_y = (screen_height - rows * (window_height + spacing)) // 2
        index = 0
        for row in range(rows):
            current_cols = windows_per_row[row]
            total_width = current_cols * window_width + (current_cols - 1) * spacing
            start_x = (screen_width - total_width) // 2
            for col in range(current_cols):
                if index >= num_windows:
                    break
                x = start_x + col * (window_width + spacing)
                y = start_y + row * (window_height + spacing)
                win32gui.MoveWindow(windows[index]["hwnd"], x, y, window_width, window_height, True)
                index += 1

    def run(self):
        if not self.wechat_path:
            print(json.dumps({"status": "error", "error": "未找到微信安装路径，请确认微信已安装"}, ensure_ascii=False))
            return

        for i in range(self.count):
            subprocess.Popen([self.wechat_path], shell=True)
            if i < self.count - 1:
                time.sleep(0.3)

        for _ in range(20):
            now_hwnds = self._find_wechat_windows()
            new_hwnds = [w for w in now_hwnds if w["hwnd"] not in {h["hwnd"] for h in self.before_hwnds}]
            if len(new_hwnds) >= self.count:
                self._arrange_windows(new_hwnds)
                print(json.dumps({
                    "status": "ok",
                    "summary": f"已启动 {len(new_hwnds)} 个微信实例",
                    "details": {
                        "launched_count": self.count,
                        "wechat_path": self.wechat_path,
                        "window_count": len(new_hwnds),
                    }
                }, ensure_ascii=False))
                return
            time.sleep(0.5)

        now_hwnds = self._find_wechat_windows()
        new_hwnds = [w for w in now_hwnds if w["hwnd"] not in {h["hwnd"] for h in self.before_hwnds}]
        self._arrange_windows(new_hwnds)
        print(json.dumps({
            "status": "ok" if new_hwnds else "warn",
            "summary": f"已启动 {len(new_hwnds)} 个微信实例" if new_hwnds else "未检测到微信窗口",
            "details": {
                "launched_count": self.count,
                "wechat_path": self.wechat_path,
                "window_count": len(new_hwnds),
            }
        }, ensure_ascii=False))


if __name__ == "__main__":
    app = WeChatDoubleApp()
    app.run()
