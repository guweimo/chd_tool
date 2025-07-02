## 使用 pyinstaller 打包

### 初始化：

管理员启动
```cmd 

pyinstaller --onefile --windowed --uac-admin --icon=icon.png index.py
```

```cmd
pyinstaller --onefile --windowed --icon=icon.png index.py

pyinstaller --onefile --windowed --upx-dir=C:\\SoftwareFiles\\Work\\upx-5.0.0-win64 --icon=icon.png index.py

python -OO -m PyInstaller --onefile --windowed --icon=icon.png index.py
```

### 下次执行：

```
pyinstaller index.spec
```

## 使用 nuitka 打包

### build

```cmd
ccc
```

```cmd
python -m nuitka     --standalone     --onefile     --windows-disable-console     --enable-plugin=pyqt5     --include-qt-plugins=sensible,platforms     --include-data-file=down.png=down.png     --include-data-file=icon.png=icon.png     --windows-icon-from-ico=icon.ico     --output-dir=dist     --remove-output     --output-filename="多配置管理.exe"     --windows-company-name="YourCompany"     --windows-product-name="MultiConfigManager"     --windows-file-version=1.0.0     --windows-product-version=1.0.0     --windows-file-description="多配置管理工具"     index.py
```
