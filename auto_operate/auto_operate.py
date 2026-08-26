import os
import json
import sys
import time
import ctypes
from ctypes import wintypes
import threading
import subprocess
from datetime import datetime

import psutil
import win32gui
import win32con

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QMenu, QMessageBox, QFileDialog, QDialog, QTextEdit,
    QAbstractItemView, QFrame, QStyle
)
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QIcon, QFont, QColor, QAction
from PySide6.QtWidgets import QSystemTrayIcon

from pynput import keyboard
from pynput.keyboard import Key, Controller as KeyController
from pynput.mouse import Button, Controller as MouseController

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
        self._stop_event = threading.Event()
        self._click_event = threading.Event()
        self._buy_lock = threading.Lock()

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

    def _keyboard_listener(self):
        """键盘监听线程"""
        with keyboard.Listener(on_press=self._on_press, on_release=self._on_release) as listener:
            while not self._stop_event.is_set():
                listener.join(0.5)

    def _on_press(self, key):
        if self._stop_event.is_set():
            return

        try:
            if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
                self.on_ctrl = True
                return

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
                    self.current_pos = self.mouse_controller.position
                    self._tray_notify(f"当前坐标: {self.current_pos}", "坐标信息")

            if self.auto_buy:
                return

            if self.on_alt:
                if key == keyboard.Key.f1:
                    current_pos = self.mouse_controller.position
                    time.sleep(0.05)
                    self.mouse_controller.click(Button.left)
                    time.sleep(0.05)
                    self.mouse_controller.position = (1862, 1268)
                    time.sleep(0.05)
                    self.mouse_controller.click(Button.left)
                    time.sleep(0.05)
                    self.mouse_controller.position = current_pos
                elif key == keyboard.Key.f2:
                    current_pos = self.mouse_controller.position
                    time.sleep(0.05)
                    self.mouse_controller.position = (1031, 1480)
                    time.sleep(0.05)
                    self.mouse_controller.click(Button.left)
                    time.sleep(0.05)
                    self.mouse_controller.position = (1854, 1265)
                    time.sleep(0.05)
                    self.mouse_controller.click(Button.left)
                    time.sleep(0.05)
                    self.mouse_controller.position = current_pos

        except AttributeError:
            pass

    def _on_release(self, key):
        try:
            if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
                self.on_ctrl = False
            elif key in (keyboard.Key.alt_l, keyboard.Key.alt_r):
                self.on_alt = False
        except AttributeError:
            pass

    def _auto_click(self):
        while not self._stop_event.is_set():
            if self._click_event.is_set():
                self.mouse_controller.click(Button.left)
                time.sleep(0.01)
            else:
                time.sleep(0.1)

    def _start_buy_thread(self, positions, name):
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
                    self.mouse_controller.position = (x, y)
                    time.sleep(0.05)
                    self.key_controller.press(Key.shift)
                    time.sleep(0.05)
                    self.mouse_controller.click(Button.right)
                    time.sleep(0.05)
                    self.key_controller.release(Key.shift)
                    time.sleep(0.05)
                    self.key_controller.type('9999')
                    time.sleep(0.05)
                    self.mouse_controller.position = (1906, 717)
                    self.mouse_controller.click(Button.left)
                time.sleep(0.05)
            self.auto_buy = False
        except Exception as e:
            self.auto_buy = False
            self._tray_notify(f"操作失败: {str(e)}", "错误")

    def _emergency_stop(self):
        self._stop_event.set()
        self._click_event.clear()
        with self._buy_lock:
            for t in self.active_buy_threads:
                if t.is_alive():
                    t.join(0.5)
        self._tray_notify("已强制终止所有操作", "系统")
        self._click_event.clear()

    def _tray_notify(self, message, title="提示"):
        # 托盘气泡通知已禁用
        pass


