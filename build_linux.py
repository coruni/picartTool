#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyInstaller打包脚本(Linux版本)
用于将文件处理工具打包成适合飞牛OS运行的二进制文件
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# 全局应用名称，供多个函数使用
APP_NAME = "文件处理工具"

def get_pyinstaller_command():
    """生成PyInstaller打包命令(Linux版本)"""

    # 项目信息
    app_name = APP_NAME
    main_script = "main.py"

    # 收集所有需要包含的Python模块
    python_modules = [
        "main.py",
        "gui.py",
        "file_processor.py",
        "api_handler.py",
        "compression_handler.py",
        "image_processor.py",
        "logger.py",
        "config.py",
        "tools_config.py",
        "utils.py"
    ]

    # 数据文件（配置文件、说明文档等）
    data_files = [
        ("config.json", "."),
        ("config_example.json", "."),
        ("README.md", "."),
        ("requirements.txt", ".")
    ]

    # 包含整个tools目录
    tools_dir = "tools"
    if os.path.exists(tools_dir):
        data_files.append((tools_dir, "tools"))

    # 隐藏导入（可能被PyInstaller遗漏的模块）
    hidden_imports = [
        "tkinterdnd2",
        "tkinterdnd2.tkdnd",
        "PIL",
        "PIL.Image",
        "PIL.ImageTk",
        "requests",
        "json",
        "configparser",
        "pathlib",
        "threading",
        "queue",
        "datetime",
        "hashlib",
        "gui",  # 添加gui模块
        "file_processor",
        "api_handler",
        "compression_handler",
        "image_processor",
        "logger",
        "config",
        "tools_config",
        "utils"
    ]

    # 基础命令 - Linux版本
    cmd = [
        "pyinstaller",
        "--onefile",  # 打包成单个可执行文件
        "--name", app_name,
        "--paths", ".",  # 确保当前目录在分析路径中
        "--clean",  # 清理临时文件
        "--noconfirm",  # 覆盖输出目录而不询问
    ]

    # 添加数据文件
    for src, dst in data_files:
        if os.path.exists(src):
            # Linux下使用冒号作为分隔符
            cmd.extend(["--add-data", f"{src}:{dst}"])

    # 添加隐藏导入
    for import_name in hidden_imports:
        cmd.extend(["--hidden-import", import_name])

    # 收集第三方库的资源（以防漏收）
    cmd.extend(["--collect-all", "tkinterdnd2"])

    # 排除不需要的模块（减小文件大小）
    exclusions = [
        "matplotlib",
        "numpy",
        "scipy",
        "pandas",
        "jupyter",
        "IPython"
    ]

    for exclusion in exclusions:
        cmd.extend(["--exclude-module", exclusion])

    # 添加主脚本
    cmd.append(main_script)

    return cmd

def build_executable():
    """执行打包过程"""
    print("开始打包文件处理工具(Linux版本)...")

    # 检查PyInstaller是否安装
    try:
        subprocess.run(["pyinstaller", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("正在安装PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

    # 生成打包命令
    cmd = get_pyinstaller_command()

    print("执行打包命令:")
    print(" ".join(cmd))
    print()

    # 执行打包
    try:
        result = subprocess.run(cmd, check=True)
        print("打包成功！")
        print(f"可执行文件位于: dist/{APP_NAME}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"打包失败: {e}")
        return False

def create_flyingbull_package():
    """创建适合飞牛OS的压缩包"""
    app_name = "文件处理工具"
    fb_dir = f"{app_name}_飞牛OS版"

    if os.path.exists(fb_dir):
        shutil.rmtree(fb_dir)

    os.makedirs(fb_dir)

    # 复制可执行文件
    exe_path = f"dist/{app_name}"
    if os.path.exists(exe_path):
        shutil.copy2(exe_path, fb_dir)
        # 设置执行权限
        os.chmod(os.path.join(fb_dir, app_name), 0o755)

    # 复制必需的配置文件
    essential_files = [
        "config_example.json",
        "README.md",
        "tools/README.txt",
        "tools/下载指南.md"
    ]

    for file_path in essential_files:
        if os.path.exists(file_path):
            if os.path.isdir(file_path):
                shutil.copytree(file_path, os.path.join(fb_dir, os.path.basename(file_path)))
            else:
                os.makedirs(os.path.dirname(os.path.join(fb_dir, file_path)), exist_ok=True)
                shutil.copy2(file_path, os.path.join(fb_dir, os.path.basename(file_path)))

    # 创建启动脚本(Linux shell脚本)
    start_sh_content = f"""
#!/bin/bash
cd "$(dirname "$0")"
echo "启动{app_name}..."
./{app_name}
if [ $? -ne 0 ]; then
    echo ""
    echo "程序异常退出，请检查依赖项是否完整。"
    read -p "按Enter键继续..."
fi
"""

    with open(os.path.join(fb_dir, "启动程序.sh"), "w", encoding="utf-8") as f:
        f.write(start_sh_content)
    # 设置执行权限
    os.chmod(os.path.join(fb_dir, "启动程序.sh"), 0o755)

    print(f"飞牛OS版已创建: {fb_dir}")
    return fb_dir

if __name__ == "__main__":
    print("=" * 50)
    print("文件处理工具 - PyInstaller打包脚本(Linux版本)")
    print("专为飞牛OS优化")
    print("=" * 50)

    # 切换到脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # 执行打包
    if build_executable():
        # 创建飞牛OS版
        fb_dir = create_flyingbull_package()

        print("\n打包完成！")
        print(f"可执行文件: dist/{APP_NAME}")
        print(f"飞牛OS版目录: {fb_dir}")
        print("\n使用说明:")
        print("1. 将整个飞牛OS版目录复制到飞牛NAS上")
        print("2. 确保有执行权限: chmod +x 启动程序.sh")
        print("3. 运行 ./启动程序.sh 启动应用")
    else:
        print("\n打包失败，请检查错误信息并重试。")
        sys.exit(1)