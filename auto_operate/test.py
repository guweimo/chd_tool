import threading
import pyautogui
from pynput import keyboard
from pynput.keyboard import Key, Controller as KeyController
from pynput.mouse import Button, Controller as MouseController
from pystray import Icon, Menu, MenuItem
from PIL import Image
import time
import sys
import win32gui
import win32con
import win32api
import ctypes

# 定义Windows API常量
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_CHAR = 0x0102
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
INPUT_HARDWARE = 2
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_ABSOLUTE = 0x8000

class AutoClicker:
    def __init__(self):
        self.is_clicking = False
        self.is_running = True
        self.on_ctrl = False
        self.on_alt = False
        self.auto_buy = False
        self.stop_operate = False
        self.target_window_title = "游戏窗口"  # 替换为你的游戏窗口标题
        self.hwnd = None
        self.key_controller = KeyController()
        self.mouse_controller = MouseController()
        self.current_pos = (0, 0)
        self.position1 = [
            [1664, 876],
            [1713, 1050],
            [2088, 939],
        ]
        self.position2 = [
            [1664, 936],
            [2065, 824],
            [2065, 997],
        ]
        self.position3 = [
            [1652, 821],
            [1678, 998],
            [2075, 880],
        ]
        
        # 获取屏幕尺寸
        self.screen_width = win32api.GetSystemMetrics(0)
        self.screen_height = win32api.GetSystemMetrics(1)
        
        # 托盘图标和菜单
        self.tray_icon = self.create_tray_icon()
        
        # 键盘监听
        self.listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        self.listener.start()

        # 自动点击线程
        self.click_thread = threading.Thread(target=self.auto_click)
        self.click_thread.daemon = True
        self.click_thread.start()

        # 运行托盘图标
        self.tray_icon.run()

    def create_tray_icon(self):
        # 创建托盘图标
        try:
            image = Image.open("c:/project/auto_operate/icon.png")  # 需要准备一个图标文件
        except FileNotFoundError:
            image = Image.new('RGB', (64, 64), (30, 144, 255))  # 如果图标文件不存在，使用默认蓝色图标
        menu = Menu(
            MenuItem('退出', self.on_exit),
            MenuItem('当前位置', lambda: f"{self.current_pos}"),
            MenuItem('Ctrl+F1 自动点击', None),
            MenuItem('Ctrl+F2 取消自动', None),
            MenuItem('Ctrl+F5 攻击免疫', None),
            MenuItem('Ctrl+F6 小吸红', None),
            MenuItem('Ctrl+F7 属性免疫', None),
            MenuItem('激活游戏窗口', self.activate_target_window),
        )
        return Icon("AutoClicker", image, "自动操作工具", menu)

    def activate_target_window(self):
        """激活目标窗口"""
        self.hwnd = win32gui.FindWindow(None, self.target_window_title)
        if self.hwnd:
            # 如果窗口最小化，恢复窗口
            if win32gui.IsIconic(self.hwnd):
                win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
            # 激活窗口
            win32gui.SetForegroundWindow(self.hwnd)
            self.tray_icon.notify("已激活游戏窗口", "操作成功")
        else:
            self.tray_icon.notify("未找到游戏窗口", "操作失败")

    def is_target_window_active(self):
        """检查目标窗口是否处于活动状态"""
        hwnd = win32gui.GetForegroundWindow()
        active_window_title = win32gui.GetWindowText(hwnd)
        # return self.target_window_title in active_window_title
        return self.hwnd is not None

    def win32_click(self, x=None, y=None, button='left'):
        """使用win32api模拟鼠标点击"""
        # if x is not None and y is not None:
            # self.win32_move(x, y)

        point = win32api.MAKELONG(x, y)
        if button == 'left':
            win32gui.SendMessage(self.hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, point)
            win32gui.SendMessage(self.hwnd, win32con.WM_LBUTTONUP, 0, point)
        elif button == 'right':
        # 发送右键按下和释放消息
            win32gui.SendMessage(self.hwnd, win32con.WM_RBUTTONDOWN, win32con.MK_RBUTTON, point)
            win32gui.SendMessage(self.hwnd, win32con.WM_RBUTTONUP, 0, point)
        else:
            return

    def win32_move(self, x, y):
        """使用win32api移动鼠标"""
        # 转换为绝对坐标
        abs_x = int(x * 65535 / self.screen_width)
        abs_y = int(y * 65535 / self.screen_height)
        win32api.mouse_event(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, abs_x, abs_y, 0, 0)

    def win32_key_press(self, key_code, shift=False):
        """使用win32api模拟按键"""
        if shift:
            win32api.keybd_event(win32con.VK_SHIFT, 0, 0, 0)
        
        win32api.keybd_event(key_code, 0, 0, 0)
        time.sleep(0.01)
        win32api.keybd_event(key_code, 0, win32con.KEYEVENTF_KEYUP, 0)
        
        if shift:
            win32api.keybd_event(win32con.VK_SHIFT, 0, win32con.KEYEVENTF_KEYUP, 0)

    def on_exit(self):
        self.is_running = False
        self.tray_icon.stop()
        self.listener.stop()
        sys.exit(0)

    def on_press(self, key):
        try:
            if key == keyboard.Key.f2 and self.on_ctrl:
                self.is_clicking = False
                self.stop_operate = True

            # 检测 Ctrl 键
            elif key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
                self.on_ctrl = True

            # 检测 Alt 键
            elif key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
                self.on_alt = True

            # Ctrl + F4 退出
            elif key == keyboard.Key.f4 and self.on_ctrl:
                self.on_exit()

            if self.auto_buy:
                return

            # 在执行任何操作前检查窗口是否激活
            # if not self.is_target_window_active():
            #     self.tray_icon.notify("请先激活游戏窗口", "操作失败")
            #     return
            
            # ctrl + F1 开始点击
            if key == keyboard.Key.f1 and self.on_ctrl:
                self.is_clicking = True
                # self.tray_icon.notify("自动点击已启动", "状态")

            # Ctrl + F9 获取坐标
            elif key == keyboard.Key.f9 and self.on_ctrl:
                self.current_pos = win32api.GetCursorPos()
                print(f"当前坐标:  {self.current_pos}。{self.current_pos.x}, {self.current_pos.y}")
                self.tray_icon.notify(f"当前坐标: {self.current_pos}", "坐标信息")

            # Ctrl + F5 购买
            elif key == keyboard.Key.f5 and self.on_ctrl:
                self.tray_icon.notify("攻击免疫", "药水")
                buy_thread = threading.Thread(target=self.simulate_shift_right_click, daemon=True, args=(self.position1,))
                buy_thread.start()

            # Ctrl + F6 购买
            elif key == keyboard.Key.f6 and self.on_ctrl:
                self.tray_icon.notify("小吸红", "药水")
                buy_thread = threading.Thread(target=self.simulate_shift_right_click, daemon=True, args=(self.position2,))
                buy_thread.start()
            
            # Ctrl + F7 购买
            elif key == keyboard.Key.f7 and self.on_ctrl:
                self.tray_icon.notify("属性免疫", "药水")
                buy_thread = threading.Thread(target=self.simulate_shift_right_click, daemon=True, args=(self.position3,))
                buy_thread.start()
            
            elif key == keyboard.Key.f1 and self.on_alt:
                current_pos = win32api.GetCursorPos()

                time.sleep(0.05)
                self.win32_click(button='left')

                time.sleep(0.05)
                self.win32_move(1862, 1268)
                time.sleep(0.05)
                self.win32_click(button='left')
                time.sleep(0.05)

                self.win32_move(current_pos.x, current_pos.y)
            
            elif key == keyboard.Key.f2 and self.on_alt:
                current_pos = win32api.GetCursorPos()

                time.sleep(0.05)
                self.win32_move(1031, 1480)
                time.sleep(0.05)
                self.win32_click(button='left')

                time.sleep(0.05)
                self.win32_move(1854, 1265)
                time.sleep(0.05)
                self.win32_click(button='left')

                time.sleep(0.05)
                self.win32_move(current_pos.x, current_pos.y)

            elif key == keyboard.Key.f3 and self.on_alt:
                print('into')
                hwnd = win32gui.GetForegroundWindow()
                print('self', hwnd)
                self.target_window_title = win32gui.GetWindowText(hwnd)
                print('self', self.target_window_title)
                self.activate_target_window()
            
        except AttributeError:
            self.tray_icon.notify('error')
            pass

    def on_release(self, key):
        try:
            if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
                self.on_ctrl = False
            elif key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
                self.on_alt = False
        except AttributeError:
            pass

    def auto_click(self):
        while self.is_running:
            if self.is_clicking:
                # 只有在目标窗口激活时才执行点击
                if self.is_target_window_active():
                    x, y =win32api.GetCursorPos()
                    self.win32_click(x=x, y=y, button='left')
                    time.sleep(0.01)  # 点击间隔
                else:
                    time.sleep(0.1)
            else:
                time.sleep(0.1)

    def simulate_shift_right_click(self, position):
        self.stop_operate = False
        try:
            time.sleep(0.5)
            self.auto_buy = True
            
            # 确保目标窗口激活
            if not self.is_target_window_active():
                self.tray_icon.notify("操作失败: 游戏窗口未激活", "错误")
                self.auto_buy = False
                return

            for i in range(10):
                for j in range(3):
                    x, y = position[j]
                    if self.stop_operate:
                        self.auto_buy = False
                        return

                    # 使用win32api移动和点击
                    self.win32_move(x, y)
                    time.sleep(0.05)

                    # 按下Shift+右键
                    win32api.keybd_event(win32con.VK_SHIFT, 0, 0, 0)
                    time.sleep(0.05)
                    self.win32_click(button='right')
                    time.sleep(0.05)
                    win32api.keybd_event(win32con.VK_SHIFT, 0, win32con.KEYEVENTF_KEYUP, 0)

                    # 输入999
                    for num in ['9', '9', '9']:
                        self.win32_key_press(ord(num))
                        time.sleep(0.01)

                    time.sleep(0.05)
                    self.win32_move(1906, 717)
                    self.win32_click(button='left')
                time.sleep(0.05)

            self.auto_buy = False
        except Exception as e:
            self.auto_buy = False
            self.tray_icon.notify(f"操作失败: {str(e)}", "错误")

if __name__ == "__main__":
    AutoClicker()
