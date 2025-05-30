import threading
import pyautogui
from pynput import keyboard
from pynput.keyboard import Key, Controller as KeyController
from pynput.mouse import Button, Controller as MouseController
from pystray import Icon, Menu, MenuItem
from PIL import Image
import time
import sys

class AutoClicker:
    def __init__(self):
        self.is_clicking = False
        self.is_running = True
        self.on_ctrl = False
        self.on_alt = False
        self.auto_buy = False
        self.stop_operate = False
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
        )
        return Icon("AutoClicker", image, "自动操作工具", menu)

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

            # 检测 Ctrl 键
            elif key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
                self.on_alt = True

            # Ctrl + F4 退出
            elif key == keyboard.Key.f4 and self.on_ctrl:
                self.on_exit()

            if self.auto_buy:
                return

            # ctrl + F1 开始点击
            if key == keyboard.Key.f1 and self.on_ctrl:
                self.is_clicking = True
                # self.tray_icon.notify("自动点击已启动", "状态")

            # # ctrl + F2 停止点击
            # elif key == keyboard.Key.f2 and self.on_ctrl:
            #     self.is_clicking = False
            #     self.stop_operate = True
            #     # self.tray_icon.notify("自动点击已停止", "状态")

            # Ctrl + F9 获取坐标
            elif key == keyboard.Key.f9 and self.on_ctrl:
                self.current_pos = pyautogui.position()
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
                current_pos = pyautogui.position()

                time.sleep(0.05)
                self.mouse_controller.click(Button.left)

                time.sleep(0.05)
                pyautogui.moveTo(1862, 1268)
                time.sleep(0.05)
                self.mouse_controller.click(Button.left)
                time.sleep(0.05)

                pyautogui.moveTo(current_pos.x, current_pos.y)
            

            elif key == keyboard.Key.f2 and self.on_alt:
                current_pos = pyautogui.position()

                time.sleep(0.05)
                pyautogui.moveTo(1031, 1480)
                time.sleep(0.05)
                self.mouse_controller.click(Button.left)

                time.sleep(0.05)
                pyautogui.moveTo(1854, 1265)
                time.sleep(0.05)
                self.mouse_controller.click(Button.left)

                time.sleep(0.05)
                pyautogui.moveTo(current_pos.x, current_pos.y)
            
            
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
                self.mouse_controller.click(Button.left)
                time.sleep(0.01)  # 点击间隔
            else:
                time.sleep(0.1)

    def simulate_shift_right_click(self, position):
        # print('position', position)
        self.stop_operate = False
        try:
            time.sleep(0.5)
            self.auto_buy = True
            for i in range(10):
                for j in range(3):
                    x, y = position[j]
                    if self.stop_operate:
                        self.auto_buy = False
                        return
                    pyautogui.moveTo(x, y)
                    time.sleep(0.05)
                    self.key_controller.press(Key.shift)
                    time.sleep(0.05)
                    self.mouse_controller.click(Button.right)
                    time.sleep(0.05)
                    self.key_controller.release(Key.shift)
                    time.sleep(0.05)
                    pyautogui.typewrite('999')
                    time.sleep(0.05)
                    pyautogui.moveTo(1906, 717)
                    pyautogui.click()
                time.sleep(0.05)

            self.auto_buy = False
        except Exception as e:
            self.auto_buy = False
            self.tray_icon.notify(f"操作失败: {str(e)}")

if __name__ == "__main__":
    AutoClicker()