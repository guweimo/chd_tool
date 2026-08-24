import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import psutil
import subprocess
import os
import json
import threading
import time
from datetime import datetime
import ctypes
from ctypes import wintypes
import win32gui
import win32con
import win32api
import win32process

import pyautogui
from pynput import keyboard
from pynput.keyboard import Key, Controller as KeyController
from pynput.mouse import Button, Controller as MouseController
from pystray import Icon, Menu, MenuItem
from PIL import Image
import sys

# Windows API常量定义
SW_HIDE = 0
SW_SHOW = 5
SW_RESTORE = 9

# Windows API类型定义
LRESULT = ctypes.c_long


def get_dpi_scale():
    """获取系统 DPI 缩放比例（96 DPI 为 100%，返回 1.0）"""
    try:
        hdc = ctypes.windll.user32.GetDC(0)
        dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX = 88
        ctypes.windll.user32.ReleaseDC(0, hdc)
        return dpi / 96.0
    except Exception:
        return 1.0


class AutoClickerMixin:
    """自动点击/购买功能混入类，提供快捷键操作和托盘通知能力"""

    def init_auto_clicker(self):
        """初始化自动点击器相关状态和线程"""
        # 线程控制事件
        self._stop_event = threading.Event()
        self._click_event = threading.Event()
        self._buy_lock = threading.Lock()

        # 状态变量
        self.on_ctrl = False
        self.on_alt = False
        self.auto_buy = False
        self.stop_operate = False
        self.current_pos = (0, 0)
        self.key_controller = KeyController()
        self.mouse_controller = MouseController()
        self.active_buy_threads = []

        # 坐标配置
        self.position1 = [[1664, 876], [1713, 1050], [2088, 939]]
        self.position2 = [[1664, 936], [2065, 824], [2065, 997]]
        self.position3 = [[1652, 821], [1678, 998], [2075, 880]]

        # 启动键盘监听和自动点击线程
        self.listener_thread = threading.Thread(target=self._keyboard_listener, daemon=True)
        self.click_thread = threading.Thread(target=self._auto_click, daemon=True)
        self.listener_thread.start()
        self.click_thread.start()

    # ---- 键盘监听 ----

    def _keyboard_listener(self):
        """键盘监听线程"""
        with keyboard.Listener(on_press=self._on_press, on_release=self._on_release) as listener:
            while not self._stop_event.is_set():
                listener.join(0.5)

    def _on_press(self, key):
        """键盘按下事件"""
        if self._stop_event.is_set():
            return

        try:
            # 检测 Ctrl 键
            if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
                self.on_ctrl = True
                return

            # 检测 Alt 键
            if key in (keyboard.Key.alt_l, keyboard.Key.alt_r):
                self.on_alt = True
                return

            if self.on_ctrl:
                if key == keyboard.Key.f1:
                    self._click_event.set()
                    self._tray_notify("自动点击已启动", "状态")

                elif key == keyboard.Key.f2:
                    self._click_event.clear()
                    self.stop_operate = True
                    self._tray_notify("自动点击已停止", "状态")

                elif key == keyboard.Key.f4:
                    self.on_exit()

                elif key == keyboard.Key.f5:
                    self._tray_notify("攻击免疫", "药水")
                    self._start_buy_thread(self.position1, "攻击免疫")

                elif key == keyboard.Key.f6:
                    self._tray_notify("小吸红", "药水")
                    self._start_buy_thread(self.position2, "小吸红")

                elif key == keyboard.Key.f7:
                    self._tray_notify("属性免疫", "药水")
                    self._start_buy_thread(self.position3, "属性免疫")

                elif key == keyboard.Key.f9:
                    self.current_pos = pyautogui.position()
                    self._tray_notify(f"当前坐标: {self.current_pos}", "坐标信息")

            if self.auto_buy:
                return

            # Alt 组合键
            if self.on_alt:
                if key == keyboard.Key.f1:
                    current_pos = pyautogui.position()
                    time.sleep(0.05)
                    self.mouse_controller.click(Button.left)
                    time.sleep(0.05)
                    pyautogui.moveTo(1862, 1268)
                    time.sleep(0.05)
                    self.mouse_controller.click(Button.left)
                    time.sleep(0.05)
                    pyautogui.moveTo(current_pos.x, current_pos.y)

                elif key == keyboard.Key.f2:
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
            pass

    def _on_release(self, key):
        """键盘释放事件"""
        try:
            if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
                self.on_ctrl = False
            elif key in (keyboard.Key.alt_l, keyboard.Key.alt_r):
                self.on_alt = False
        except AttributeError:
            pass

    # ---- 自动点击 ----

    def _auto_click(self):
        """自动点击线程"""
        while not self._stop_event.is_set():
            if self._click_event.is_set():
                self.mouse_controller.click(Button.left)
                time.sleep(0.01)
            else:
                time.sleep(0.1)

    # ---- 购买操作 ----

    def _start_buy_thread(self, positions, name):
        """安全启动购买线程"""
        if not self._buy_lock.acquire(blocking=False):
            self._tray_notify("已有购买操作在进行中", "警告")
            return

        try:
            thread = threading.Thread(
                target=self._simulate_shift_right_click,
                args=(positions, name),
                daemon=True
            )
            self.active_buy_threads.append(thread)
            thread.start()
        finally:
            self._buy_lock.release()

    def _simulate_shift_right_click(self, positions, name):
        """Shift+右键购买操作"""
        self.stop_operate = False
        try:
            time.sleep(0.5)
            self.auto_buy = True
            for i in range(3):
                for j in range(3):
                    x, y = positions[j]
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
                    pyautogui.typewrite('9999')
                    time.sleep(0.05)
                    pyautogui.moveTo(1906, 717)
                    pyautogui.click()
                time.sleep(0.05)
            self.auto_buy = False
        except Exception as e:
            self.auto_buy = False
            self._tray_notify(f"操作失败: {str(e)}", "错误")

    def _emergency_stop(self, icon=None, item=None):
        """紧急停止所有操作"""
        self._stop_event.set()
        self._click_event.clear()
        with self._buy_lock:
            for t in self.active_buy_threads:
                if t.is_alive():
                    t.join(0.5)
        self._tray_notify("已强制终止所有操作", "系统")
        self._click_event.clear()

    # ---- 托盘通知 ----

    def _tray_notify(self, message, title="提示"):
        """通过托盘图标发送通知（如果托盘存在）"""
        if hasattr(self, 'tray_icon') and self.tray_icon:
            try:
                self.tray_icon.notify(message, title)
            except Exception:
                pass