class RainbowIslandManager(QMainWindow, AutoClickerMixin):
    """彩虹岛应用管理器 + 自动点击器（PySide6 版）"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("彩虹岛管理器")

        # 设置窗口图标和应用图标
        icon_path = self._get_data_path("icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            QApplication.instance().setWindowIcon(QIcon(icon_path))

        self._dpi_scale = get_dpi_scale()
        # PySide6 已自动处理 DPI 缩放，窗口尺寸不再额外乘 scale
        base_w, base_h = 800, 600
        self.resize(base_w, base_h)
        self.setMinimumSize(base_w, base_h)

        # 应用数据存储
        self.applications = {}
        self.running_processes = {}
        self.data_file = self._get_data_path("rainbow_island_apps.json")

        self.selected_pid = None
        self.window_cache = {}
        self.last_cache_time = 0
        self.cache_ttl = 5
        self.hidden_windows = {}
        self.tray_icon = None

        self.load_applications()
        self.create_widgets()
        self.init_auto_clicker()

        # 窗口关闭时最小化到托盘
        self.closeEvent = self._on_window_close

        self.monitor_thread = threading.Thread(target=self.monitor_processes, daemon=True)
        self.monitor_thread.start()

        self._init_tray()

    def _get_data_path(self, filename):
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, filename)

    # ---- 托盘图标 ----

    def _init_tray(self):
        # 优先尝试 icon.png，找不到时回退到 icon.ico
        icon_path = self._get_data_path("icon.png")
        icon = QIcon(icon_path)
        if icon.isNull():
            ico_path = self._get_data_path("icon.ico")
            if os.path.exists(ico_path):
                icon = QIcon(ico_path)
        if icon.isNull():
            print("[WARN] 托盘图标加载失败，使用默认图标")
            icon = QIcon()

        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip("彩虹岛管理器")

        menu = QMenu()
        menu.addAction("显示主窗口", self._show_window)
        menu.addAction("强制停止所有操作", self._emergency_stop)
        menu.addSeparator()
        menu.addAction("退出程序", self.on_exit)

        info_action = QAction("当前位置", self)
        info_action.setEnabled(False)
        menu.addAction(info_action)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self._show_window()

    def _show_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _on_window_close(self, event):
        """窗口关闭时最小化到托盘（不显示气泡提示）"""
        event.ignore()
        self.hide()

    # ---- 退出 ----

    def on_exit(self):
        self._stop_event.set()
        self._click_event.clear()
        try:
            self.listener_thread.join(1)
        except Exception:
            pass
        if self.tray_icon:
            self.tray_icon.hide()
        QApplication.instance().quit()

    # ---- GUI 界面 ----

    def create_widgets(self):
        # Qt 已自动按 DPI 缩放，尺寸和字号不额外乘 scale
        pad = 10

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(pad, pad, pad, pad)
        layout.setSpacing(10)

        # 标题
        title = QLabel("彩虹岛管理器")
        title_font = QFont("Microsoft YaHei UI", 16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # 控制面板
        control_group = QGroupBox("控制面板")
        control_group.setFont(QFont("Microsoft YaHei UI", 9))
        control_layout = QHBoxLayout(control_group)
        control_layout.setContentsMargins(pad, pad, pad, pad)
        control_layout.setSpacing(10)

        scan_btn = QPushButton("扫描所有相关程序")
        add_btn = QPushButton("添加应用")
        refresh_btn = QPushButton("刷新状态")
        help_btn = QPushButton("操作说明")
        for btn in (scan_btn, add_btn, refresh_btn, help_btn):
            btn.setFont(QFont("Microsoft YaHei UI", 10))
            control_layout.addWidget(btn)
        scan_btn.clicked.connect(self.scan_applications)
        add_btn.clicked.connect(self.add_application)
        refresh_btn.clicked.connect(self.refresh_status)
        help_btn.clicked.connect(self.show_operation_help)

        layout.addWidget(control_group)

        # 进程实例列表
        list_group = QGroupBox("进程实例列表")
        list_group.setFont(QFont("Microsoft YaHei UI", 9))
        list_layout = QVBoxLayout(list_group)
        list_layout.setContentsMargins(pad, pad, pad, pad)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["应用名称", "路径", "状态", "进程ID", "操作"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.setFont(QFont("Microsoft YaHei UI", 9))
        self.table.verticalHeader().setDefaultSectionSize(24)

        # 右键菜单
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_table_menu)
        self.table.itemDoubleClicked.connect(self.on_item_double_click)

        list_layout.addWidget(self.table)
        layout.addWidget(list_group, stretch=1)

        # 状态栏
        self.status_label = QLabel("就绪")
        self.status_label.setFont(QFont("Microsoft YaHei UI", 9))
        layout.addWidget(self.status_label)

        self.refresh_treeview()

    def _show_table_menu(self, pos):
        index = self.table.indexAt(pos)
        if not index.isValid():
            return
        row = index.row()
        pid_item = self.table.item(row, 3)
        if not pid_item:
            return
        self.selected_pid = int(pid_item.text())
        self.table.selectRow(row)

        menu = QMenu(self)
        is_visible = self.check_window_visibility(self.selected_pid)
        hide_action = menu.addAction("隐藏进程", lambda: self.hide_application(self.selected_pid))
        show_action = menu.addAction("显示进程", lambda: self.show_application(self.selected_pid))
        hide_action.setEnabled(is_visible)
        show_action.setEnabled(not is_visible)
        menu.addSeparator()
        menu.addAction("查看窗口信息", lambda: self.show_window_info(self.selected_pid))
        menu.addSeparator()
        menu.addAction("停止进程", lambda: self.stop_application(self.selected_pid))
        menu.addAction("刷新状态", self.refresh_status)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def on_item_double_click(self, item):
        row = item.row()
        pid_item = self.table.item(row, 3)
        if not pid_item:
            return
        pid = int(pid_item.text())
        is_visible = self.check_window_visibility(pid)
        if is_visible:
            self.hide_application(pid)
        else:
            self.show_application(pid)

    # ---- 数据加载/保存 ----

    def load_applications(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.applications = json.load(f)
            except Exception:
                self.applications = {}

    def save_applications(self):
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.applications, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存数据失败: {e}")

    # ---- 扫描/添加应用 ----

    def scan_applications(self):
        self.status_label.setText("正在扫描程序...")
        threading.Thread(target=self._scan_applications_thread, daemon=True).start()

    def _scan_applications_thread(self):
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
            self.status_label.setText(f"扫描完成，发现 {len(found_processes)} 个相关进程")
        except Exception as e:
            self.status_label.setText(f"扫描失败: {e}")

    def add_application(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择应用程序", "", "可执行文件 (*.exe);;所有文件 (*.*)"
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
                self.status_label.setText(f"已添加应用: {app_name}")
            else:
                QMessageBox.information(self, "提示", "该应用已存在")

    def refresh_status(self):
        self.refresh_treeview()
        self.status_label.setText("状态已刷新")

    def show_operation_help(self):
        """弹出操作说明对话框"""
        help_text = (
            "【全局快捷键】\n"
            "  Ctrl+F1   启动自动点击\n"
            "  Ctrl+F2   停止自动点击\n"
            "  Ctrl+F4   退出程序\n"
            "  Ctrl+F5   购买攻击免疫\n"
            "  Ctrl+F6   购买小吸红\n"
            "  Ctrl+F7   购买属性免疫\n"
            "  Ctrl+F9   获取当前鼠标坐标\n\n"
            "【Alt 组合键】\n"
            "  Alt+F1    一键购买操作1\n"
            "  Alt+F2    一键购买操作2\n\n"
            "【列表操作】\n"
            "  双击行      隐藏/显示对应进程窗口\n"
            "  右键点击    打开进程操作菜单（隐藏/显示/停止/窗口信息）\n\n"
            "【窗口行为】\n"
            "  关闭主窗口后程序最小化到系统托盘\n"
            "  托盘右键菜单可显示主窗口、强制停止操作或退出程序\n"
        )

        dialog = QDialog(self)
        dialog.setWindowTitle("操作说明")
        dialog.resize(480, 420)
        dlayout = QVBoxLayout(dialog)
        text = QTextEdit(dialog)
        text.setPlainText(help_text)
        text.setReadOnly(True)
        text.setFont(QFont("Microsoft YaHei UI", 10))
        dlayout.addWidget(text)
        close_btn = QPushButton("关闭", dialog)
        close_btn.clicked.connect(dialog.accept)
        dlayout.addWidget(close_btn, alignment=Qt.AlignCenter)
        dialog.exec()

    def refresh_treeview(self):
        self.table.setRowCount(0)
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
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = [
                proc_info['name'],
                proc_info['path'],
                proc_info['status'],
                str(pid),
                "双击操作"
            ]
            for col, val in enumerate(values):
                item = QTableWidgetItem(val)
                # 去除编辑和选中标志，避免单元格显示 I-beam 文本光标
                item.setFlags(item.flags() & ~Qt.ItemIsEditable & ~Qt.ItemIsSelectable)
                self.table.setItem(row, col, item)
            window_info = self.get_game_windows(pid)
            if window_info and 'size' in window_info:
                width, height = window_info['size']
                if width > 500 or self.hidden_windows.get(pid) is None:
                    self.hidden_windows[pid] = window_info

    # ---- 窗口管理 ----

    def get_process_windows(self, pid):
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

    def stop_application(self, pid):
        try:
            if psutil.pid_exists(pid):
                process = psutil.Process(pid)
                process.terminate()
                self.status_label.setText(f"已停止进程: {pid}")
                self.refresh_treeview()
                QMessageBox.information(self, "成功", f"已成功停止进程: {pid}")
            else:
                QMessageBox.warning(self, "警告", f"进程 {pid} 不存在")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"停止进程失败: {e}")

    def hide_application(self, pid):
        if self.hide_process_windows(pid):
            self.status_label.setText(f"已隐藏进程: {pid}")
        else:
            QMessageBox.critical(self, "错误", f"隐藏进程失败: {pid}")

    def show_application(self, pid):
        if self.show_process_windows(pid):
            self.status_label.setText(f"已显示进程: {pid}")
        else:
            QMessageBox.critical(self, "错误", f"显示进程失败: {pid}")

    def enhanced_hide_window(self, hwnd):
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
            except Exception:
                return False

    def enhanced_show_window(self, hwnd):
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
            except Exception:
                return False

    def mute_process_audio(self, pid):
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
        def hide_in_thread():
            try:
                window_info_list = self.get_process_windows(pid)
                hidden_count = 0
                for window_info in window_info_list:
                    hwnd = window_info['handle']
                    title = window_info['title']
                    if (ctypes.windll.user32.IsWindowVisible(hwnd) and
                            "LaTale Client" in title):
                        # 隐藏前记录窗口原始位置和尺寸，恢复时保持原样
                        rect = ctypes.wintypes.RECT()
                        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
                        self.hidden_windows[pid] = {
                            'handle': hwnd,
                            'title': title,
                            'position': (rect.left, rect.top),
                            'size': (rect.right - rect.left, rect.bottom - rect.top),
                            'process_id': pid
                        }
                        self.mute_process_audio(pid)
                        self.enhanced_hide_window(hwnd)
                        ctypes.windll.user32.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                        win32gui.SetWindowPos(hwnd, 0, -1000, -1000, 10, 10, win32con.SWP_SHOWWINDOW)
                        ctypes.windll.user32.ShowWindow(hwnd, SW_HIDE)
                        hidden_count += 1
                QTimer.singleShot(0, lambda: self._on_hide_complete(pid, hidden_count))
            except Exception as e:
                QTimer.singleShot(0, lambda: QMessageBox.critical(self, "错误", f"隐藏窗口失败: {e}"))

        threading.Thread(target=hide_in_thread, daemon=True).start()
        return True

    def _on_hide_complete(self, pid, hidden_count):
        if hidden_count > 0:
            self.status_label.setText(f"已隐藏进程: {pid} ({hidden_count}个窗口)")
        else:
            QMessageBox.information(self, "提示", f"进程 {pid} 没有可见窗口")

    def show_process_windows(self, pid):
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
                            x, y, width, height = 235, 109, 3371, 1941
                        if width < 500 or height < 100:
                            width, height = 3371, 1941
                            x, y = 235, 109
                        win32gui.SetWindowPos(hwnd, win32con.HWND_BOTTOM, x, y, width, height, win32con.SWP_SHOWWINDOW)
                        ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)
                        ctypes.windll.user32.SetForegroundWindow(hwnd)
                        shown_count += 1
                QTimer.singleShot(0, lambda: self._on_show_complete(pid, shown_count))
            except Exception as e:
                QTimer.singleShot(0, lambda: QMessageBox.critical(self, "错误", f"显示窗口失败: {e}"))

        threading.Thread(target=show_in_thread, daemon=True).start()
        return True

    def _on_show_complete(self, pid, shown_count):
        if shown_count > 0:
            self.status_label.setText(f"已显示进程: {pid} ({shown_count}个窗口)")
        else:
            QMessageBox.information(self, "提示", f"进程 {pid} 没有可显示的窗口")

    def monitor_processes(self):
        pass

    def get_window_details(self, pid):
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

            dialog = QDialog(self)
            dialog.setWindowTitle(f"进程 {pid} 窗口信息")
            dialog.resize(600, 400)
            dlayout = QVBoxLayout(dialog)
            text = QTextEdit(dialog)
            text.setPlainText(info_text)
            text.setReadOnly(True)
            dlayout.addWidget(text)
            copy_btn = QPushButton("复制信息", dialog)
            copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(info_text))
            dlayout.addWidget(copy_btn, alignment=Qt.AlignCenter)
            dialog.exec()
        else:
            QMessageBox.information(self, "信息", f"进程 {pid} 没有找到任何窗口")


def main():
    # PySide6 6.x 已默认启用高 DPI 缩放，无需手动设置 AA_EnableHighDpiScaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    window = RainbowIslandManager()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
