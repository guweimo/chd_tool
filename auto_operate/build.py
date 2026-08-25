import os
import sys
import subprocess
import shutil
from pathlib import Path

# 确保控制台输出使用 UTF-8 编码，避免 GBK 下 emoji/中文报错
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


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
    print(f"[OK] 使用虚拟环境Python: {sys.executable}")


def compile_with_nuitka():
    """执行Nuitka编译"""
    project_dir = Path(__file__).parent
    dist_dir = project_dir / "dist"

    command = [
        sys.executable, "-m", "nuitka",
        "--onefile",
        "--windows-disable-console",
        "--enable-plugin=pyside6",
        "--windows-uac-admin",
        "--include-qt-plugins=sensible,platforms",
        f"--include-data-file={project_dir/'icon.png'}=icon.png",
        f"--windows-icon-from-ico={project_dir/'icon.ico'}",
        "--remove-output",
        f"--output-dir={dist_dir}",
        "--output-filename=auto_operate.exe",
        "--windows-company-name=guweimo",
        "--windows-product-name=RainbowIslandManager",
        "--windows-file-version=1.0.0",
        "--windows-product-version=1.0.0",
        "--windows-file-description=彩虹岛管理器",
        str(project_dir / "auto_operate.py")
    ]

    print("[RUN] 开始编译...")
    result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if result.returncode != 0:
        print("[FAIL] 编译失败：")
        print(result.stderr)
        return False
    return True


def deploy_to_target():
    """增量更新目标目录"""
    project_dir = Path(__file__).parent
    dist_dir = project_dir / "dist" / "auto_operate.dist"
    # 修改为目标部署路径（若留空则跳过部署）
    target_dir = Path(r"C:\Users\guweimo\Desktop\彩虹岛\auto_operate")

    if not dist_dir.exists():
        raise FileNotFoundError("编译输出目录不存在")

    print(f"[DEPLOY] 增量更新到: {target_dir}")
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

    print(f"[OK] 更新完成！路径: {target_dir}")


if __name__ == "__main__":
    try:
        ensure_venv_activated()
        compile_with_nuitka()
        # if compile_with_nuitka():
            # deploy_to_target()
    except Exception as e:
        print(f"[ERROR] 发生错误：{str(e)}")
        sys.exit(1)
