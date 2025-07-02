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
        # 线程控制事件
        self._stop_event = threading.Event()  # 主停止事件
        self._click_event = threading.Event() # 点击控制事件
        self._buy_lock = threading.Lock()    # 购买操作锁
        
        # 状态变量
        self.on_ctrl = False
        self.current_pos = (0, 0)
        self.active_buy_threads = []  # 跟踪所有购买线程
        
        # 坐标配置（保持不变）
        self.position1 = [[1664, 876], [1713, 1050], [2088, 939]]
        self.position2 = [[1664, 936], [2065, 824], [2065, 997]]
        self.position3 = [[1652, 821], [1678, 998], [2075, 880]]

        # 初始化线程和托盘
        self._init_threads()
        self._init_tray()

    def _init_threads(self):
        """初始化并启动所有线程"""
        # 键盘监听线程
        self.listener_thread = threading.Thread(
            target=self._keyboard_listener,
            daemon=True
        )
        
        # 自动点击线程
        self.click_thread = threading.Thread(
            target=self._auto_click,
            daemon=True
        )
        
        self.listener_thread.start()
        self.click_thread.start()

    def _init_tray(self):
        """初始化系统托盘"""
        try:
            image = Image.open("c:/project/auto_operate/icon.png")
        except FileNotFoundError:
            image = Image.new('RGB', (64, 64), (30, 144, 255))
            
        menu = Menu(
            MenuItem('强制停止所有操作', self._emergency_stop),
            MenuItem('退出程序', self.graceful_stop),
            MenuItem('当前位置', lambda: f"{self.current_pos}"),
            MenuItem('--- 快捷操作 ---', None),
            MenuItem('Ctrl+F1 自动点击', None),
            MenuItem('Ctrl+F2 取消自动', None),
            MenuItem('Ctrl+F5 攻击免疫', None),
            MenuItem('Ctrl+F6 小吸红', None),
            MenuItem('Ctrl+F7 属性免疫', None),
        )
        
        self.tray_icon = Icon("AutoClicker", image, "自动操作工具", menu)
        self.tray_icon.run()

    def _keyboard_listener(self):
        """键盘监听线程"""
        with keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        ) as listener:
            while not self._stop_event.is_set():
                listener.join(0.5)  # 每0.5秒检查停止事件

    def _auto_click(self):
        """自动点击线程"""
        while not self._stop_event.is_set():
            if self._click_event.is_set():
                pyautogui.click()
                time.sleep(0.01)
            else:
                time.sleep(0.1)

    def _on_press(self, key):
        """键盘按下事件处理（优化版）"""
        if self._stop_event.is_set():
            return

        try:
            # 检测Ctrl键状态
            if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
                self.on_ctrl = True
                return

            # 组合键处理
            if self.on_ctrl:
                match key:
                    case keyboard.Key.f1:
                        self._click_event.set()
                        self.tray_icon.notify("自动点击已启动", "状态")
                    
                    case keyboard.Key.f2:
                        self._click_event.clear()
                        self.tray_icon.notify("自动点击已停止", "状态")
                    
                    case keyboard.Key.f5:
                        self._start_buy_thread(self.position1, "攻击免疫")
                    
                    case keyboard.Key.f6:
                        self._start_buy_thread(self.position2, "小吸红")
                    
                    case keyboard.Key.f7:
                        self._start_buy_thread(self.position3, "属性免疫")
                    
                    case keyboard.Key.f9:
                        self.current_pos = pyautogui.position()
                        self.tray_icon.notify(f"当前坐标: {self.current_pos}", "坐标信息")
                    
                    case keyboard.Key.f4:
                        self.graceful_stop()

        except AttributeError:
            pass

    def _on_release(self, key):
        """键盘释放事件处理"""
        if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            self.on_ctrl = False

    def _start_buy_thread(self, positions, name):
        """安全启动购买线程"""
        if not self._buy_lock.acquire(blocking=False):
            self.tray_icon.notify("已有购买操作在进行中", "警告")
            return

        try:
            thread = threading.Thread(
                target=self._safe_shift_click,
                args=(positions, name),
                daemon=True
            )
            self.active_buy_threads.append(thread)
            thread.start()
        finally:
            self._buy_lock.release()

    def _safe_shift_click(self, positions, name):
        """带异常处理的购买操作"""
        try:
            self.tray_icon.notify(f"开始购买: {name}", "药水")
            for j in range(3):
                for pos in positions:
                    if self._stop_event.is_set():
                        return
                    
                    x, y = pos
                    pyautogui.moveTo(x, y)
                    with self.key_controller.pressed(Key.shift):
                        time.sleep(0.1)
                        self.mouse_controller.click(Button.right)
                        time.sleep(0.1)
                    pyautogui.typewrite('999')
                    pyautogui.moveTo(1906, 717)
                    pyautogui.click()
                time.sleep(0.2)
        except Exception as e:
            self.tray_icon.notify(f"操作失败: {str(e)}", "错误")
        finally:
            self.active_buy_threads = [t for t in self.active_buy_threads if t.is_alive()]

    def graceful_stop(self, icon=None, item=None):
        """安全停止所有操作"""
        # 设置停止事件
        self._stop_event.set()
        self._click_event.clear()

        # 等待线程结束
        self._wait_for_threads()

        # 清理资源
        if icon:
            icon.stop()
        sys.exit(0)

    def _emergency_stop(self, icon=None, item=None):
        """紧急停止所有操作"""
        self._stop_event.set()
        self._click_event.clear()
        
        # 终止所有购买线程
        with self._buy_lock:
            for t in self.active_buy_threads:
                if t.is_alive():
                    t.join(0.5)  # 给线程0.5秒完成清理

        self.tray_icon.notify("已强制终止所有操作", "系统")
        self._click_event.clear()

    def _wait_for_threads(self, timeout=3):
        """等待线程结束"""
        start_time = time.time()
        for t in [self.listener_thread, self.click_thread] + self.active_buy_threads:
            remaining_time = timeout - (time.time() - start_time)
            if remaining_time <= 0:
                break
            t.join(remaining_time)

if __name__ == "__main__":
    ac = AutoClicker()
