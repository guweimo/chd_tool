import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import keyboard
import win32api
import win32con
import win32gui
import threading
import time
import json
import os
import ctypes
import platform
from PIL import ImageGrab


class InputSimulator:
    @staticmethod
    def send_key(hwnd, key_code, press=True):
        """发送键盘按键消息到指定窗口"""
        if press:
            win32gui.SendMessage(hwnd, win32con.WM_KEYDOWN, key_code, 0)
        else:
            win32gui.SendMessage(hwnd, win32con.WM_KEYUP, key_code, 0)

    @staticmethod
    def send_text(hwnd, text):
        """模拟文本输入到指定窗口"""
        for char in text:
            # 发送字符消息
            win32gui.SendMessage(hwnd, win32con.WM_CHAR, ord(char), 0)
            time.sleep(0.01)  # 短暂延迟确保输入顺序正确

    @staticmethod
    def send_click(hwnd, x, y):
        """模拟鼠标点击"""
        lparam = win32api.MAKELONG(x, y)
        # 移动鼠标
        win32gui.SendMessage(hwnd, win32con.WM_MOUSEMOVE, 0, lparam)
        # 按下左键
        win32gui.SendMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
        time.sleep(0.05)
        # 释放左键
        win32gui.SendMessage(hwnd, win32con.WM_LBUTTONUP, 0, lparam)


class DPI_AwareWindow:
    def __init__(self, root):
        self.root = root
        self.setup_dpi_awareness()
        self.setup_ui_scaling()

    def setup_dpi_awareness(self):
        """设置DPI感知"""
        if platform.system() == 'Windows':
            try:
                # 尝试设置最高级别的DPI感知
                ctypes.windll.shcore.SetProcessDpiAwareness(1)  # PER_MONITOR_DPI_AWARE
            except:
                try:
                    # 回退到系统级别的DPI感知
                    ctypes.windll.user32.SetProcessDPIAware()
                except:
                    pass

    def setup_ui_scaling(self):
        """根据DPI设置UI缩放比例"""
        if platform.system() == 'Windows':
            try:
                # 获取系统DPI缩放比例
                self.dpi = ctypes.windll.user32.GetDpiForWindow(self.root.winfo_id())
                self.scaling = self.dpi / 96.0  # 96是100%缩放的标准DPI
                # from ctypes import windll
                # windll.shcore.SetProcessDpiAwareness(1)
                # hdc = windll.user32.GetDC(0)
                # scaling = windll.gdi32.GetDeviceCaps(hdc, 88) / 96  # 88=LOGPIXELSX
                # windll.user32.ReleaseDC(0, hdc)
                # self.scaling = max(1.0, scaling)
            except:
                self.scaling = 1.0
        else:
            self.scaling = 1.0

    def scale(self, size):
        """根据DPI缩放比例调整尺寸"""
        return int(size * self.scaling)


