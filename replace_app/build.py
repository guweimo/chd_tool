import os
import sys
import subprocess
import shutil
from pathlib import Path

def ensure_venv_activated():
    """激活上级目录的虚拟环境"""
    venv_path = Path(__file__).parent.parent / ".venv"
    if not venv_path.exists():
        raise RuntimeError(f"虚拟环境不存在于: {venv_path}")

    if os.name == 'nt':
        python_exec = venv_path / "Scripts" / "python.exe"
        os.environ["PATH"] = str(venv_path / "Scripts") + os.pathsep + os.environ["PATH"]
    else:
        python_exec = venv_path / "bin" / "python"
        os.environ["PATH"] = str(venv_path / "bin") + os.pathsep + os.environ["PATH"]

    if not python_exec.exists():
        raise RuntimeError(f"Python解释器不存在: {python_exec}")

    sys.executable = str(python_exec)
    print(f"✅ 使用虚拟环境Python: {sys.executable}")

def compile_with_nuitka():
    """执行Nuitka编译"""
    project_dir = Path(__file__).parent
    dist_dir = project_dir / "dist"
    
    command = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--windows-disable-console",
        "--enable-plugin=pyqt5",
        "--include-qt-plugins=sensible,platforms",
        f"--include-data-file={project_dir/'down.png'}=down.png",
        f"--include-data-file={project_dir/'icon.png'}=icon.png",
        f"--windows-icon-from-ico={project_dir/'icon.ico'}",
        "--remove-output",
        f"--output-dir={dist_dir}",
        "--output-filename=多配置管理.exe",
        "--windows-company-name=YourCompany",
        "--windows-product-name=MultiConfigManager",
        "--windows-file-version=1.0.0",
        "--windows-product-version=1.0.0",
        "--windows-file-description=多配置管理工具",
        str(project_dir / "index.py")
    ]

    print("🚀 开始编译...")
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print("❌ 编译失败：")
        print(result.stderr)
        return False
    return True

def deploy_to_target():
    """增量更新目标目录"""
    project_dir = Path(__file__).parent
    dist_dir = project_dir / "dist" / "index.dist"
    target_dir = Path(r"C:\Users\guweimo\Desktop\彩虹岛config\多配置管理")

    if not dist_dir.exists():
        raise FileNotFoundError("编译输出目录不存在")

    print(f"🔄 增量更新到: {target_dir}")
    target_dir.mkdir(parents=True, exist_ok=True)

    # 只覆盖dist中存在的文件/目录
    for item in dist_dir.glob("*"):
        dest = target_dir / item.name
        if dest.exists():
            if dest.is_file():
                dest.unlink()  # 删除目标文件
            else:
                shutil.rmtree(dest)  # 删除目标目录
        if item.is_dir():
            shutil.copytree(item, dest)  # 复制整个目录
        else:
            shutil.copy2(item, dest)  # 复制文件（保留元数据）

    print(f"✅ 更新完成！路径: {target_dir}")

if __name__ == "__main__":
    try:
        ensure_venv_activated()
        if compile_with_nuitka():
            deploy_to_target()
            if os.name == 'nt':
                os.startfile(r"C:\Users\guweimo\Desktop\彩虹岛config\多配置管理")
    except Exception as e:
        print(f"❌ 发生错误：{str(e)}")
        sys.exit(1)