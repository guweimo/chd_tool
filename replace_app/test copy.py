from PyQt5.QtWidgets import QComboBox, QListView, QStylePainter, QStyleOptionComboBox, QStyle, QApplication
from PyQt5.QtCore import Qt, QEvent, QPoint
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QPalette, QCursor
from pathlib import Path

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

# 使用示例
if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    
    combo = CheckableComboBox()
    combo.addItems(["苹果", "香蕉", "橙子", "葡萄", "西瓜"])
    
    # 显示当前选中的项目
    def show_selected():
        print("当前选中:", combo.checkedItems())
        print("对应数据:", combo.checkedData())
    
    combo.model().itemChanged.connect(show_selected)
    
    combo.show()
    sys.exit(app.exec_())