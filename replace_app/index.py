import sys
import json
import os
import shutil
import ctypes
import subprocess
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, 
                            QPushButton, QListWidget, QFileDialog, QLabel, 
                            QInputDialog, QListWidgetItem, QHBoxLayout, 
                            QMessageBox, QGroupBox, QComboBox, QCheckBox,
                            QLineEdit, QFormLayout, QDialog, QDialogButtonBox,
                            QGridLayout, QStyledItemDelegate, QScrollArea,
                            QFrame, QListView, QStyle, QStylePainter, QStyleOptionComboBox)
from PyQt5.QtCore import Qt, QSize, QEvent
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon, QStandardItemModel, QStandardItem, QCursor
from pathlib import Path

CONFIG_FILE = "accounts_config.json"

def resource_path(relative_path):
    """动态获取资源路径（同时支持开发环境和打包后环境）"""
    if hasattr(sys, '_MEIPASS'):
        # 打包后的临时目录路径
        base_path = Path(sys._MEIPASS)
    else:
        # 开发时的项目根目录
        base_path = Path(__file__).parent
    
    target_path = base_path / relative_path
    
    # 调试输出（打包后检查控制台输出）
    # print(f"[DEBUG] 资源路径: {target_path} | 文件存在: {target_path.exists()}")
    
    if not target_path.exists():
        raise FileNotFoundError(f"资源文件不存在: {target_path}")
    
    return str(target_path)


class CheckableComboBox(QComboBox):
    def __init__(self, parent=None):
        super(CheckableComboBox, self).__init__(parent)
        self.setView(QListView(self))
        self.view().viewport().installEventFilter(self)
        self.setModel(QStandardItemModel(self))
        
        # 配置基本属性
        down = Path(resource_path('down.png')).as_posix()
        style = f"""
            QComboBox {{
                combobox-popup: 0;
                font-family: PingFang SC;
                font-size: 14px;
                padding: 5px 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                min-height: 28px;
                font-weight: bold;
            }}
            QComboBox:hover {{
                border: 1px solid #aaa;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left-width: 1px;
                border-left-color: #ddd;
                border-left-style: solid;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
            }}
            QComboBox::down-arrow {{
                image: url({down});
                width: 14px;
                height: 14px;
            }}
            QComboBox QAbstractItemView {{
                font-family: PingFang SC;
                font-size: 13px;
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background: white;
                selection-background-color: #5c9eff;
                selection-color: white;
                outline: 0;
                margin: 0;
            }}
            QComboBox QAbstractItemView::item {{
                height: 30px;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: #5c9eff; 
                color: white;
            }}
        """
        self.setStyleSheet(style)
        self._popup_open = False
        self._display_text = "请选择..."
        
        # 连接信号
        self.model().itemChanged.connect(self._update_display_text)
        
    def eventFilter(self, obj, event):
        # 处理下拉列表中选项的鼠标释放事件
        if event.type() == QEvent.MouseButtonRelease and obj == self.view().viewport():
            index = self.view().indexAt(event.pos())
            if index.isValid():
                item = self.model().item(index.row())
                if item is not None and item.isCheckable():
                    # 切换复选框状态
                    new_state = Qt.Checked if item.checkState() == Qt.Unchecked else Qt.Unchecked
                    item.setCheckState(new_state)
                    return True
        
        # 处理点击组合框本身的事件
        if event.type() == QEvent.MouseButtonPress:
            if self._popup_open:
                self.hidePopup()
            else:
                self.showPopup()
            return True
            
        return super().eventFilter(obj, event)
    
    def showPopup(self):
        super().showPopup()
        self._popup_open = True
        
    def hidePopup(self):
        view = self.view()
        local_pos = view.mapFromGlobal(QCursor.pos())
        
        # 只有当鼠标不在下拉列表内时才隐藏
        if not view.rect().contains(local_pos) or not view.isVisible():
            super().hidePopup()
            self._popup_open = False
            self._update_display_text()
    
    def paintEvent(self, event):
        painter = QStylePainter(self)
        painter.setPen(self.palette().color(QPalette.Text))
        
        opt = QStyleOptionComboBox()
        self.initStyleOption(opt)
        
        # 使用我们存储的显示文本
        opt.text = self._display_text
        opt.currentText = self._display_text  # 确保当前文本也更新

        painter.drawComplexControl(QStyle.CC_ComboBox, opt)
        painter.drawControl(QStyle.CE_ComboBoxLabel, opt)
    
    def _update_display_text(self):
        """更新显示文本"""
        selected = self.checkedItems()
        self._display_text = ", ".join(selected) if selected else "请选择..."
        self.update()  # 触发重绘
    
    def addItem(self, text, data=None):
        item = QStandardItem(text)
        item.setCheckable(True)
        item.setCheckState(Qt.Unchecked)
        if data is None:
            data = text
        item.setData(data)
        self.model().appendRow(item)
        
    def addItems(self, texts, datalist=None):
        for i, text in enumerate(texts):
            try:
                data = datalist[i]
            except (TypeError, IndexError):
                data = None
            self.addItem(text, data)
            
    def checkedItems(self):
        """获取所有选中的项目文本"""
        return [self.model().item(i).text() 
                for i in range(self.model().rowCount())
                if self.model().item(i).checkState() == Qt.Checked]
    
    def checkedData(self):
        """获取所有选中的项目数据"""
        return [self.model().item(i).data()
                for i in range(self.model().rowCount())
                if self.model().item(i).checkState() == Qt.Checked]



class StyledComboBoxDelegate(QStyledItemDelegate):
    """Custom delegate for styling combo box items"""
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def paint(self, painter, option, index):
        option.font.setFamily("PingFang SC")
        option.font.setPointSize(10)
        super().paint(painter, option, index)