class RainbowIslandManager(tk.Tk, AutoClickerMixin):
    """彩虹岛应用管理器 + 自动点击器（合并版）"""

    def __init__(self):
        tk.Tk.__init__(self)
        self.title("彩虹岛管理器")

        # pyautogui 会自动启用 DPI 感知，导致 tkinter 窗口不再被 Windows
        # 位图拉伸而变小。这里按 DPI 比例放大窗口尺寸，恢复视觉大小。
        self._dpi_scale = get_dpi_scale()
        base_w, base_h = 800, 600
        self.geometry(f"{int(base_w * self._dpi_scale)}x{int(base_h * self._dpi_scale)}")
        self.minsize(int(base_w * self._dpi_scale), int(base_h * self._dpi_scale))

        # 按 DPI 放大全局字体，避免高 DPI 下字体过小
        if self._dpi_scale > 1.0:
            self._apply_dpi_font()

        # 应用数据存储
        self.applications = {}
        self.running_processes = {}
        self.data_file = self._get_data_path("rainbow_island_apps.json")

        # 选中的进程ID
        self.selected_pid = None

        # 窗口句柄缓存
        self.window_cache = {}
        self.last_cache_time = 0
        self.cache_ttl = 5
        self.hidden_windows = {}

        # 托盘图标
        self.tray_icon = None

        # 加载已有数据
        self.load_applications()

        # 创建界面
        self.create_widgets()

        # 初始化自动点击器
        self.init_auto_clicker()

        # 窗口关闭事件
        self.protocol("WM_DELETE_WINDOW", self._on_window_close)

        # 启动后台监控线程
        self.monitor_thread = threading.Thread(target=self.monitor_processes, daemon=True)
        self.monitor_thread.start()

        # 先显示主窗口，确保界面可见
        self._show_main_window()

        # 延迟启动托盘图标，避免托盘线程抢占主窗口显示时机
        self.after(200, self._init_tray)

    def _apply_dpi_font(self):
        """根据 DPI 比例放大全局默认字体（ttk 控件使用 ttk.Style 设置）"""
        scale = self._dpi_scale
        try:
            from tkinter.font import Font, families
            default_size = max(9, int(round(9 * scale)))
            # 选择系统支持的中文/默认字体
            family = "Microsoft YaHei UI" if "Microsoft YaHei UI" in families() else "TkDefaultFont"
            base_font = Font(family=family, size=default_size)

            # 通过 ttk.Style 设置所有 ttk 控件字体
            style = ttk.Style(self)
            style.configure(".", font=base_font)
            # Treeview 表头和内容字体、行高
            heading_size = max(9, int(round(10 * scale)))
            heading_font = Font(family=family, size=heading_size, weight="bold")
            style.configure("Treeview", font=base_font, rowheight=int(20 * scale))
            style.configure("Treeview.Heading", font=heading_font)
            # LabelFrame、Button、Label、Entry 等
            style.configure("TLabel", font=base_font)
            style.configure("TButton", font=base_font)
            style.configure("TLabelframe", font=base_font)
            style.configure("TLabelframe.Label", font=base_font)
            style.configure("TEntry", font=base_font)
            style.configure("TCombobox", font=base_font)

            # 标题专用样式（加粗，字号按 DPI 缩放）
            title_font = Font(family=family, size=max(14, int(round(16 * scale))), weight="bold")
            style.configure("Title.TLabel", font=title_font)

            # 同时通过 option_add 设置 tk 控件默认字体
            self.option_add("*Font", base_font)
        except Exception:
            pass

    def _show_main_window(self):
        """显示并聚焦主窗口"""
        self.deiconify()
        self.update()
        self.lift()
        self.focus_force()

    def _get_data_path(self, filename):
        """获取数据文件路径（兼容打包和开发环境）"""
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, filename)

    # ---- 托盘图标 ----

    def _init_tray(self):
        """初始化系统托盘图标"""
        def create_icon():
            try:
                icon_path = self._get_data_path("icon.png")
                image = Image.open(icon_path)
            except FileNotFoundError:
                image = Image.new('RGB', (64, 64), (30, 144, 255))

            menu = Menu(
                MenuItem('显示主窗口', self._show_window),
                MenuItem('强制停止所有操作', self._emergency_stop),
                MenuItem('退出程序', self.on_exit),
                MenuItem('当前位置', lambda: f"{self.current_pos}"),
                MenuItem('--- 快捷键说明 ---', None),
                MenuItem('Ctrl+F1 自动点击', None),
                MenuItem('Ctrl+F2 取消自动', None),
                MenuItem('Ctrl+F4 退出程序', None),
                MenuItem('Ctrl+F5 攻击免疫', None),
                MenuItem('Ctrl+F6 小吸红', None),
                MenuItem('Ctrl+F7 属性免疫', None),
                MenuItem('Ctrl+F9 获取坐标', None),
            )

            self.tray_icon = Icon("RainbowIslandManager", image, "彩虹岛管理器", menu)
            self.tray_icon.run()

        # 在独立线程中运行托盘图标
        self.tray_thread = threading.Thread(target=create_icon, daemon=True)
        self.tray_thread.start()

    def _show_window(self, icon=None, item=None):
        """从托盘显示主窗口"""
        self.after(0, lambda: (
            self.deiconify(),
            self.lift(),
            self.attributes('-topmost', True),
            self.attributes('-topmost', False)
        ))

    def _on_window_close(self):
        """点击窗口关闭按钮时最小化到托盘"""
        self.withdraw()

    # ---- 退出 ----

    def on_exit(self, icon=None, item=None):
        """退出程序"""
        self._stop_event.set()
        self._click_event.clear()

        # 停止键盘监听
        try:
            self.listener_thread.join(1)
        except Exception:
            pass

        # 停止托盘
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass

        # 退出
        self.after(0, self.destroy)
        sys.exit(0)

    # ---- GUI 界面 ----

    def create_widgets(self):
        """创建界面"""
        scale = getattr(self, '_dpi_scale', 1.0)
        # padding 按 DPI 缩放，确保高 DPI 下内边距视觉比例与原版一致
        pad = max(5, int(round(10 * scale)))
        # 按钮内部 padding 和按钮间距按 DPI 缩放
        btn_ipadx = max(8, int(round(12 * scale)))
        btn_padx = max(8, int(round(10 * scale)))

        # 主框架
        main_frame = ttk.Frame(self, padding=str(pad))
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 标题（字号固定 16，与原版 tray.py 配置一致）
        title_label = ttk.Label(main_frame, text="彩虹岛管理器", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=4, pady=(0, 20))

        # 控制按钮区域
        control_frame = ttk.LabelFrame(main_frame, text="控制面板", padding=str(pad))
        control_frame.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(0, 10))

        # 扫描按钮
        scan_btn = ttk.Button(control_frame, text="扫描所有相关程序", command=self.scan_applications)
        scan_btn.grid(row=0, column=0, padx=(0, btn_padx), ipadx=btn_ipadx)

        # 添加应用按钮
        add_btn = ttk.Button(control_frame, text="添加应用", command=self.add_application)
        add_btn.grid(row=0, column=1, padx=(0, btn_padx), ipadx=btn_ipadx)

        # 刷新按钮
        refresh_btn = ttk.Button(control_frame, text="刷新状态", command=self.refresh_status)
        refresh_btn.grid(row=0, column=2, ipadx=btn_ipadx)

        # 应用列表区域
        list_frame = ttk.LabelFrame(main_frame, text="进程实例列表", padding=str(pad))
        list_frame.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))

        # 进程列表表格
        columns = ("应用名称", "路径", "状态", "进程ID", "操作")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)

        scale = getattr(self, '_dpi_scale', 1.0)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=int(120 * scale))

        self.tree.column("路径", width=int(200 * scale))
        self.tree.column("进程ID", width=int(80 * scale))
        self.tree.column("操作", width=int(150 * scale))

        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.tree.configure(yscrollcommand=scrollbar.set)

        # 状态栏
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=3, column=0, columnspan=4, sticky=(tk.W, tk.E))

        self.status_label = ttk.Label(status_frame, text="就绪")
        self.status_label.grid(row=0, column=0, sticky=tk.W)

        # 配置网格权重
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        # 绑定右键事件
        self.tree.bind("<Button-3>", self.on_right_click)

        # 初始填充数据
        self.refresh_treeview()

    # ---- 数据加载/保存 ----

    def load_applications(self):
        """从文件加载应用数据"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.applications = json.load(f)
            except:
                self.applications = {}

    def save_applications(self):
        """保存应用数据到文件"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.applications, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("错误", f"保存数据失败: {e}")

    # ---- 扫描/添加应用 ----

    def scan_applications(self):
        """扫描所有相关程序"""
        self.status_label.config(text="正在扫描程序...")
        threading.Thread(target=self._scan_applications_thread, daemon=True).start()

    def _scan_applications_thread(self):
        """扫描程序的线程函数"""
        try:
            rainbow_keywords = ['LataleClient_x64']
            found_processes = []

            for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
                try:
                    proc_info = proc.info
                    name_lower = proc_info['name'].lower() if proc_info['name'] else ""
                    cmdline = " ".join(proc_info['cmdline']) if proc_info['cmdline'] else ""

                    for keyword in rainbow_keywords:
                        if keyword.lower() in name_lower:
                            found_processes.append({
                                'pid': proc_info['pid'],
                                'name': proc_info['name'],
                                'path': proc_info['exe'],
                                'cmdline': cmdline
                            })
                            break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            for proc_info in found_processes:
                app_name = proc_info['name']
                if app_name not in self.applications:
                    self.applications[app_name] = {
                        'name': app_name,
                        'path': proc_info['path'],
                        'description': f"自动扫描发现的进程: {proc_info['cmdline'][:100]}",
                        'created_time': datetime.now().isoformat()
                    }

            self.save_applications()
            self.refresh_treeview()
            self.status_label.config(text=f"扫描完成，发现 {len(found_processes)} 个相关进程")

        except Exception as e:
            self.status_label.config(text=f"扫描失败: {e}")

    def add_application(self):
        """手动添加应用"""
        file_path = filedialog.askopenfilename(
            title="选择应用程序",
            filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")]
        )

        if file_path:
            app_name = os.path.basename(file_path)
            if app_name not in self.applications:
                self.applications[app_name] = {
                    'name': app_name,
                    'path': file_path,
                    'description': "手动添加的应用",
                    'created_time': datetime.now().isoformat()
                }
                self.save_applications()
                self.refresh_treeview()
                self.status_label.config(text=f"已添加应用: {app_name}")
            else:
                messagebox.showinfo("提示", "该应用已存在")

    def refresh_status(self):
        """刷新进程状态"""
        self.refresh_treeview()
        self.status_label.config(text="状态已刷新")

    def refresh_treeview(self):
        """刷新树形视图"""
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.running_processes = {}
        rainbow_keywords = ['LataleClient_x64']

        for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline', 'create_time']):
            try:
                proc_info = proc.info
                name_lower = proc_info['name'].lower() if proc_info['name'] else ""
                cmdline = " ".join(proc_info['cmdline']) if proc_info['cmdline'] else ""

                for keyword in rainbow_keywords:
                    if keyword.lower() in name_lower:
                        pid = proc_info['pid']
                        self.running_processes[pid] = {
                            'pid': pid,
                            'name': proc_info['name'],
                            'path': proc_info['exe'],
                            'cmdline': cmdline,
                            'create_time': proc_info['create_time'],
                            'status': '运行中'
                        }
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        for pid, proc_info in self.running_processes.items():
            item = self.tree.insert("", "end", values=(
                proc_info['name'],
                proc_info['path'],
                proc_info['status'],
                str(pid),
                "双击操作"
            ), tags=(str(pid), proc_info['status']))
            window_info = self.get_game_windows(pid)
            if window_info and 'size' in window_info:
                width, height = window_info['size']
                if width > 500 or self.hidden_windows.get(pid) is None:
                    self.hidden_windows[pid] = window_info

        self.tree.bind("<Double-1>", self.on_item_double_click)
        self.create_context_menu()

    def create_context_menu(self):
        """创建右键上下文菜单"""
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="隐藏进程", command=self.hide_selected_app)
        self.context_menu.add_command(label="显示进程", command=self.show_selected_app)
        self.context_menu.add_command(label="查看窗口信息", command=self.show_selected_window_info)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="停止进程", command=self.stop_selected_app)
        self.context_menu.add_command(label="刷新状态", command=self.refresh_status)
        self.tree.bind("<Button-3>", self.on_right_click)

    def on_item_double_click(self, event):
        """处理双击事件"""
        item = self.tree.selection()[0] if self.tree.selection() else None
        if item:
            values = self.tree.item(item, 'values')
            if values and len(values) >= 4:
                pid = int(values[3])
                is_visible = self.check_window_visibility(pid)
                if is_visible:
                    self.hide_application(pid)
                else:
                    self.show_application(pid)

    def on_right_click(self, event):
        """处理右键点击事件"""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            values = self.tree.item(item, 'values')
            if values and len(values) >= 4:
                pid = int(values[3])
                self.selected_pid = pid
                self.update_context_menu(None)
                self.context_menu.post(event.x_root, event.y_root)

    def update_context_menu(self, status):
        """根据窗口可见性更新右键菜单"""
        if hasattr(self, 'selected_pid') and self.selected_pid:
            is_visible = self.check_window_visibility(self.selected_pid)
            if is_visible:
                self.context_menu.entryconfig("隐藏进程", state="normal")
                self.context_menu.entryconfig("显示进程", state="disabled")
            else:
                self.context_menu.entryconfig("隐藏进程", state="disabled")
                self.context_menu.entryconfig("显示进程", state="normal")
            self.context_menu.entryconfig("停止进程", state="normal")

    # ---- 窗口管理 ----

    def get_process_windows(self, pid):
        """获取指定进程的所有窗口信息（带缓存）"""
        current_time = time.time()
        if (pid in self.window_cache and
                current_time - self.last_cache_time < self.cache_ttl):
            return self.window_cache[pid]

        window_info_list = []

        @ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
        def enum_windows_proc(hwnd, lParam):
            lpdw_process_id = ctypes.wintypes.DWORD()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(lpdw_process_id))
            if lpdw_process_id.value == pid:
                title_length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                title_buffer = ctypes.create_unicode_buffer(title_length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, title_buffer, title_length + 1)
                rect = ctypes.wintypes.RECT()
                ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
                window_info_list.append({
                    'handle': hwnd,
                    'title': title_buffer.value,
                    'position': (rect.left, rect.top),
                    'size': (rect.right - rect.left, rect.bottom - rect.top),
                    'process_id': pid
                })
            return True

        ctypes.windll.user32.EnumWindows(enum_windows_proc, 0)
        self.window_cache[pid] = window_info_list
        self.last_cache_time = current_time
        return window_info_list

    def get_game_windows(self, pid):
        """获取指定进程的游戏窗口信息"""
        current_time = time.time()
        if (pid in self.window_cache and
                current_time - self.last_cache_time < self.cache_ttl):
            window_info_list = self.window_cache[pid]
        else:
            window_info_list = self.get_process_windows(pid)

        window_info = {}
        for w in window_info_list:
            if "LaTale Client" in w['title']:
                window_info = w
        return window_info

    def check_window_visibility(self, pid):
        """检查指定进程的窗口是否可见"""
        try:
            window_info_list = self.get_process_windows(pid)
            for window_info in window_info_list:
                hwnd = window_info['handle']
                is_visible = ctypes.windll.user32.IsWindowVisible(hwnd)
                if is_visible:
                    return True
            return False
        except Exception as e:
            print(f"检查窗口可见性时出错: {e}")
            return False

    def stop_selected_app(self):
        """停止选中的应用实例"""
        if hasattr(self, 'selected_pid') and self.selected_pid:
            self.stop_application(self.selected_pid)

    def hide_selected_app(self):
        """隐藏选中的应用实例"""
        if hasattr(self, 'selected_pid') and self.selected_pid:
            self.hide_application(self.selected_pid)

    def show_selected_app(self):
        """显示选中的应用实例"""
        if hasattr(self, 'selected_pid') and self.selected_pid:
            self.show_application(self.selected_pid)

    def start_application(self, app_name):
        """启动应用"""
        try:
            app_info = self.applications[app_name]
            subprocess.Popen([app_info['path']],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
            self.status_label.config(text=f"已启动: {app_name}")
            self.refresh_treeview()
        except Exception as e:
            messagebox.showerror("错误", f"启动应用失败: {e}")

    def stop_application(self, pid):
        """停止指定进程ID的应用"""
        try:
            if psutil.pid_exists(pid):
                process = psutil.Process(pid)
                process.terminate()
                self.status_label.config(text=f"已停止进程: {pid}")
                self.refresh_treeview()
                messagebox.showinfo("成功", f"已成功停止进程: {pid}")
            else:
                messagebox.showwarning("警告", f"进程 {pid} 不存在")
        except Exception as e:
            messagebox.showerror("错误", f"停止进程失败: {e}")

    def hide_application(self, pid):
        """隐藏指定进程ID的应用窗口"""
        try:
            if self.hide_process_windows(pid):
                self.status_label.config(text=f"已隐藏进程: {pid}")
            else:
                messagebox.showerror("错误", f"隐藏进程失败: {pid}")
        except Exception as e:
            messagebox.showerror("错误", f"隐藏进程失败: {e}")

    def show_application(self, pid):
        """显示指定进程ID的应用窗口"""
        try:
            if self.show_process_windows(pid):
                self.status_label.config(text=f"已显示进程: {pid}")
            else:
                messagebox.showerror("错误", f"显示进程失败: {pid}")
        except Exception as e:
            messagebox.showerror("错误", f"显示进程失败: {e}")

    def enhanced_hide_window(self, hwnd):
        """增强的窗口隐藏方法"""
        try:
            GWL_EXSTYLE = -20
            WS_EX_TOOLWINDOW = 0x00000080
            WS_EX_NOACTIVATE = 0x08000000

            ctypes.windll.user32.ShowWindow(hwnd, SW_HIDE)
            current_exstyle = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            new_exstyle = current_exstyle | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_exstyle)
            ctypes.windll.user32.EnableWindow(hwnd, False)
            HWND_BOTTOM = 1
            SWP_NOACTIVATE = 0x0010
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            ctypes.windll.user32.SetWindowPos(hwnd, HWND_BOTTOM, 0, 0, 0, 0,
                                              SWP_NOACTIVATE | SWP_NOMOVE | SWP_NOSIZE)
            is_visible = ctypes.windll.user32.IsWindowVisible(hwnd)
            return not is_visible
        except Exception as e:
            print(f"增强隐藏窗口失败: {e}")
            try:
                ctypes.windll.user32.ShowWindow(hwnd, SW_HIDE)
                return True
            except:
                return False

    def enhanced_show_window(self, hwnd):
        """增强的窗口显示方法"""
        try:
            GWL_EXSTYLE = -20
            WS_EX_TOOLWINDOW = 0x00000080
            WS_EX_NOACTIVATE = 0x08000000
            current_exstyle = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            new_exstyle = current_exstyle & ~(WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE)
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_exstyle)
            ctypes.windll.user32.EnableWindow(hwnd, True)
            return True
        except Exception as e:
            print(f"增强显示窗口失败: {e}")
            try:
                ctypes.windll.user32.ShowWindow(hwnd, SW_SHOW)
                return True
            except:
                return False

    def mute_process_audio(self, pid):
        """静音指定进程的音频"""
        try:
            from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
            sessions = AudioUtilities.GetAllSessions()
            for session in sessions:
                if session.Process and session.Process.pid == pid:
                    volume = session._ctl.QueryInterface(ISimpleAudioVolume)
                    volume.SetMute(1, None)
                    return True
            return False
        except Exception as e:
            print(f"静音音频失败: {e}")
            return False

    def unmute_process_audio(self, pid):
        """取消静音指定进程的音频"""
        try:
            from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
            sessions = AudioUtilities.GetAllSessions()
            for session in sessions:
                if session.Process and session.Process.pid == pid:
                    volume = session._ctl.QueryInterface(ISimpleAudioVolume)
                    volume.SetMute(0, None)
                    return True
            return False
        except Exception as e:
            print(f"取消静音失败: {e}")
            return False

    def hide_process_windows(self, pid):
        """隐藏指定进程的所有窗口"""
        def hide_in_thread():
            try:
                window_info_list = self.get_process_windows(pid)
                hidden_count = 0
                for window_info in window_info_list:
                    hwnd = window_info['handle']
                    title = window_info['title']
                    if (ctypes.windll.user32.IsWindowVisible(hwnd) and
                            "LaTale Client" in title):
                        self.mute_process_audio(pid)
                        self.enhanced_hide_window(hwnd)
                        ctypes.windll.user32.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                        win32gui.SetWindowPos(hwnd, 0, -1000, -1000, 10, 10, win32con.SWP_SHOWWINDOW)
                        ctypes.windll.user32.ShowWindow(hwnd, SW_HIDE)
                        hidden_count += 1
                self.after(0, lambda: self._on_hide_complete(pid, hidden_count))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("错误", f"隐藏窗口失败: {e}"))

        threading.Thread(target=hide_in_thread, daemon=True).start()
        return True

    def _on_hide_complete(self, pid, hidden_count):
        """隐藏操作完成后的回调"""
        if hidden_count > 0:
            self.status_label.config(text=f"已隐藏进程: {pid} ({hidden_count}个窗口)")
        else:
            messagebox.showinfo("提示", f"进程 {pid} 没有可见窗口")

    def show_process_windows(self, pid):
        """显示指定进程的所有窗口"""
        def show_in_thread():
            try:
                window_info_list = self.get_process_windows(pid)
                shown_count = 0
                for window_info in window_info_list:
                    hwnd = window_info['handle']
                    title = window_info['title']
                    if "LaTale Client" in title:
                        self.unmute_process_audio(pid)
                        self.enhanced_show_window(hwnd)
                        ctypes.windll.user32.ShowWindow(hwnd, win32con.SW_SHOWNORMAL)
                        window_placement = self.hidden_windows.get(pid)
                        if window_placement:
                            x, y = window_placement['position']
                            width, height = window_placement['size']
                        else:
                            x, y, width, height = 129, 57, 1936, 1119
                        if width < 500 or height < 100:
                            width, height = 1936, 1119
                            x, y = 129, 57
                        win32gui.SetWindowPos(hwnd, win32con.HWND_BOTTOM, x, y, width, height, win32con.SWP_SHOWWINDOW)
                        ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)
                        ctypes.windll.user32.SetForegroundWindow(hwnd)
                        shown_count += 1
                self.after(0, lambda: self._on_show_complete(pid, shown_count))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("错误", f"显示窗口失败: {e}"))

        threading.Thread(target=show_in_thread, daemon=True).start()
        return True

    def _on_show_complete(self, pid, shown_count):
        """显示操作完成后的回调"""
        if shown_count > 0:
            self.status_label.config(text=f"已显示进程: {pid} ({shown_count}个窗口)")
        else:
            messagebox.showinfo("提示", f"进程 {pid} 没有可显示的窗口")

    def delete_application(self, app_name):
        """删除应用"""
        if messagebox.askyesno("确认", f"确定要删除应用 '{app_name}' 吗？"):
            if app_name in self.applications:
                del self.applications[app_name]
                self.save_applications()
                self.refresh_treeview()
                self.status_label.config(text=f"已删除: {app_name}")

    def monitor_processes(self):
        """后台监控进程状态"""
        pass

    def get_window_details(self, pid):
        """获取指定进程ID的所有窗口详细信息"""
        try:
            class WINDOWPLACEMENT(ctypes.Structure):
                _fields_ = [
                    ("length", ctypes.c_uint),
                    ("flags", ctypes.c_uint),
                    ("showCmd", ctypes.c_uint),
                    ("ptMinPosition", ctypes.wintypes.POINT),
                    ("ptMaxPosition", ctypes.wintypes.POINT),
                    ("rcNormalPosition", ctypes.wintypes.RECT)
                ]

            window_info_list = self.get_process_windows(pid)
            window_details = []

            for window_info in window_info_list:
                hwnd = window_info['handle']
                title_length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                title_buffer = ctypes.create_unicode_buffer(title_length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, title_buffer, title_length + 1)
                rect = ctypes.wintypes.RECT()
                ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
                is_visible = ctypes.windll.user32.IsWindowVisible(hwnd)
                placement = WINDOWPLACEMENT()
                placement.length = ctypes.sizeof(WINDOWPLACEMENT)
                ctypes.windll.user32.GetWindowPlacement(hwnd, ctypes.byref(placement))
                window_details.append({
                    'handle': hwnd,
                    'title': title_buffer.value,
                    'visible': bool(is_visible),
                    'position': (rect.left, rect.top),
                    'size': (rect.right - rect.left, rect.bottom - rect.top),
                    'minimized': placement.showCmd == 2,
                    'maximized': placement.showCmd == 3,
                    'process_id': pid
                })
            return window_details
        except Exception as e:
            print(f"获取窗口详细信息时出错: {e}")
            return []

    def show_window_info(self, pid):
        """显示指定进程的窗口信息"""
        details = self.get_window_details(pid)
        if details:
            info_text = f"进程 {pid} 的窗口信息:\n"
            for i, window in enumerate(details, 1):
                info_text += f"\n窗口 {i}:\n"
                info_text += f"  句柄: {window['handle']}\n"
                info_text += f"  标题: {window['title']}\n"
                info_text += f"  可见: {'是' if window['visible'] else '否'}\n"
                info_text += f"  位置: {window['position']}\n"
                info_text += f"  大小: {window['size']}\n"
                info_text += f"  最小化: {'是' if window['minimized'] else '否'}\n"
                info_text += f"  最大化: {'是' if window['maximized'] else '否'}\n"

            info_window = tk.Toplevel(self)
            info_window.title(f"进程 {pid} 窗口信息")
            info_window.geometry("600x400")

            text_widget = tk.Text(info_window, wrap=tk.WORD)
            text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            text_widget.insert(tk.END, info_text)
            text_widget.config(state=tk.DISABLED)

            copy_btn = ttk.Button(info_window, text="复制信息",
                                  command=lambda: self.clipboard_clear() or
                                                  self.clipboard_append(info_text))
            copy_btn.pack(pady=5)
        else:
            messagebox.showinfo("信息", f"进程 {pid} 没有找到任何窗口")

    def show_selected_window_info(self):
        """显示选中进程的窗口信息"""
        if hasattr(self, 'selected_pid') and self.selected_pid:
            self.show_window_info(self.selected_pid)


def main():
    app = RainbowIslandManager()
    app.mainloop()


if __name__ == "__main__":
    main()