class WindowAutomator(DPI_AwareWindow):
    def __init__(self, root):
        super().__init__(root)
        self.running = False
        self.target_hwnd = None
        self.window_list = []
        self.coords = {1: None, 2: None, 3: None}
        self.config_file = "window_automator_config.json"
        
        self.screenshot_var = tk.BooleanVar(value=False)
        self.screenshot_dir = "screenshots"
        os.makedirs(self.screenshot_dir, exist_ok=True)

        
        # 设置字体
        self.font_normal = ('Microsoft YaHei', self.scale(10))
        self.font_large = ('Microsoft YaHei', self.scale(12))
        self.font_small = ('Microsoft YaHei', self.scale(9))
        
        # 初始化UI
        self.init_ui()
        
        # 加载保存的配置
        self.load_config()
        
        # 刷新窗口列表
        self.refresh_window_list()
        
        # 绑定快捷键
        keyboard.add_hotkey('alt+1', lambda: self.capture_coord(1))
        keyboard.add_hotkey('alt+2', lambda: self.capture_coord(2))
        keyboard.add_hotkey('alt+3', lambda: self.capture_coord(3))
    
    def init_ui(self):
        """初始化用户界面"""
        self.root.title("自动激活工具 ")
        
        # 设置窗口大小（根据DPI缩放）
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = self.scale(min(1200, screen_width - 100))
        window_height = self.scale(min(800, screen_height - 100))
        self.root.geometry(f"{window_width}x{window_height}")

        self.root.minsize(self.scale(800), self.scale(600))
        
        # 主框架 - 使用PanedWindow实现可调整大小的分割
        main_paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashwidth=self.scale(5))
        main_paned.pack(fill=tk.BOTH, expand=True)
        
        # 左侧控制面板（占50%宽度）
        control_frame = ttk.Frame(main_paned)
        main_paned.add(control_frame, width=int(window_width*0.5), stretch="always")
        
        # 右侧日志区域（占50%宽度）
        log_frame = ttk.LabelFrame(main_paned, text="执行日志")
        main_paned.add(log_frame, width=int(window_width*0.5), stretch="always")
        
        # 日志区域内容
        self.log_text = scrolledtext.ScrolledText(
            log_frame, 
            wrap=tk.WORD, 
            state=tk.DISABLED,
            font=self.font_small,
            padx=self.scale(5),
            pady=self.scale(5)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 控制面板内容
        # 窗口选择
        window_frame = ttk.LabelFrame(control_frame, text="窗口选择", padding=self.scale(5))
        window_frame.pack(fill=tk.X, pady=self.scale(5))
        
        self.window_combobox = ttk.Combobox(
            window_frame, 
            state="readonly",
            font=self.font_normal
        )
        self.window_combobox.pack(fill=tk.X, padx=self.scale(5), pady=self.scale(5))
        
        btn_frame = ttk.Frame(window_frame)
        btn_frame.pack(fill=tk.X, pady=self.scale(5))
        
        ttk.Button(
            btn_frame, 
            text="刷新列表", 
            command=self.refresh_window_list,
            style="TButton"
        ).pack(side=tk.LEFT, padx=self.scale(2))
        ttk.Button(
            btn_frame, 
            text="绑定窗口", 
            command=self.bind_window,
            style="TButton"
        ).pack(side=tk.LEFT, padx=self.scale(2))
        
        # 坐标设置
        coord_frame = ttk.LabelFrame(control_frame, text="坐标设置 (Alt+1/2/3获取)", padding=self.scale(5))
        coord_frame.pack(fill=tk.X, pady=self.scale(5))
        
        self.coord_labels = {}
        for i in range(1, 4):
            frame = ttk.Frame(coord_frame)
            frame.pack(fill=tk.X, pady=self.scale(2))
            
            ttk.Label(frame, text=f"坐标{i}:", font=self.font_normal).pack(side=tk.LEFT)
            self.coord_labels[i] = ttk.Label(
                frame, 
                text="未设置", 
                foreground="red",
                font=self.font_normal
            )
            self.coord_labels[i].pack(side=tk.LEFT, padx=self.scale(5))
            ttk.Button(
                frame, 
                text="测试", 
                command=lambda i=i: self.test_coord(i),
                style="TButton"
            ).pack(side=tk.LEFT)
        
        # 添加截图选项
        screenshot_frame = ttk.Frame(control_frame)
        screenshot_frame.pack(fill=tk.X, pady=self.scale(5))

        
        # 截图复选框（左侧）
        ttk.Checkbutton(
            screenshot_frame,
            text="执行时截图保存",
            variable=self.screenshot_var,
            style="TCheckbutton",
            command=self.save_config,
        ).pack(side=tk.LEFT, padx=self.scale(5))

        # 提示标签（右侧）
        ttk.Label(
            screenshot_frame,
            text="⚠️ 勾选后截图激活状况并会激活窗口到最前，不然无法截到游戏界面",
            foreground="red",
            font=(self.font_normal[0], self.scale(10)),  # 比正文字体小一点
            wraplength=self.scale(500)  # 允许自动换行
        ).pack(side=tk.LEFT, padx=self.scale(10))
        
        # 延迟设置
        delay_frame = ttk.Frame(control_frame)
        delay_frame.pack(fill=tk.X, pady=self.scale(5))
        
        ttk.Label(delay_frame, text="点击延迟:", font=self.font_normal).pack(side=tk.LEFT)
        self.click_delay = tk.DoubleVar(value=0.5)
        ttk.Spinbox(
            delay_frame, 
            from_=0.1, 
            to=5, 
            increment=0.1, 
            textvariable=self.click_delay, 
            width=self.scale(5),
            font=self.font_normal,
            command=self.save_config,
        ).pack(side=tk.LEFT, padx=self.scale(5))
        
        ttk.Label(delay_frame, text="输入延迟:", font=self.font_normal).pack(side=tk.LEFT)
        self.input_delay = tk.DoubleVar(value=0.3)
        ttk.Spinbox(
            delay_frame, 
            from_=0.1, 
            to=5, 
            increment=0.1, 
            textvariable=self.input_delay, 
            width=self.scale(5),
            font=self.font_normal,
            command=self.save_config,
        ).pack(side=tk.LEFT, padx=self.scale(5))
        
        # 配置操作
        config_frame = ttk.Frame(control_frame)
        config_frame.pack(fill=tk.X, pady=self.scale(5))
        
        # 操作按钮
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill=tk.X, pady=self.scale(10))
        
        ttk.Button(
            btn_frame, 
            text="开始执行", 
            command=self.start_execution,
            style="Large.TButton"
        ).pack(side=tk.LEFT, padx=self.scale(5))
        ttk.Button(
            btn_frame, 
            text="停止执行", 
            command=self.stop_execution,
            style="Large.TButton"
        ).pack(side=tk.LEFT, padx=self.scale(5))
        
        # 输入区域
        input_frame = ttk.LabelFrame(
            control_frame, 
            text="输入内容 (每行一条)", 
            padding=self.scale(5)
        )
        input_frame.pack(fill=tk.BOTH, expand=True)
        
        self.input_text = scrolledtext.ScrolledText(
            input_frame, 
            wrap=tk.WORD,
            font=self.font_normal,
            padx=self.scale(5),
            pady=self.scale(5)
        )
        self.input_text.pack(fill=tk.BOTH, expand=True)
        
        # 配置样式
        self.setup_styles()
    
    def setup_styles(self):
        """配置UI样式"""
        style = ttk.Style()
        
        # 普通按钮样式
        style.configure("TButton", 
                       font=self.font_normal,
                       padding=self.scale(5))
        
        # 大按钮样式
        style.configure("Large.TButton", 
                       font=self.font_large,
                       padding=self.scale(8))
        
        # 组合框样式
        style.configure("TCombobox", 
                       font=self.font_normal)
        
        # 标签样式
        style.configure("TLabel", 
                       font=self.font_normal)
        
        # 标签框架标题样式（新增）
        style.configure("TLabelframe.Label", 
                    font=self.font_large)  # 使用大号字体

        # 框架样式
        style.configure("TLabelframe", 
                       font=self.font_normal)
        
        style.configure('TCheckbutton', 
                    font=self.font_normal,
                    padding=self.scale(3))

        # 调整所有控件的默认字体
        self.root.option_add("*Font", self.font_normal)

    def load_config(self):
        """从JSON文件加载配置"""
        if not os.path.exists(self.config_file):
            self.log("没有找到配置文件，使用默认设置")
            return
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            # 加载延迟设置
            self.click_delay.set(config.get('click_delay', 0.5))
            self.input_delay.set(config.get('input_delay', 0.3))
            # 加载截图选项
            self.screenshot_var.set(config.get('screenshot_enabled', False))

            # 加载坐标设置
            saved_coords = config.get('coords', {})
            for i in range(1, 4):
                if str(i) in saved_coords:
                    self.coords[i] = tuple(saved_coords[str(i)])
                    self.coord_labels[i].config(text=f"{self.coords[i]}", foreground="green")
            
            self.log("配置已从文件加载")
        except Exception as e:
            self.log(f"加载配置文件失败: {str(e)}")
    
    def save_config(self):
        """保存配置到JSON文件"""
        try:
            config = {
                'click_delay': self.click_delay.get(),
                'input_delay': self.input_delay.get(),
                'screenshot_enabled': self.screenshot_var.get(), 
                'coords': {},
            }
            
            # 保存坐标
            for i in range(1, 4):
                if self.coords[i]:
                    config['coords'][str(i)] = list(self.coords[i])
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            
            self.log("配置已保存到文件")
        except Exception as e:
            self.log(f"保存配置文件失败: {str(e)}")
    
    def log(self, message):
        """记录日志"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def refresh_window_list(self):
        """刷新窗口列表"""
        self.window_list = []
        
        def enum_windows_callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title and "LaTale Client" in title:
                    self.window_list.append({
                        'hwnd': hwnd,
                        'title': title,
                        'class': win32gui.GetClassName(hwnd)
                    })
        
        win32gui.EnumWindows(enum_windows_callback, None)
        
        # 更新下拉框
        if self.window_list:
            titles = [f"{win['title']} [{win['class']}]" for win in self.window_list]
            self.window_combobox['values'] = titles
            self.log(f"找到 {len(self.window_list)} 个LaTale客户端窗口")
        else:
            self.window_combobox['values'] = []
            self.log("未找到LaTale客户端窗口")

    
    def bind_window(self):
        """绑定选中的窗口"""
        selection = self.window_combobox.current()
        if selection == -1:
            messagebox.showwarning("警告", "请先选择一个窗口")
            return
        
        self.target_hwnd = self.window_list[selection]['hwnd']
        title = self.window_list[selection]['title']
        self.log(f"已绑定窗口: {title}")
        
        # 获取窗口位置
        try:
            left, top, right, bottom = win32gui.GetWindowRect(self.target_hwnd)
            width = right - left
            height = bottom - top
            self.log(f"窗口位置: 左={left}, 上={top}, 宽={width}, 高={height}")
        except Exception as e:
            self.log(f"获取窗口信息失败: {str(e)}")
        
    def get_window_client_rect(self, hwnd):
        """获取窗口客户区矩形（排除边框和标题栏）"""
        try:
            # 获取窗口矩形
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            
            # 计算客户区矩形
            client_left, client_top, client_right, client_bottom = win32gui.GetClientRect(hwnd)
            client_left, client_top = win32gui.ClientToScreen(hwnd, (client_left, client_top))
            client_right, client_bottom = win32gui.ClientToScreen(hwnd, (client_right, client_bottom))
            
            # 计算边框和标题栏的偏移量
            border_width = left - client_left
            title_bar_height = client_top - top - border_width
            
            return {
                'window_rect': (left, top, right, bottom),
                'client_rect': (client_left, client_top, client_right, client_bottom),
                'border_width': border_width,
                'title_bar_height': title_bar_height
            }
        except Exception as e:
            self.log(f"获取窗口客户区失败: {str(e)}")
            return None

    def capture_window_screenshot(self, prefix=""):
        """捕获窗口截图并保存"""
        if not self.target_hwnd:
            return None
        
        try:
            # 获取窗口位置和尺寸
            left, top, right, bottom = win32gui.GetWindowRect(self.target_hwnd)
            width = right - left
            height = bottom - top
            
            # 使用PIL捕获窗口
            screenshot = ImageGrab.grab(bbox=(left, top, right, bottom))
            
            # 生成带时间戳的文件名
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"{prefix}{timestamp}.png"
            filepath = os.path.join(self.screenshot_dir, filename)
            
            # 保存截图
            screenshot.save(filepath)
            self.log(f"截图已保存: {filepath}")
            return filepath
            
        except Exception as e:
            self.log(f"截图失败: {str(e)}")
            return None


    def capture_coord(self, coord_num):
        """捕获坐标点（改进版，考虑窗口边框）"""
        if not self.target_hwnd:
            self.log("错误: 请先绑定窗口")
            return
        
        # 获取鼠标位置
        x, y = win32api.GetCursorPos()
        
        # 获取窗口客户区信息
        window_info = self.get_window_client_rect(self.target_hwnd)
        if not window_info:
            self.log("错误: 无法获取窗口客户区信息")
            return
        
        # 计算相对于客户区的坐标
        rel_x = x - window_info['client_rect'][0]
        rel_y = y - window_info['client_rect'][1]
        
        # 保存坐标
        self.coords[coord_num] = (rel_x, rel_y)
        self.coord_labels[coord_num].config(text=f"({rel_x}, {rel_y})", foreground="green")
        self.log(f"已设置坐标{coord_num}: ({rel_x}, {rel_y})")
        self.log(f"窗口边框宽度: {window_info['border_width']}, 标题栏高度: {window_info['title_bar_height']}")
        self.save_config()
        self.log("坐标已自动保存")

    def test_coord(self, coord_num):
        """测试坐标点（改进版，考虑窗口边框）"""
        if not self.coords[coord_num]:
            self.log(f"错误: 坐标{coord_num}未设置")
            return
        
        if not self.target_hwnd:
            self.log("错误: 请先绑定窗口")
            return
        
        rel_x, rel_y = self.coords[coord_num]
        
        try:
            # 获取窗口客户区信息
            window_info = self.get_window_client_rect(self.target_hwnd)
            if not window_info:
                self.log("错误: 无法获取窗口客户区信息")
                return
            
            InputSimulator.send_click(self.target_hwnd, rel_x, rel_y)
            
            self.log(f"已测试坐标{coord_num}: ({rel_x}, {rel_y})")
        except Exception as e:
            self.log(f"测试坐标失败: {str(e)}")
        
    def start_execution(self):
        """开始执行自动化任务"""
        if self.running:
            return
        
        # 验证设置
        if not self.target_hwnd:
            self.log("错误: 请先绑定窗口")
            return
        
        if not self.coords[1] or not self.coords[2]:
            self.log("错误: 请设置坐标1和坐标2")
            return
        
        # 获取输入内容
        text = self.input_text.get("1.0", tk.END).strip()
        if not text:
            self.log("错误: 请输入要执行的内容")
            return
        
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        if not lines:
            self.log("错误: 没有有效的输入行")
            return
        
        # 在新线程中执行
        self.running = True
        threading.Thread(
            target=self.execute_automation,
            args=(lines,),
            daemon=True
        ).start()
    
    def stop_execution(self):
        """停止执行"""
        self.running = False
        self.log("正在停止执行...")
    
    def execute_automation(self, lines):
        """执行自动化任务"""
        coord1 = self.coords[1]
        coord2 = self.coords[2]
        coord3 = self.coords[3]
        
        try:
            # 激活窗口
            if self.screenshot_var.get():
                win32gui.ShowWindow(self.target_hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(self.target_hwnd)

            for i, line in enumerate(lines):
                if not self.running:
                    break
                
                self.log(f"正在处理第 {i+1}/{len(lines)} 行: {line[:20]}...")
                
                # 1. 点击第一个坐标
                InputSimulator.send_click(self.target_hwnd, coord1[0], coord1[1])
                
                time.sleep(0.1)
                # 2. 输入激活码
                InputSimulator.send_text(self.target_hwnd, line)
                
                time.sleep(self.input_delay.get())
                
                # 3. 点击第二个坐标
                InputSimulator.send_click(self.target_hwnd, coord2[0], coord2[1])
                time.sleep(self.click_delay.get())
                
                # 4. 如果勾选了截图选项，则保存截图
                if self.screenshot_var.get():
                    self.capture_window_screenshot(prefix=f"step_{i+1}_{line}_")

                time.sleep(self.click_delay.get())
                InputSimulator.send_click(self.target_hwnd, coord3[0], coord3[1])

                self.log(f"第 {i+1} 行处理完成")
            
            if self.running:
                self.log("所有行处理完成")
        except Exception as e:
            self.log(f"执行过程中出错: {str(e)}")
        finally:
            self.running = False


if __name__ == "__main__":
    root = tk.Tk()
    app = WindowAutomator(root)
    root.mainloop()