class AccountDialog(QDialog):
    """账号管理对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("账号管理")
        self.setModal(True)
        self.resize(400, 300)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 账号列表
        self.account_list = QListWidget()
        self.account_list.setAlternatingRowColors(True)
        layout.addWidget(self.account_list)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        self.add_button = QPushButton("添加账号")
        self.add_button.clicked.connect(self.add_account)
        button_layout.addWidget(self.add_button)
        
        self.remove_button = QPushButton("移除账号")
        self.remove_button.clicked.connect(self.remove_account)
        button_layout.addWidget(self.remove_button)
        
        layout.addLayout(button_layout)
        
        # 对话框按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def add_account(self):
        """添加新账号"""
        name, ok = QInputDialog.getText(self, "添加账号", "输入账号名称:")
        if ok and name:
            if not self.account_exists(name):
                self.account_list.addItem(name)
            else:
                QMessageBox.warning(self, "警告", "该账号已存在!")
    
    def remove_account(self):
        """移除选中账号"""
        selected = self.account_list.currentItem()
        if selected:
            reply = QMessageBox.question(
                self, "确认", 
                f"确定要移除账号 '{selected.text()}' 吗?", 
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                self.account_list.takeItem(self.account_list.row(selected))
    
    def account_exists(self, name):
        """检查账号是否已存在"""
        return any(name == self.account_list.item(i).text() 
                  for i in range(self.account_list.count()))
    
    def get_accounts(self):
        """获取所有账号名称"""
        return [self.account_list.item(i).text() 
               for i in range(self.account_list.count())]
    
    def set_accounts(self, accounts):
        """设置账号列表"""
        self.account_list.clear()
        for account in accounts:
            self.account_list.addItem(account)

class FolderItemWidget(QWidget):
    """自定义列表项部件，包含文件夹路径和名称"""
    def __init__(self, path, name, parent=None):
        super().__init__(parent)
        self.path = path
        self.name = name
        self.init_ui()
    
    def init_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(15, 5, 15, 5)
        
        # 名称标签
        self.name_label = QLabel(self.name)
        self.name_label.setFont(QFont("PingFang SC", 10))
        self.name_label.setFixedWidth(200)
        
        # 路径标签
        self.path_label = QLabel(self.path)
        self.path_label.setFont(QFont("PingFang SC", 9))
        self.path_label.setStyleSheet("color: #666;")
        
        # 添加到布局
        layout.addWidget(self.name_label)
        layout.addWidget(self.path_label)
        layout.addStretch()
        
        self.setLayout(layout)

class FolderSelectorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        # 添加下面这行代码设置窗口图标
        icon = resource_path('icon.png')
        self.setWindowIcon(QIcon(icon))
        down = Path(resource_path('down.png')).as_posix()
        self.select_style = f"""
            QComboBox {{
                combobox-popup: 0;
                font-family: PingFang SC;
                font-size: 14px;
                padding: 5px 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                min-height: 28px;
                font-weight: bold;
            }}
            QComboBox:hover {{
                border: 1px solid #aaa;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left-width: 1px;
                border-left-color: #ddd;
                border-left-style: solid;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
            }}
            QComboBox::down-arrow {{
                image: url({down});
                width: 14px;
                height: 14px;
            }}
            QComboBox QAbstractItemView {{
                font-family: PingFang SC;
                font-size: 13px;
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background: white;
                selection-background-color: #5c9eff;
                selection-color: white;
                outline: 0;
                margin: 0;
            }}
            QComboBox QAbstractItemView::item {{
                height: 30px;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: #5c9eff; 
                color: white;
            }}
        """
        self.init_settings()
        self.init_data()
        self.init_ui()

    def init_settings(self):
        """初始化设置"""
        self.setWindowTitle("多配置管理器")
        self.setGeometry(100, 100, 1200, 700)
        self.encoding_backup = ''
        self.encoding_format = ''
        self.encoding_source = ''
    
    def init_data(self):
        """初始化数据"""
        self.accounts = {}  # 存储账号数据
        self.function4_config_name = '' # 存储账号的选项四的配置文件名
        self.current_account = None  # 当前账号
        self.folders = {}  # 存储文件夹数据：{path: name}
        self.equipment_configs = {}  # 存储装备配置数据
        self.load_config()  # 加载保存的配
    
    def init_ui(self):
        """初始化用户界面"""
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # 主布局（水平分割左中右三部分）
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(20)
        
        # 左侧面板（文件夹列表部分）
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel, 40)  # 左侧占40%宽度
        
        # 中间面板（功能部分）
        center_panel = self.create_center_panel()
        main_layout.addWidget(center_panel, 32)  # 中间占30%宽度
        
        # 右侧面板（日志部分）
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel, 28)  # 右侧占30%宽度
        
        main_widget.setLayout(main_layout)
        self.update_list_widget()  # 初始化列表显示
    
    def create_left_panel(self):
        """创建左侧面板"""
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        # 账号管理部分
        account_group = self.create_account_group()
        layout.addWidget(account_group)
        
        # 标题标签
        title_label = QLabel("已选择的配置文件夹:")
        title_label.setStyleSheet("""
            font-size: 16px; 
            font-weight: bold;
            font-family: PingFang SC;
            color: #333;
        """)
        layout.addWidget(title_label)
        
        # 列表部件，显示已选择的文件夹
        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setStyleSheet("""
            QListWidget {
                font-family: PingFang SC;
                font-size: 12px;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 5px;
                background: white;
            }
            QListWidget::item {
                border-bottom: 1px solid #eee;
                height: 50px;
            }
            QListWidget::item:hover {
                background: #f5f5f5;
            }
        """)
        # 添加双击打开文件夹功能
        self.list_widget.itemDoubleClicked.connect(self.open_folder)
        layout.addWidget(self.list_widget)
        
        # 按钮布局
        button_layout = self.create_folder_buttons()
        layout.addLayout(button_layout)
        
        panel.setLayout(layout)
        return panel
    
    def create_center_panel(self):
        """创建中间面板（功能部分）"""
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        layout.setAlignment(Qt.AlignTop)
        
        # 功能选项组
        function_group = self.create_function_group()
        layout.addWidget(function_group)
        
        panel.setLayout(layout)
        return panel
    
    def create_right_panel(self):
        """创建右侧面板（日志部分）"""
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        # 日志显示区域
        log_group = self.create_log_group()
        layout.addWidget(log_group)
        
        panel.setLayout(layout)
        return panel
    
    def open_folder(self, item):
        """双击打开文件夹"""
        widget = self.list_widget.itemWidget(item)
        if widget and os.path.exists(widget.path):
            try:
                if sys.platform == 'win32':
                    os.startfile(widget.path)
                elif sys.platform == 'darwin':
                    subprocess.Popen(['open', widget.path])
                else:
                    subprocess.Popen(['xdg-open', widget.path])
            except Exception as e:
                QMessageBox.warning(self, "警告", f"无法打开文件夹: {str(e)}")
    
    def create_account_group(self):
        """创建账号管理组"""
        group = QGroupBox("账号管理")
        group.setStyleSheet("""
            QGroupBox {
                font-family: PingFang SC;
                font-size: 14px;
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
            }
        """)
        layout = QHBoxLayout()
        
        # 账号选择下拉菜单
        self.account_combo = QComboBox()
        self.account_combo.setItemDelegate(StyledComboBoxDelegate(self.account_combo))
        self.account_combo.setStyleSheet(self.select_style)
        self.account_combo.addItems(self.accounts.keys())
        if self.current_account:
            self.account_combo.setCurrentText(self.current_account)
        self.account_combo.currentTextChanged.connect(self.change_account)
        layout.addWidget(self.account_combo, 70)
        
        # 账号管理按钮
        self.manage_accounts_btn = QPushButton("管理账号")
        self.manage_accounts_btn.setStyleSheet("""
            QPushButton {
                padding: 5px 10px;
                font-family: PingFang SC;
                font-size: 14px;
                background: #5c9eff;
                color: white;
                border: none;
                border-radius: 4px;
                min-height: 30px;
            }
            QPushButton:hover {
                background: #4d8ce5;
            }
        """)
        self.manage_accounts_btn.clicked.connect(self.manage_accounts)
        layout.addWidget(self.manage_accounts_btn, 30)
        
        group.setLayout(layout)
        return group
    
    def create_folder_buttons(self):
        """创建文件夹操作按钮"""
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        # 添加文件夹按钮
        add_button = QPushButton("添加配置文件夹")
        add_button.setStyleSheet("""
            QPushButton {
                padding: 8px 15px;
                font-family: PingFang SC;
                font-size: 14px;
                min-width: 100px;
                background: #5c9eff;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #4d8ce5;
            }
        """)
        add_button.clicked.connect(self.add_folder)
        button_layout.addWidget(add_button)
        
        # 编辑名称按钮
        edit_button = QPushButton("编辑名称")
        edit_button.setStyleSheet("""
            QPushButton {
                padding: 8px 15px;
                font-family: PingFang SC;
                font-size: 14px;
                min-width: 100px;
                background: #6c757d;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #5a6268;
            }
        """)
        edit_button.clicked.connect(self.edit_name)
        button_layout.addWidget(edit_button)
        
        # 移除选中文件夹按钮
        remove_button = QPushButton("移除选中")
        remove_button.setStyleSheet("""
            QPushButton {
                padding: 8px 15px;
                font-family: PingFang SC;
                font-size: 14px;
                min-width: 100px;
                background: #dc3545;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #c82333;
            }
        """)
        remove_button.clicked.connect(self.remove_folder)
        button_layout.addWidget(remove_button)
        
        return button_layout
    
    def create_function_group(self):
        """创建功能选项组"""
        group = QGroupBox("功能选项")
        group.setStyleSheet("""
            QGroupBox {
                font-family: PingFang SC;
                font-size: 14px;
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
            }
        """)
        self.function_layout = QVBoxLayout()
        
        # 功能选择下拉菜单
        self.function_combo = QComboBox()
        self.function_combo.setItemDelegate(StyledComboBoxDelegate(self.function_combo))
        self.function_combo.setStyleSheet(self.select_style)
        self.function_combo.addItem("请选择功能...")
        self.function_combo.addItem("1. 替换所有配置的指定装备")
        self.function_combo.addItem("2. 替换其他配置的指定装备配置")
        self.function_combo.addItem("3. 复制默认设置到所选配置中")
        self.function_combo.addItem("4. 替换指定配置选项")
        self.function_combo.currentIndexChanged.connect(self.on_function_changed)
        self.function_layout.addWidget(self.function_combo)
        
        # 功能1的输入控件容器
        self.function1_container = self.create_function1_widget()
        self.function_layout.addWidget(self.function1_container)
        
        # 功能2的输入控件容器
        self.function2_container = self.create_function2_widget()
        self.function_layout.addWidget(self.function2_container)
        
        # 功能3的输入控件容器
        self.function3_container = self.create_function3_widget()
        self.function_layout.addWidget(self.function3_container)
        
        # 功能4的输入控件容器
        self.function4_container = self.create_function4_widget()
        self.function_layout.addWidget(self.function4_container)
        
        # 添加执行按钮
        self.execute_button = QPushButton("执行选定功能")
        self.execute_button.setStyleSheet("""
            QPushButton {
                padding: 10px 20px;
                font-family: PingFang SC;
                font-size: 14px;
                font-weight: bold;
                background: #28a745;
                color: white;
                border: none;
                border-radius: 4px;
                margin-top: 30px;
            }
            QPushButton:hover {
                background: #218838;
            }
        """)
        self.execute_button.clicked.connect(self.execute_function)
        self.execute_button.hide()
        self.function_layout.addWidget(self.execute_button)
        
        # 添加备份复选框选项
        self.backup_checkbox = QCheckBox("执行前创建备份")
        self.backup_checkbox.setChecked(True)
        self.backup_checkbox.setStyleSheet("""
            QCheckBox {
                font-family: PingFang SC;
                font-size: 12px;
            }
        """)
        self.backup_checkbox.hide()
        self.function_layout.addWidget(self.backup_checkbox)
        
        group.setLayout(self.function_layout)
        return group
        
    def create_function1_widget(self):
        """创建功能1的控件"""
        container = QWidget()
        layout = QFormLayout()
    
        # 目标配置选择
        self.target_equipment_combo = CheckableComboBox()
        layout.addRow('目标配置:', self.target_equipment_combo)

        self.current_equipment_input = QLineEdit()
        self.current_equipment_input.setPlaceholderText("输入当前装备名称")
        self.current_equipment_input.setStyleSheet("""
            QLineEdit {
                padding: 5px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)
        
        self.replace_equipment_input = QLineEdit()
        self.replace_equipment_input.setPlaceholderText("输入替换装备名称")
        self.replace_equipment_input.setStyleSheet("""
            QLineEdit {
                padding: 5px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)
    
        layout.addRow("当前装备:", self.current_equipment_input)
        layout.addRow("替换装备:", self.replace_equipment_input)
        
        container.setLayout(layout)
        container.hide()
        return container
    
    def create_function2_widget(self):
        """创建功能2的控件"""
        container = QWidget()
        layout = QFormLayout()
        
        # 源配置下拉菜单
        self.source_config_combo = QComboBox()
        self.source_config_combo.setItemDelegate(StyledComboBoxDelegate(self.source_config_combo))
        self.source_config_combo.setPlaceholderText("选择源配置")
        self.source_config_combo.setStyleSheet(self.select_style)
        self.source_config_combo.currentIndexChanged.connect(self.load_equipment_configs)
        layout.addRow("源配置:", self.source_config_combo)
        
        # 装备配置下拉菜单
        self.equipment_config_combo = QComboBox()
        self.equipment_config_combo.setItemDelegate(StyledComboBoxDelegate(self.equipment_config_combo))
        self.equipment_config_combo.setPlaceholderText("选择装备配置")
        self.equipment_config_combo.setStyleSheet(self.select_style)
        layout.addRow("装备配置:", self.equipment_config_combo)

        # 目标配置下拉菜单（多选）
        self.target_config_combo = CheckableComboBox()
        layout.addRow("3. 目标配置:", self.target_config_combo)
        
        # 刷新装备配置按钮
        self.refresh_equipment_btn = QPushButton("刷新装备配置")
        self.refresh_equipment_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 10px;
                font-family: PingFang SC;
                font-size: 14px;
                background: #6c757d;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #5a6268;
            }
        """)
        self.refresh_equipment_btn.clicked.connect(self.refresh_equipment_configs)
        layout.addRow(self.refresh_equipment_btn)
        
        container.setLayout(layout)
        container.hide()
        return container
    
    def create_function3_widget(self):
        """创建功能3的控件"""
        container = QWidget()
        layout = QFormLayout()
        
        # 源配置下拉菜单
        self.source_default_combo = QComboBox()
        self.source_default_combo.setItemDelegate(StyledComboBoxDelegate(self.source_default_combo))
        self.source_default_combo.setPlaceholderText("选择源配置")
        self.source_default_combo.setStyleSheet(self.select_style)
        layout.addRow("源配置:", self.source_default_combo)
        
        # 目标配置下拉菜单
        self.target_default_combo = CheckableComboBox()
        layout.addRow("2. 目标配置:", self.target_default_combo)
        
        container.setLayout(layout)
        container.hide()
        return container
    
    def create_function4_widget(self):
        """创建功能4的控件"""
        container = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # 提示标签
        info_label = QLabel("该选项只会读取默认设置，需要其他设置则读取设置后保存")
        info_label.setStyleSheet("""
            font-family: PingFang SC; 
            font-size: 12px; 
            color: #666;
            padding: 5px;
            background: #f8f9fa;
            border-radius: 4px;
        """)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # 源配置下拉菜单
        layout.addWidget(QLabel("1. 源配置:"))
        self.source_option_combo = QComboBox()
        self.source_option_combo.setItemDelegate(StyledComboBoxDelegate(self.source_option_combo))
        self.source_option_combo.setPlaceholderText("选择源配置")
        self.source_option_combo.setStyleSheet(self.select_style)
        layout.addWidget(self.source_option_combo)
        
        # 目标配置下拉菜单
        layout.addWidget(QLabel("2. 目标配置:"))
        self.target_option_combo = CheckableComboBox()
        self.target_option_combo.setPlaceholderText("选择目标配置")
        layout.addWidget(self.target_option_combo)
        
        # 说明使用自定义配置文件还是Default.save
        custom_file_info = QLabel("输入配置名称将使用 [配置名称]，不输入则使用目标角色的当前配置")
        custom_file_info.setStyleSheet("""
            font-family: PingFang SC; 
            font-size: 11px; 
            color: #888;
            padding: 3px;
            background: #fff3cd;
            border-radius: 3px;
            margin-bottom: 5px;
        """)
        layout.addWidget(custom_file_info)

         # 配置名称输入框（新增）
        self.config_name_input = QLineEdit()
        self.config_name_input.setPlaceholderText("输入配置名称（可选，留空则使用当前配置）")
        self.config_name_input.setStyleSheet("""
            QLineEdit {
                padding: 5px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)

        # 加载之前保存的配置名称
        self.config_name_input.setText(self.function4_config_name)

        layout.addWidget(QLabel("配置名称（可选）:（建议所有角色的配置同一个名称）"))
        layout.addWidget(self.config_name_input)
        
        # 选项复选框 - 使用网格布局分成两列
        options_group = QGroupBox("3. 选择要替换的选项")
        options_group.setStyleSheet("""
            QGroupBox {
                font-family: PingFang SC;
                font-size: 12px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)
        options_layout = QVBoxLayout()
        
        # 添加"全选"复选框
        self.select_all_check = QCheckBox("全选")
        self.select_all_check.setStyleSheet("font-weight: bold;")
        self.select_all_check.stateChanged.connect(self.toggle_select_all)
        options_layout.addWidget(self.select_all_check)
        
        # 添加分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        options_layout.addWidget(separator)
        
        # 使用网格布局放置其他复选框
        grid_layout = QGridLayout()
        
        # 第一列复选框
        self.item_use_check = QCheckBox("保护吃药")
        self.skill_buff_check = QCheckBox("技能-辅助技能")
        self.pet_build_check = QCheckBox("智能联合宠物技能")
        self.item_filter_check = QCheckBox("物品设置")
        self.filter_pick2_check = QCheckBox("额外模糊过滤")
        self.filter_throw2_check = QCheckBox("额外模糊保留")
        
        # 第二列复选框
        self.item_buff_check = QCheckBox("保护-其他操作")
        self.diy_trigger_check = QCheckBox("DIY指令")
        self.item_disassemble_check = QCheckBox("物品分解")
        self.filter_pick1_check = QCheckBox("额外模糊拾取")
        self.filter_throw1_check = QCheckBox("额外模糊丢弃")
        self.store_items_check = QCheckBox("存取材料")

        # 添加复选框到网格布局
        grid_layout.addWidget(self.item_use_check, 0, 0)
        grid_layout.addWidget(self.skill_buff_check, 1, 0)
        grid_layout.addWidget(self.pet_build_check, 2, 0)
        grid_layout.addWidget(self.item_filter_check, 3, 0)
        grid_layout.addWidget(self.filter_pick2_check, 4, 0)
        grid_layout.addWidget(self.filter_throw2_check, 5, 0)
        
        grid_layout.addWidget(self.item_buff_check, 0, 1)
        grid_layout.addWidget(self.diy_trigger_check, 1, 1)
        grid_layout.addWidget(self.item_disassemble_check, 2, 1)
        grid_layout.addWidget(self.filter_pick1_check, 3, 1)
        grid_layout.addWidget(self.filter_throw1_check, 4, 1)
        grid_layout.addWidget(self.store_items_check, 5, 1)
        
        options_layout.addLayout(grid_layout)
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        container.setLayout(layout)
        container.hide()
        return container
    
    def encode_data(self, value, encoding):
        s1 = json.dumps(value)
        s2_bytes = s1.encode('latin1')
        s2 = s2_bytes.decode(encoding)
        v = json.loads(s2)
        return v

    def toggle_select_all(self, state):
        """全选/取消全选所有选项"""
        checkboxes = [
            self.item_use_check,
            self.item_buff_check,
            self.skill_buff_check,
            self.diy_trigger_check,
            self.pet_build_check,
            self.item_disassemble_check,
            self.item_filter_check,
            self.filter_pick1_check,
            self.filter_pick2_check,
            self.filter_throw1_check,
            self.filter_throw2_check,
            self.store_items_check,
        ]
        
        for checkbox in checkboxes:
            checkbox.setChecked(state == Qt.Checked)

    def create_log_group(self):
        """创建日志组（带滚动条）"""
        group = QGroupBox("操作日志")
        group.setStyleSheet("""
            QGroupBox {
                font-family: PingFang SC;
                font-size: 14px;
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
            }
        """)
        layout = QVBoxLayout()
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        
        # 创建日志内容部件
        log_content = QWidget()
        log_content.setStyleSheet("background: #f8f9fa;")
        log_layout = QVBoxLayout(log_content)
        log_layout.setContentsMargins(10, 10, 10, 10)
        
        self.log_label = QLabel("等待执行操作...")
        self.log_label.setStyleSheet("""
            font-family: PingFang SC;
            font-size: 12px;
            color: #666;
        """)
        self.log_label.setWordWrap(True)
        self.log_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        log_layout.addWidget(self.log_label)
        log_layout.addStretch()
        
        # 设置滚动区域的内容
        scroll_area.setWidget(log_content)
        layout.addWidget(scroll_area)
        
        group.setLayout(layout)
        return group
    
    # def read_default_save(self, file_path):
    #     """读取 Default.save 文件，自动检测编码（GB2312 或 Windows-1252）"""
    #     with open(file_path, 'rb') as f:
    #         raw_bytes = f.read()
    #     try:
    #         # 优先尝试 GB2312 解码
    #         self.encoding_backup = 'gb2312'
    #         content = raw_bytes.decode('gb2312')
    #         return json.loads(content)
    #     except UnicodeDecodeError:
    #         self.encoding_backup = 'windows-1252'
    #         try:
    #             # 如果 GB2312 失败，尝试 Windows-1252
    #             with open(file_path, 'r', encoding='windows-1252') as f:
    #                 return json.load(f)
    #         except Exception as e:
    #             raise ValueError(f"无法解码文件 {file_path}: {str(e)}")
    #     except json.JSONDecodeError:
    #         raise ValueError(f"文件 {file_path} 不是有效的 JSON 格式")
    #     except Exception as e:
    #         raise ValueError(f"读取文件 {file_path} 时出错: {str(e)}")
    
    def read_default_save(self, file_path):
        """读取 Default.save 文件，自动检测编码（GB2312 或 Windows-1252）"""
        try:
            # 优先尝试 GB2312 解码
            self.encoding_backup = 'gb2312'
            with open(file_path, 'r', encoding='gb2312') as f:
                return json.load(f)
        except UnicodeDecodeError:
            self.encoding_backup = 'gb2312'
            try:
                # 如果 GB2312 失败，尝试强制读取 gb2312
                with open(file_path, 'r', encoding='gb2312', errors='ignore') as f:
                    content = f.read()

                # 写入 tmp 文件
                temp_filename = file_path + '.tmp'
                with open(temp_filename, 'w', encoding='gb2312') as f:
                    f.write(content)
                # 替换原文件
                os.replace(temp_filename, file_path)
                
                # 重新读取出来
                with open(file_path, 'r', encoding='gb2312') as f:
                    return json.load(f)
            except Exception as e:
                raise ValueError(f"无法解码文件 {file_path}: {str(e)}")
        except json.JSONDecodeError:
            raise ValueError(f"文件 {file_path} 不是有效的 JSON 格式")
        except Exception as e:
            raise ValueError(f"读取文件 {file_path} 时出错: {str(e)}")

    def write_default_save(self, file_path, data):
        """写入 Default.save 文件，使用检测到的编码"""
        try:
            with open(file_path, 'w', encoding=self.encoding_format) as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            raise ValueError(f"写入文件 {file_path} 时出错: {str(e)}")
    
    def load_config(self):
        """从文件加载配置"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.accounts = data.get("accounts", {})
                    
                    # 如果有账号数据，默认选择第一个账号
                    if self.accounts:
                        self.current_account = next(iter(self.accounts.keys()))
                        self.folders = self.accounts[self.current_account].get("configurations", {})
                        self.function4_config_name = self.accounts[self.current_account].get("function4_config_name", '')
            except Exception as e:
                QMessageBox.warning(self, "警告", f"加载配置文件失败: {str(e)}")
    
    def save_config(self):
        """保存配置到文件"""
        if self.current_account:
            # 更新当前账号的配置
            self.accounts[self.current_account] = {
                "configurations": self.folders,
                "count": len(self.folders),
                'function4_config_name': self.function4_config_name,
            }
        
        data = {
            "accounts": self.accounts
        }
        
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存配置文件失败: {str(e)}")
    
    def on_function_changed(self, index):
        """当功能选择发生变化时"""
        # 隐藏所有功能容器
        self.function1_container.hide()
        self.function2_container.hide()
        self.function3_container.hide()
        self.function4_container.hide()
        self.execute_button.show()
        self.backup_checkbox.show()
        
        # 根据选择显示对应的容器
        if index == 1:  # 替换所有配置的指定装备
            self.function1_container.show()
            self.update_equipment_config_combos()
        elif index == 2:  # 替换其他配置的指定装备配置
            self.function2_container.show()
            self.update_source_config_combo()
        elif index == 3:  # 复制默认设置到所选配置中
            self.function3_container.show()
            self.update_default_config_combos()
        elif index == 4:  # 替换指定配置选项
            self.function4_container.show()
            self.update_option_config_combos()
        else:
            self.backup_checkbox.hide()
            self.execute_button.hide()

    def update_option_config_combos(self):
        """更新功能4的下拉菜单"""
        self.source_option_combo.clear()
        self.target_option_combo.clear()
        
        # 添加所有配置选项
        for path, name in self.folders.items():
            self.source_option_combo.addItem(name, path)

        # 添加目标配置选项，首先是"所有配置"选项
        all_config_item = QStandardItem("所有配置")
        self.target_option_combo.model().appendRow(all_config_item)
        all_config_item.setCheckable(True)
        all_config_item.setCheckState(Qt.Checked)  # 默认选中
        all_config_item.setData("all")

        # 添加其他配置选项
        for path, name in self.folders.items():
            item = QStandardItem(name)
            item.setCheckable(True)
            item.setCheckState(Qt.Unchecked)
            item.setData(path)
            item.setEnabled(False)  # 初始时禁用，因为"所有配置"已选中
            self.target_option_combo.model().appendRow(item)
        
        # 连接信号，处理选择变化
        self.target_option_combo.model().itemChanged.connect(
            lambda item: self.handle_target_selection_change(item, self.target_option_combo)
        )

        # 默认选中第一个源配置
        if self.source_option_combo.count() > 0:
            self.source_option_combo.setCurrentIndex(0)

    def handle_target_selection_change(self, item, combo_box):
        """处理目标配置选择变化"""
        model = combo_box.model()

        # 获取"所有配置"项（总是第一个）
        all_config_item = model.item(0)
        
        if item == all_config_item:
            # 处理"所有配置"项的选择变化
            if item.checkState() == Qt.Checked:
                # 选中"所有配置"时，禁用其他选项并取消选中
                for i in range(1, model.rowCount()):
                    other_item = model.item(i)
                    other_item.setEnabled(False)
                    other_item.setCheckState(Qt.Unchecked)
            else:
                # 取消选中"所有配置"时，启用其他选项
                for i in range(1, model.rowCount()):
                    model.item(i).setEnabled(True)
                # 禁用"所有配置"项，防止重新选择
                all_config_item.setEnabled(False)
        else:
            # 处理其他选项的选择变化
            if item.checkState() == Qt.Checked:
                # 当选中任何其他选项时，取消选中"所有配置"并禁用
                all_config_item.setCheckState(Qt.Unchecked)
                all_config_item.setEnabled(False)
            
            # 检查是否至少有一个选项被选中
            has_selection = any(
                model.item(i).checkState() == Qt.Checked 
                for i in range(1, model.rowCount())
            )
            
            # 如果没有选中任何选项，重新启用"所有配置"
            if not has_selection:
                all_config_item.setEnabled(True)
                all_config_item.setCheckState(Qt.Checked)

    def update_default_config_combos(self):
        """更新功能3的下拉菜单"""
        self.source_default_combo.clear()
        self.target_default_combo.clear()
        
        # 添加源配置选项
        for path, name in self.folders.items():
            self.source_default_combo.addItem(name, path)

        # 添加目标配置选项 - "所有配置"
        all_config_item = QStandardItem("所有配置")
        self.target_default_combo.model().appendRow(all_config_item)
        all_config_item.setCheckable(True)
        all_config_item.setCheckState(Qt.Checked)  # 默认选中
        all_config_item.setData("all")

        # 添加其他配置选项
        for path, name in self.folders.items():
            item = QStandardItem(name)
            item.setCheckable(True)
            item.setCheckState(Qt.Unchecked)
            item.setData(path)
            item.setEnabled(False)  # 初始时禁用，因为"所有配置"已选中
            self.target_default_combo.model().appendRow(item)
        
        # 连接信号
        self.target_default_combo.model().itemChanged.connect(
            lambda item: self.handle_target_selection_change(item, self.target_default_combo)
        )
        
        # 默认选中第一个源配置
        if self.source_default_combo.count() > 0:
            self.source_default_combo.setCurrentIndex(0)
        
        # 当源配置变化时，更新目标配置选项
        self.source_default_combo.currentIndexChanged.connect(self.on_source_default_changed)

    def on_source_default_changed(self):
        """当源配置变化时，更新目标配置选项"""
        current_source = self.source_default_combo.currentData()
        model = self.target_default_combo.model()

        # 禁用源配置对应的目标选项
        for i in range(1, model.rowCount()):
            item = model.item(i)
            if item.data() == current_source:
                item.setEnabled(False)
                item.setCheckState(Qt.Unchecked)
            else:
                # 如果当前不是"所有配置"模式，则启用
                if model.item(0).checkState() != Qt.Checked:
                    item.setEnabled(True)

    def update_source_config_combo(self):
        """更新源配置下拉菜单，同时更新目标配置"""
        self.source_config_combo.clear()
        self.target_config_combo.clear()

        for path, name in self.folders.items():
            self.source_config_combo.addItem(name, path)
        
        # 如果有选中项，默认选中第一个
        if self.source_config_combo.count() > 0:
            self.source_config_combo.setCurrentIndex(0)
            self.load_equipment_configs()

        # 添加目标配置选项 - "所有配置"
        all_config_item = QStandardItem("所有配置")
        self.target_config_combo.model().appendRow(all_config_item)
        all_config_item.setCheckable(True)
        all_config_item.setCheckState(Qt.Checked)  # 默认选中
        all_config_item.setData("all")
        
        # 添加其他配置选项
        for path, name in self.folders.items():
            item = QStandardItem(name)
            item.setCheckable(True)
            item.setCheckState(Qt.Unchecked)
            item.setData(path)
            item.setEnabled(False)  # 初始时禁用，因为"所有配置"已选中
            self.target_config_combo.model().appendRow(item)
        
        # 连接信号
        self.target_config_combo.model().itemChanged.connect(
            lambda item: self.handle_target_selection_change(item, self.target_config_combo)
        )
    
    def update_equipment_config_combos(self):
        """更新功能1的目标配置下拉菜单"""
        self.target_equipment_combo.clear()
        
        # 添加"所有配置"选项
        all_config_item = QStandardItem("所有配置")
        self.target_equipment_combo.model().appendRow(all_config_item)
        all_config_item.setCheckable(True)
        all_config_item.setCheckState(Qt.Checked)  # 默认选中
        all_config_item.setData("all")
        
        # 添加其他配置选项
        for path, name in self.folders.items():
            item = QStandardItem(name)
            item.setCheckable(True)
            item.setCheckState(Qt.Unchecked)
            item.setData(path)
            item.setEnabled(False)  # 初始时禁用，因为"所有配置"已选中
            self.target_equipment_combo.model().appendRow(item)
        
        # 连接信号
        self.target_equipment_combo.model().itemChanged.connect(
            lambda item: self.handle_target_selection_change(item, self.target_equipment_combo)
        )

    def load_equipment_configs(self):
        """从Config.save文件加载装备配置"""
        selected_path = self.source_config_combo.currentData()
        if not selected_path:
            return
            
        config_file = os.path.join(selected_path, "Config.save")
        
        # 清空现有配置
        self.equipment_configs = {}
        self.equipment_config_combo.clear()
        
        if not os.path.exists(config_file):
            self.log_operation(f"错误: {config_file} 不存在")
            QMessageBox.warning(self, "警告", "找不到Config.save配置文件")
            return
            
        try:
            with open(config_file, 'r', encoding='gb2312') as f:
                suit_data = json.load(f)
                diysuit_items = suit_data.get("diysuit_item", [])
                
                if not diysuit_items:
                    self.log_operation(f"警告: {selected_path} 中没有找到diysuit_item配置")
                    QMessageBox.warning(self, "警告", "该配置中没有找到diysuit_item数据")
                    return
                
                for index, item in enumerate(diysuit_items, 1):
                    config_name = item.get("name", f"未命名配置_{index}")
                    self.equipment_configs[f"config_{index}"] = {
                        "name": config_name,
                        "data": item.get("data")
                    }
                    self.equipment_config_combo.addItem(config_name, f"config_{index}")
                
                self.log_operation(f"成功加载 {len(diysuit_items)} 个装备配置")
        except json.JSONDecodeError:
            self.log_operation(f"错误: {config_file} 不是有效的JSON文件")
            QMessageBox.critical(self, "错误", "Config.save文件格式错误，不是有效的JSON")
        except Exception as e:
            self.log_operation(f"加载装备配置出错: {str(e)}")
            QMessageBox.critical(self, "错误", f"加载装备配置失败: {str(e)}")

    def refresh_equipment_configs(self):
        """刷新装备配置"""
        self.load_equipment_configs()
        QMessageBox.information(self, "信息", "装备配置已刷新")
    
    def manage_accounts(self):
        """管理账号"""
        dialog = AccountDialog(self)
        dialog.set_accounts(self.accounts.keys())
        
        if dialog.exec_() == QDialog.Accepted:
            new_accounts = dialog.get_accounts()
            
            # 检查是否有账号被删除
            deleted_accounts = set(self.accounts.keys()) - set(new_accounts)
            for account in deleted_accounts:
                del self.accounts[account]
            
            # 检查是否有新账号添加
            added_accounts = set(new_accounts) - set(self.accounts.keys())
            for account in added_accounts:
                self.accounts[account] = {"configurations": {}, "count": 0}
            
            # 更新账号下拉菜单
            self.account_combo.clear()
            self.account_combo.addItems(self.accounts.keys())
            
            # 如果当前账号被删除，选择第一个账号
            if self.current_account not in self.accounts:
                if self.accounts:
                    self.current_account = next(iter(self.accounts.keys()))
                    self.account_combo.setCurrentText(self.current_account)
                    self.folders = self.accounts[self.current_account]["configurations"]
                    self.function4_config_name = self.accounts[self.current_account]["function4_config_name"]
                    self.config_name_input.setText(self.function4_config_name)
                    self.update_list_widget()
                else:
                    self.current_account = None
                    self.folders = {}
                    self.update_list_widget()
            
            # 保存配置
            self.save_config()
    
    def change_account(self, account_name):
        """切换当前账号"""
        if account_name in self.accounts:
            self.current_account = account_name
            self.folders = self.accounts[account_name].get("configurations", {})
            self.function4_config_name = self.accounts[account_name].get("function4_config_name", '')
            self.config_name_input.setText(self.function4_config_name)
            self.update_list_widget()
            self.log_operation(f"切换到账号: {account_name}")
    
    def add_folder(self):
        """打开文件夹选择对话框并添加选择的文件夹"""
        if not self.current_account:
            QMessageBox.warning(self, "警告", "请先选择或创建一个账号!")
            return
        
        folder = QFileDialog.getExistingDirectory(self, "选择配置文件夹")
        if not folder:  # 用户取消选择
            return
            
        if folder in self.folders:  # 避免重复添加
            QMessageBox.warning(self, "警告", "该配置文件夹已存在!")
            return
            
        # 获取文件夹名称
        name, ok = QInputDialog.getText(
            self, '输入名称', 
            '为这个配置输入一个名称:', 
            text=os.path.basename(folder)  # 默认使用文件夹名
        )
        
        if not ok:
            return
            
        if not name:
            QMessageBox.warning(self, "警告", "名称不能为空!")
            return
            
        self.folders[folder] = name
        self.update_list_widget()
        self.log_operation(f"添加配置: {name} ({folder})")
        
        # 如果当前显示的是功能2或3或4，更新下拉菜单
        if self.function_combo.currentIndex() in (2, 3, 4):
            self.update_source_config_combo()
            self.update_default_config_combos()
            self.update_option_config_combos()
            
        # 自动保存配置
        self.save_config()
    
    def edit_name(self):
        """编辑选中文件夹的名称"""
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择一个配置!")
            return
        
        item = selected_items[0]
        widget = self.list_widget.itemWidget(item)
        old_name = widget.name
        path = widget.path
        
        # 获取新名称
        name, ok = QInputDialog.getText(
            self, '编辑名称', 
            '输入新的名称:', 
            text=old_name
        )
        
        if not ok:
            return
            
        if not name:
            QMessageBox.warning(self, "警告", "名称不能为空!")
            return
            
        self.folders[path] = name
        self.update_list_widget()
        self.log_operation(f"重命名配置: {old_name} -> {name}")
        
        # 如果当前显示的是功能2或3或4，更新下拉菜单
        if self.function_combo.currentIndex() in (2, 3, 4):
            self.update_source_config_combo()
            self.update_default_config_combos()
            self.update_option_config_combos()
            
        # 自动保存配置
        self.save_config()
    
    def remove_folder(self):
        """移除列表中选中的文件夹"""
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择要移除的配置!")
            return
        
        item = selected_items[0]
        widget = self.list_widget.itemWidget(item)
        path = widget.path
        name = widget.name
        
        reply = QMessageBox.question(
            self, '确认', 
            f'确定要移除配置 "{name}" 吗?', 
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.Yes
        )
        
        if reply != QMessageBox.Yes:
            return
            
        del self.folders[path]
        self.update_list_widget()
        self.log_operation(f"移除配置: {name}")
        
        # 如果当前显示的是功能2或3或4，更新下拉菜单
        if self.function_combo.currentIndex() in (2, 3, 4):
            self.update_source_config_combo()
            self.update_default_config_combos()
            self.update_option_config_combos()
            
        # 自动保存配置
        self.save_config()
    
    def update_list_widget(self):
        """更新列表部件显示"""
        self.list_widget.clear()
        
        for path, name in self.folders.items():
            # 创建自定义部件
            item_widget = FolderItemWidget(path, name)
            
            # 创建QListWidgetItem
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 60))  # 增大项高度
            
            # 添加到列表
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, item_widget)
    
    def normalize_string(self, s):
        """标准化字符串，统一处理特殊字符"""
        # 将中文点(・)和英文点(·)统一替换为中文点
        return s.replace('・', '・').replace('·', '・')
    
    def execute_function(self):
        """执行选定的功能"""
        if not self.current_account:
            QMessageBox.warning(self, "警告", "请先选择或创建一个账号!")
            return
            
        if not self.folders:
            QMessageBox.warning(self, "警告", "请先添加配置文件夹!")
            return
        
        selected_function = self.function_combo.currentIndex()
        if selected_function == 0:  # "请选择功能..."
            QMessageBox.warning(self, "警告", "请先选择一个功能!")
            return
        
        # 根据选择的功能调用相应的方法
        try:
            if selected_function == 1:
                self.execute_function1()
            elif selected_function == 2:
                self.execute_function2()
            elif selected_function == 3:
                self.execute_function3()
            elif selected_function == 4:
                self.execute_function4()
        except Exception as e:
            self.log_operation(f"执行过程中出错: {str(e)}")
            QMessageBox.critical(self, "错误", f"执行过程中出错: {str(e)}")
    
    def execute_function1(self):
        """功能1: 替换所有配置的指定装备"""
        current_equip = self.current_equipment_input.text().strip()
        replace_equip = self.replace_equipment_input.text().strip()

        if not current_equip:
            QMessageBox.warning(self, "警告", "请输入当前装备和替换装备名称!")
            return

        # 获取选中的目标配置
        model = self.target_equipment_combo.model()
        all_config_selected = model.item(0).checkState() == Qt.Checked
        
        if all_config_selected:
            target_configs = list(self.folders.items())
            target_name = "所有配置"
        else:
            target_configs = []
            for i in range(1, model.rowCount()):
                item = model.item(i)
                if item.checkState() == Qt.Checked:
                    target_configs.append((item.data(), item.text()))
            target_name = ", ".join([name for path, name in target_configs])
        
        if not target_configs:
            QMessageBox.warning(self, "警告", "请至少选择一个目标配置!")
            return

        self.log_operation(f"执行: 在{target_name}中替换装备 {current_equip} -> {replace_equip}")
        
        # 实际替换逻辑
        try:
            updated_files = 0
            total_updated = 0
            
            for path, name in target_configs:
                config_file = os.path.join(path, "Config.save")
                if not os.path.exists(config_file):
                    self.log_operation(f"跳过: {name} 没有Config.save文件")
                    continue
                
                # 备份原文件
                if self.backup_checkbox.isChecked():
                    self.backup_file(config_file)
                
                # 读取配置文件
                with open(config_file, 'r', encoding='gb2312') as f:
                    config_data = json.load(f)
                
                # 替换装备
                if "diysuit_item" in config_data:
                    updated = False
                    for item in config_data["diysuit_item"]:
                        if "data" in item and isinstance(item["data"], dict):
                            for equip_id, equip_name in item["data"].items():
                                # 修改这里，直接比较字符串，不进行任何处理
                                if self.normalize_string(equip_name) == self.normalize_string(current_equip):
                                    item["data"][equip_id] = self.normalize_string(replace_equip)
                                    total_updated += 1
                                    updated = True
                    
                    if updated:
                        # 写入更新后的文件
                        with open(config_file, 'w', encoding='gb2312') as f:
                            json.dump(config_data, f, indent=4, ensure_ascii=False)
                        updated_files += 1
                        self.log_operation(f"成功: 已在 {name} 中替换了装备")
            
            QMessageBox.information(self, "完成", 
                f"已在 {updated_files}/{len(self.folders)} 个配置文件中完成替换\n"
                f"共更新了 {total_updated} 处装备数据")
            
        except json.JSONDecodeError:
            self.log_operation("错误: 配置文件不是有效的JSON格式")
            QMessageBox.critical(self, "错误", "遇到无效的JSON配置文件")
        except Exception as e:
            self.log_operation(f"错误: {str(e)}")
            QMessageBox.critical(self, "错误", f"替换装备时出错: {str(e)}")
    
    def execute_function2(self):
        """功能2: 替换其他配置的指定装备配置"""
        if self.source_config_combo.currentIndex() == -1:
            QMessageBox.warning(self, "警告", "请选择源配置!")
            return
        
        if self.equipment_config_combo.currentIndex() == -1:
            QMessageBox.warning(self, "警告", "请选择装备配置!")
            return
        
    
        # 获取选中的目标配置
        model = self.target_config_combo.model()
        all_config_selected = model.item(0).checkState() == Qt.Checked
        
        if all_config_selected:
            # 选择"所有配置"时，排除源配置
            target_configs = [(path, name) for path, name in self.folders.items() 
                            if path != self.source_config_combo.currentData()]
            target_name = "所有配置"
        else:
            # 选择特定配置时
            target_configs = []
            for i in range(1, model.rowCount()):
                item = model.item(i)
                if item.checkState() == Qt.Checked:
                    path = item.data()
                    name = item.text()
                    if path != self.source_config_combo.currentData():  # 排除源配置
                        target_configs.append((path, name))
            target_name = ", ".join([name for path, name in target_configs])
        
        if not target_configs:
            QMessageBox.warning(self, "警告", "请至少选择一个目标配置!")
            return
        
        source_name = self.source_config_combo.currentText()
        config_id = self.equipment_config_combo.currentData()
        config_data = self.equipment_configs.get(config_id)
        
        if not config_data:
            QMessageBox.warning(self, "警告", "获取装备配置数据失败!")
            return
        
        target_config_name = config_data['name']
        self.log_operation(f"执行: 从配置 {source_name} 复制装备配置 {target_config_name} 的data到{target_name}")

        # 实际替换逻辑
        try:
            updated_count = 0
            
            for target_path, target_name in target_configs:
                target_file = os.path.join(target_path, "Config.save")
                if not os.path.exists(target_file):
                    continue
                    
                # 读取目标文件
                with open(target_file, 'r', encoding='gb2312') as f:
                    target_data = json.load(f)
                
                # 备份原文件
                if self.backup_checkbox.isChecked():
                    self.backup_file(target_file)
                
                # 更新diysuit_item中name匹配的data
                if "diysuit_item" in target_data:
                    updated = False
                    for item in target_data["diysuit_item"]:
                         if item.get("name") == target_config_name:
                            item["data"] = config_data["data"]
                            updated = True
                            break
                    
                    if updated:
                        # 写入更新
                        with open(target_file, 'w', encoding='gb2312') as f:
                            json.dump(target_data, f, indent=4, ensure_ascii=False)
                        updated_count += 1
                        self.log_operation(f"成功更新配置: {target_name}")
                    else:
                        self.log_operation(f"配置 {target_name} 中未找到名称匹配的装备")
                else:
                    self.log_operation(f"配置 {target_name} 中没有diysuit_item数据")
            
            QMessageBox.information(self, "成功", 
                f"已在 {updated_count}/{len(target_configs)} 个配置中更新了 {target_config_name} 的data数据")
        
        except json.JSONDecodeError:
            self.log_operation("错误: 目标文件不是有效的JSON格式")
            QMessageBox.critical(self, "错误", "目标配置文件不是有效的JSON格式")
        except Exception as e:
            self.log_operation(f"替换失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"替换装备配置失败: {str(e)}")
    
    def execute_function3(self):
        """功能3: 复制默认设置到所选配置中"""
        if self.source_default_combo.currentIndex() == -1:
            QMessageBox.warning(self, "警告", "请选择源配置!")
            return
        
        # 获取选中的目标配置
        model = self.target_default_combo.model()
        all_config_selected = model.item(0).checkState() == Qt.Checked
        
        if all_config_selected:
            target_configs = [(path, name) for path, name in self.folders.items() 
                            if path != self.source_default_combo.currentData()]
            target_name = "所有配置"
        else:
            target_configs = []
            for i in range(1, model.rowCount()):
                item = model.item(i)
                if item.checkState() == Qt.Checked:
                    path = item.data()
                    name = item.text()
                    if path != self.source_default_combo.currentData():  # 排除源配置
                        target_configs.append((path, name))
            target_name = ", ".join([name for path, name in target_configs])
        
        if not target_configs:
            QMessageBox.warning(self, "警告", "请至少选择一个目标配置!")
            return
        
        source_name = self.source_default_combo.currentText()
        self.log_operation(f"执行: 从配置 {source_name} 复制Default.save到 {target_name}")
        
        try:
            source_file = os.path.join(self.source_default_combo.currentData(), "Default.save")
            if not os.path.exists(source_file):
                QMessageBox.warning(self, "警告", f"源配置 {source_name} 中没有找到Default.save文件!")
                self.log_operation(f"错误: {source_name} 中没有Default.save文件")
                return


            # 处理每个目标配置
            success_count = 0
            for target_path, target_name in target_configs:
                target_file = os.path.join(target_path, "Default.save")
                
                # 备份目标文件
                if os.path.exists(target_file) and self.backup_checkbox.isChecked():
                    self.backup_file(target_file)
                
                # 复制文件
                shutil.copy2(source_file, target_file)
                self.log_operation(f"成功: 已将配置复制到 {target_name}")
                success_count += 1
            
            QMessageBox.information(
                self, "完成", 
                f"已成功复制到 {success_count}/{len(target_configs)} 个目标配置"
            )
            
        except Exception as e:
            self.log_operation(f"复制失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"复制Default.save文件失败: {str(e)}")
    
    def execute_function4(self):
        """功能4: 替换指定配置选项"""
        if self.source_option_combo.currentIndex() == -1:
            QMessageBox.warning(self, "警告", "请选择源配置!")
            return
        
        if not self.folders:
            QMessageBox.warning(self, "警告", "请先添加配置文件夹!")
            return

        # 检查是否至少选择了一个目标配置
        all_config_item = self.target_option_combo.model().item(0)
        if all_config_item.checkState() != Qt.Checked and len(self.target_option_combo.checkedItems()) == 0:
            QMessageBox.warning(self, "警告", "请至少选择一个目标配置!")
            return
        
        
        # 获取配置名称
        config_name = self.config_name_input.text().strip()
    
        # 确定文件名：如果有配置名称则使用 [配置名称].json，否则使用 Default.save
        if config_name:
            file_name = f"{config_name}.json"
        else:
            file_name = "Default.save"
        
        if not (self.item_use_check.isChecked() or 
               self.item_buff_check.isChecked() or 
               self.skill_buff_check.isChecked() or
               self.filter_pick1_check.isChecked() or
               self.filter_pick2_check.isChecked() or
               self.filter_throw1_check.isChecked() or
               self.filter_throw2_check.isChecked() or
               self.diy_trigger_check.isChecked() or
               self.pet_build_check.isChecked() or
               self.item_disassemble_check.isChecked() or
               self.item_filter_check.isChecked() or
               self.store_items_check.isChecked()):
            QMessageBox.warning(self, "警告", "请至少选择一个要替换的选项!")
            return
        
        source_path = self.source_option_combo.currentData()
        source_name = self.source_option_combo.currentText()
        
        # # 获取目标配置列表
        # if target_path == "all":  # 所有配置
        #     target_configs = [(path, name) for path, name in self.folders.items() 
        #                     if path != source_path]
        #     target_name = "所有配置"
        # else:
        #     if source_path == target_path:
        #         QMessageBox.warning(self, "警告", "源配置和目标配置不能相同!")
        #         return
        #     target_configs = [(target_path, self.target_option_combo.currentText())]
        #     target_name = self.target_option_combo.currentText()

        # self.log_operation(f"执行: 从配置 {source_name} 复制选定选项到 {target_name}")

        # 获取选中的目标配置
        target_configs = []
        all_config_selected = self.target_option_combo.model().item(0).checkState() == Qt.Checked

        if all_config_selected:
            # 选择"所有配置"时，排除源配置
            for path, name in self.folders.items():
                if path != source_path:
                    target_configs.append((path, name))
            target_name = "所有配置"
        else:
            # 选择特定配置时
            for i in range(self.target_option_combo.model().rowCount()):
                item = self.target_option_combo.model().item(i)
                if item.checkState() == Qt.Checked:
                    path = item.data()
                    name = item.text()
                    if path != source_path:  # 排除源配置
                        target_configs.append((path, name))
            
            if not target_configs:
                QMessageBox.warning(self, "警告", "没有有效的目标配置!")
                return
        
            target_name = ", ".join([name for path, name in target_configs])
        
        self.log_operation(f"执行: 从配置 {source_name} 复制选定选项到 {target_name}")
        
        current_file = ''
        try:
            # 读取源配置文件
            source_file = os.path.join(source_path, "Default.save")
            if not os.path.exists(source_file):
                QMessageBox.warning(self, "警告", f"源配置 {source_name} 中没有找到Default.save文件!")
                self.log_operation(f"错误: {source_name} 中没有Default.save文件")
                return
            
            # 使用新的读取方法处理编码问题
            source_data = self.read_default_save(source_file)
            self.encoding_source = self.encoding_backup
            
            # 确定要复制的字段
            fields_to_copy = []
            if self.item_use_check.isChecked():
                fields_to_copy.append(("item_use_data", "吃药"))
            if self.item_buff_check.isChecked():
                fields_to_copy.append(("item_buff_data", "buff药"))
            if self.skill_buff_check.isChecked():
                fields_to_copy.append(("skill_buff_data", "buff技能"))
            if self.filter_pick1_check.isChecked():
                fields_to_copy.append(("item_filter_pick_data_1", "额外模糊拾取"))
            if self.filter_pick2_check.isChecked():
                fields_to_copy.append(("item_filter_pick_data_2", "额外模糊过滤"))
            if self.filter_throw1_check.isChecked():
                fields_to_copy.append(("item_filter_throw_data_1", "额外模糊丢弃"))
            if self.filter_throw2_check.isChecked():
                fields_to_copy.append(("item_filter_throw_data_2", "额外模糊保留"))
            if self.diy_trigger_check.isChecked():
                fields_to_copy.append(("diytrigger", "DIY指令"))
            if self.pet_build_check.isChecked():
                fields_to_copy.append(("pet_build", "智能联合宠物技能"))
            if self.item_disassemble_check.isChecked():
                fields_to_copy.append(("item_filter_disassemble", "物品分解"))
            if self.item_filter_check.isChecked():
                fields_to_copy.append(("item_filter_1", "物品设置1"))
                fields_to_copy.append(("item_filter_2", "物品设置2"))
                fields_to_copy.append(("item_filter_3", "物品设置3"))
                fields_to_copy.append(("item_filter_4", "物品设置4"))
            if self.store_items_check.isChecked():
                fields_to_copy.append(("store_items", "存取材料"))

            # 处理每个目标配置
            updated_count = 0
            for target_path, target_name in target_configs:
                target_file = os.path.join(target_path, file_name)
                if not os.path.exists(target_file):
                    self.log_operation(f"跳过: {target_name} 没有 {file_name} 文件")
                    continue
                
                # 读取目标文件
                target_data = self.read_default_save(target_file)
                self.encoding_format = self.encoding_backup
                
                # 备份原文件
                if self.backup_checkbox.isChecked():
                    current_file = target_file
                    self.backup_file(target_file)
                
                # 替换选定字段
                updated = False
                for field, field_name in fields_to_copy:
                    if field in source_data:
                        target_data[field] = source_data[field]
                        self.log_operation(f"已更新: {target_name} 的 {field_name} 配置")
                        updated = True
                
                if updated:
                    # 写入更新后的文件
                    self.write_default_save(target_file, target_data)
                    updated_count += 1
            
            QMessageBox.information(
                self, "完成", 
                f"已成功更新 {updated_count}/{len(target_configs)} 个配置的选定选项"
            )

            if config_name:
                self.function4_config_name = config_name
                self.save_config()
            
        except json.JSONDecodeError:
            self.log_operation("错误: 配置文件不是有效的JSON格式")
            QMessageBox.critical(self, "错误", "配置文件格式错误，不是有效的JSON")
        except Exception as e:
            self.log_operation(f"替换失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"替换配置选项失败: {str(e)}")
            shutil.copy2(current_file + '.bak', current_file)
    
    def backup_file(self, target_file, message=None):
        """备份文件"""
        backup_file = target_file + ".bak"
        shutil.copy2(target_file, backup_file)
        if message:
            self.log_operation(message)
        else:
            self.log_operation(f"已备份文件: {backup_file}")

    def log_operation(self, message):
        """记录操作日志"""
        current_text = self.log_label.text()
        new_text = f"{message}\n{current_text}"
        self.log_label.setText(new_text)
        # 自动滚动到底部
        self.log_label.adjustSize()
        scroll_area = self.log_label.parent().parent()
        if isinstance(scroll_area, QScrollArea):
            scroll_area.verticalScrollBar().setValue(scroll_area.verticalScrollBar().maximum())


if __name__ == "__main__":
    # Windows高DPI支持
    if sys.platform == "win32":
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    
    # Qt高DPI支持
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # 设置全局字体和调色板
    font = QFont("PingFang SC", 12)
    app.setFont(font)
    
    # 设置调色板
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(240, 240, 240))
    palette.setColor(QPalette.WindowText, QColor(0, 0, 0))
    palette.setColor(QPalette.Base, QColor(255, 255, 255))
    palette.setColor(QPalette.AlternateBase, QColor(240, 240, 240))
    palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 220))
    palette.setColor(QPalette.ToolTipText, QColor(0, 0, 0))
    palette.setColor(QPalette.Text, QColor(0, 0, 0))
    palette.setColor(QPalette.Button, QColor(240, 240, 240))
    palette.setColor(QPalette.ButtonText, QColor(0, 0, 0))
    palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.Highlight, QColor(0, 120, 215))
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)
    
    window = FolderSelectorApp()
    window.show()
    sys.exit(app.exec_())
