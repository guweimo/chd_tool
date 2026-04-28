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

# Windows API常量定义
SW_HIDE = 0
SW_SHOW = 5
SW_RESTORE = 9

class RainbowIslandManager:
    def __init__(self, root):
        self.root = root
        self.root.title("彩虹岛应用管理器")
        self.root.geometry("800x600")
        
        # 应用数据存储 - 改为基于进程ID的管理
        self.applications = {}  # key: app_name, value: app_info
        self.running_processes = {}  # key: pid, value: process_info
        self.data_file = "rainbow_island_apps.json"
        
        # 选中的进程ID
        self.selected_pid = None
        
        # 窗口句柄缓存 - 优化性能
        self.window_cache = {}  # key: pid, value: list of window handles
        self.last_cache_time = 0
        self.cache_ttl = 5  # 缓存有效期5秒
        
        # 加载已有数据
        self.load_applications()
        
        # 创建界面
        self.create_widgets()
        
        # 启动后台监控线程
        self.monitor_thread = threading.Thread(target=self.monitor_processes, daemon=True)
        self.monitor_thread.start()
    
    def create_widgets(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 标题
        title_label = ttk.Label(main_frame, text="彩虹岛应用管理器", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=4, pady=(0, 20))
        
        # 控制按钮区域
        control_frame = ttk.LabelFrame(main_frame, text="控制面板", padding="10")
        control_frame.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 扫描按钮
        scan_btn = ttk.Button(control_frame, text="扫描所有相关程序", command=self.scan_applications)
        scan_btn.grid(row=0, column=0, padx=(0, 10))
        
        # 添加应用按钮
        add_btn = ttk.Button(control_frame, text="添加应用", command=self.add_application)
        add_btn.grid(row=0, column=1, padx=(0, 10))
        
        # 刷新按钮
        refresh_btn = ttk.Button(control_frame, text="刷新状态", command=self.refresh_status)
        refresh_btn.grid(row=0, column=2)
        
        # 应用列表区域
        list_frame = ttk.LabelFrame(main_frame, text="进程实例列表", padding="10")
        list_frame.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # 进程列表表格 - 修改列名以反映进程ID管理
        columns = ("应用名称", "路径", "状态", "进程ID", "操作")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120)
        
        self.tree.column("路径", width=200)
        self.tree.column("进程ID", width=80)
        self.tree.column("操作", width=150)
        
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
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # 绑定右键事件
        self.tree.bind("<Button-3>", self.on_right_click)
        
        # 初始填充数据
        self.refresh_treeview()
    
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
    
    def scan_applications(self):
        """扫描所有相关程序"""
        self.status_label.config(text="正在扫描程序...")
        
        # 在后台线程中执行扫描
        threading.Thread(target=self._scan_applications_thread, daemon=True).start()
    
    def _scan_applications_thread(self):
        """扫描程序的线程函数"""
        try:
            # 查找可能的彩虹岛相关进程
            rainbow_keywords = ['LataleClient_x64']
            found_processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
                try:
                    proc_info = proc.info
                    name_lower = proc_info['name'].lower() if proc_info['name'] else ""
                    cmdline = " ".join(proc_info['cmdline']) if proc_info['cmdline'] else ""
                    
                    # 检查是否包含关键词
                    for keyword in rainbow_keywords:
                        if keyword.lower() in name_lower or keyword.lower() in cmdline.lower():
                            found_processes.append({
                                'pid': proc_info['pid'],
                                'name': proc_info['name'],
                                'path': proc_info['exe'],
                                'cmdline': cmdline
                            })
                            break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # 更新应用列表
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
        """刷新树形视图 - 改为显示所有运行实例"""
        # 清空现有数据
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 获取当前所有运行的进程实例
        self.running_processes = {}
        
        # 查找所有相关进程
        rainbow_keywords = [ 'LataleClient_x64' ]

        for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline', 'create_time']):
            try:
                proc_info = proc.info
                name_lower = proc_info['name'].lower() if proc_info['name'] else ""
                cmdline = " ".join(proc_info['cmdline']) if proc_info['cmdline'] else ""
                
                # 检查是否包含关键词
                for keyword in rainbow_keywords:
                    if keyword.lower() in name_lower or keyword.lower() in cmdline.lower():
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
        
        # 填充数据 - 每个进程实例一行
        for pid, proc_info in self.running_processes.items():
            # 添加到树形视图
            item = self.tree.insert("", "end", values=(
                proc_info['name'],
                proc_info['path'],
                proc_info['status'],
                str(pid),
                "双击操作"
            ), tags=(str(pid), proc_info['status']))
        
        # 绑定双击事件
        self.tree.bind("<Double-1>", self.on_item_double_click)
        
        # 创建右键菜单
        self.create_context_menu()
    
    def create_context_menu(self):
        """创建右键上下文菜单 - 更新为进程ID操作"""
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="隐藏进程", command=self.hide_selected_app)
        self.context_menu.add_command(label="显示进程", command=self.show_selected_app)
        self.context_menu.add_command(label="查看窗口信息", command=self.show_selected_window_info)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="停止进程", command=self.stop_selected_app)
        self.context_menu.add_command(label="刷新状态", command=self.refresh_status)
        
        # 绑定右键点击事件
        self.tree.bind("<Button-3>", self.on_right_click)
    
    def on_item_double_click(self, event):
        """处理双击事件 - 基于窗口可见性切换"""
        item = self.tree.selection()[0] if self.tree.selection() else None
        if item:
            # 从item的values中获取进程ID
            values = self.tree.item(item, 'values')
            if values and len(values) >= 4:
                pid = int(values[3])  # 第4列是进程ID
                
                # 检查窗口当前可见性
                is_visible = self.check_window_visibility(pid)
                
                if is_visible:
                    self.hide_application(pid)
                else:
                    self.show_application(pid)
    
    def on_right_click(self, event):
        """处理右键点击事件 - 基于窗口可见性"""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            # 从item的values中获取进程ID
            values = self.tree.item(item, 'values')
            if values and len(values) >= 4:
                pid = int(values[3])  # 第4列是PID
                
                # 存储当前选中的进程ID
                self.selected_pid = pid
                
                # 根据窗口可见性更新菜单
                self.update_context_menu(None)
                
                # 显示右键菜单
                self.context_menu.post(event.x_root, event.y_root)
    
    def update_context_menu(self, status):
        """根据窗口可见性更新右键菜单"""
        # 获取当前选中进程的窗口状态
        if hasattr(self, 'selected_pid') and self.selected_pid:
            # 检查窗口是否可见
            is_visible = self.check_window_visibility(self.selected_pid)
            
            # 根据窗口可见性启用/禁用菜单项
            if is_visible:
                self.context_menu.entryconfig("隐藏进程", state="normal")
                self.context_menu.entryconfig("显示进程", state="disabled")
            else:
                self.context_menu.entryconfig("隐藏进程", state="disabled")
                self.context_menu.entryconfig("显示进程", state="normal")
            
            # 停止进程菜单项始终可用（如果进程在运行）
            self.context_menu.entryconfig("停止进程", state="normal")
    
    def get_process_windows(self, pid):
        """获取指定进程的所有窗口信息（带缓存）"""
        current_time = time.time()
        
        # 检查缓存是否有效
        if (pid in self.window_cache and 
            current_time - self.last_cache_time < self.cache_ttl):
            return self.window_cache[pid]
        
        # 重新枚举窗口
        window_info_list = []
        
        @ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
        def enum_windows_proc(hwnd, lParam):
            # 获取窗口的进程ID
            lpdw_process_id = ctypes.wintypes.DWORD()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(lpdw_process_id))
            
            if lpdw_process_id.value == pid:
                # 获取窗口标题
                title_length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                title_buffer = ctypes.create_unicode_buffer(title_length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, title_buffer, title_length + 1)
                
                window_info_list.append({
                    'handle': hwnd,
                    'title': title_buffer.value,
                    'process_id': pid
                })
            return True
        
        ctypes.windll.user32.EnumWindows(enum_windows_proc, 0)
        
        # 更新缓存
        self.window_cache[pid] = window_info_list
        self.last_cache_time = current_time
        
        return window_info_list
    
    def check_window_visibility(self, pid):
        """检查指定进程的窗口是否可见（优化版本）"""
        try:
            window_info_list = self.get_process_windows(pid)
            
            for window_info in window_info_list:
                hwnd = window_info['handle']
                # 检查窗口是否可见
                is_visible = ctypes.windll.user32.IsWindowVisible(hwnd)
                if is_visible:
                    return True
            return False
            
        except Exception as e:
            print(f"检查窗口可见性时出错: {e}")
            return False
    
    def start_selected_app(self):
        """启动选中的应用"""
        if hasattr(self, 'selected_app_name') and self.selected_app_name:
            self.start_application(self.selected_app_name)
    
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
    
    def delete_selected_app(self):
        """删除选中的应用"""
        if hasattr(self, 'selected_app_name') and self.selected_app_name:
            self.delete_application(self.selected_app_name)
    
    def start_application(self, app_name):
        """启动应用"""
        try:
            app_info = self.applications[app_name]
            process = subprocess.Popen([app_info['path']], 
                                     stdout=subprocess.PIPE, 
                                     stderr=subprocess.PIPE)
            self.processes[app_name] = process
            self.status_label.config(text=f"已启动: {app_name}")
            self.refresh_treeview()
        except Exception as e:
            messagebox.showerror("错误", f"启动应用失败: {e}")
    
    def stop_application(self, pid):
        """停止指定进程ID的应用"""
        try:
            # 终止指定进程
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
            # 使用Windows API隐藏窗口
            if self.hide_process_windows(pid):
                self.status_label.config(text=f"已隐藏进程: {pid}")
                # self.refresh_treeview()
                # messagebox.showinfo("成功", f"已成功隐藏进程: {pid}")
            else:
                messagebox.showerror("错误", f"隐藏进程失败: {pid}")
        except Exception as e:
            messagebox.showerror("错误", f"隐藏进程失败: {e}")
    
    def show_application(self, pid):
        """显示指定进程ID的应用窗口"""
        try:
            # 使用Windows API显示窗口
            if self.show_process_windows(pid):
                self.status_label.config(text=f"已显示进程: {pid}")
                # self.refresh_treeview()
                # messagebox.showinfo("成功", f"已成功显示进程: {pid}")
            else:
                messagebox.showerror("错误", f"显示进程失败: {pid}")
        except Exception as e:
            messagebox.showerror("错误", f"显示进程失败: {e}")
    
    def hide_process_windows(self, pid):
        """隐藏指定进程的所有窗口（优化版本）"""
        def hide_in_thread():
            try:
                window_info_list = self.get_process_windows(pid)
                hidden_count = 0
                
                for window_info in window_info_list:
                    hwnd = window_info['handle']
                    title = window_info['title']
                    print(f"检查窗口: {hwnd} - 标题: {title}")
                    
                    # 检查窗口是否可见且标题包含"LaTale Client"
                    if (ctypes.windll.user32.IsWindowVisible(hwnd) and 
                        "LaTale Client" in title):
                        # 隐藏窗口
                        ctypes.windll.user32.ShowWindow(hwnd, SW_HIDE)
                        hidden_count += 1
                
                # 在主线程中更新界面
                self.root.after(0, lambda: self._on_hide_complete(pid, hidden_count))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"隐藏窗口失败: {e}"))
        
        # 在后台线程中执行隐藏操作
        threading.Thread(target=hide_in_thread, daemon=True).start()
        return True
    
    def _on_hide_complete(self, pid, hidden_count):
        """隐藏操作完成后的回调"""
        if hidden_count > 0:
            self.status_label.config(text=f"已隐藏进程: {pid} ({hidden_count}个窗口)")
            # self.refresh_treeview()
            # messagebox.showinfo("成功", f"已成功隐藏进程: {pid}")
        else:
            messagebox.showinfo("提示", f"进程 {pid} 没有可见窗口")
    
    def show_process_windows(self, pid):
        """显示指定进程的所有窗口（优化版本）"""
        def show_in_thread():
            try:
                window_info_list = self.get_process_windows(pid)
                shown_count = 0
                
                for window_info in window_info_list:
                    hwnd = window_info['handle']
                    title = window_info['title']
                    
                    # 检查窗口标题是否包含"LaTale Client"
                    if "LaTale Client" in title:
                        # 显示窗口并恢复
                        ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)
                        # 将窗口置于前台
                        ctypes.windll.user32.SetForegroundWindow(hwnd)
                        shown_count += 1
                
                # 在主线程中更新界面
                self.root.after(0, lambda: self._on_show_complete(pid, shown_count))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"显示窗口失败: {e}"))
        
        # 在后台线程中执行显示操作
        threading.Thread(target=show_in_thread, daemon=True).start()
        return True
    
    def _on_show_complete(self, pid, shown_count):
        """显示操作完成后的回调"""
        if shown_count > 0:
            self.status_label.config(text=f"已显示进程: {pid} ({shown_count}个窗口)")
            # self.refresh_treeview()
            # messagebox.showinfo("成功", f"已成功显示进程: {pid}")
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
        # while True:
        #     # time.sleep(5)  # 每5秒检查一次
        #     try:
        #         # 检查进程状态并更新界面
        #         # self.root.after(0, self.refresh_treeview)
        #         pass
        #     except:
        #         pass
    
    def get_window_details(self, pid):
        """获取指定进程ID的所有窗口详细信息"""
        try:
            # 定义 WINDOWPLACEMENT 结构体
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
                
                # 获取窗口标题
                title_length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                title_buffer = ctypes.create_unicode_buffer(title_length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, title_buffer, title_length + 1)
                
                # 获取窗口位置和大小
                rect = ctypes.wintypes.RECT()
                ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
                
                # 检查窗口可见性
                is_visible = ctypes.windll.user32.IsWindowVisible(hwnd)
                
                # 检查窗口是否是最小化/最大化
                placement = WINDOWPLACEMENT()
                placement.length = ctypes.sizeof(WINDOWPLACEMENT)
                ctypes.windll.user32.GetWindowPlacement(hwnd, ctypes.byref(placement))
                
                window_details.append({
                    'handle': hwnd,
                    'title': title_buffer.value,
                    'visible': bool(is_visible),
                    'position': (rect.left, rect.top),
                    'size': (rect.right - rect.left, rect.bottom - rect.top),
                    'minimized': placement.showCmd == 2,  # SW_SHOWMINIMIZED
                    'maximized': placement.showCmd == 3,  # SW_SHOWMAXIMIZED
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
            
            # 创建信息显示窗口
            info_window = tk.Toplevel(self.root)
            info_window.title(f"进程 {pid} 窗口信息")
            info_window.geometry("600x400")
            
            text_widget = tk.Text(info_window, wrap=tk.WORD)
            text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            text_widget.insert(tk.END, info_text)
            text_widget.config(state=tk.DISABLED)
            
            # 添加复制按钮
            copy_btn = ttk.Button(info_window, text="复制信息", 
                                 command=lambda: self.root.clipboard_clear() or 
                                               self.root.clipboard_append(info_text))
            copy_btn.pack(pady=5)
            
        else:
            messagebox.showinfo("信息", f"进程 {pid} 没有找到任何窗口")
    
    def show_selected_window_info(self):
        """显示选中进程的窗口信息"""
        if hasattr(self, 'selected_pid') and self.selected_pid:
            self.show_window_info(self.selected_pid)

def main():
    root = tk.Tk()
    app = RainbowIslandManager(root)
    root.mainloop()

if __name__ == "__main__":
    main()