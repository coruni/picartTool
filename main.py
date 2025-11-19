#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件处理工具 - 主程序入口
Windows兼容的GUI文件处理应用
"""

import os
import sys
import tkinter as tk
from tkinter import messagebox

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui import FileProcessorGUI


def check_dependencies():
    """检查依赖项"""
    missing_deps = []

    # 检查必需的包
    try:
        import requests
    except ImportError:
        missing_deps.append("requests")

    try:
        import tkinterdnd2
    except ImportError:
        missing_deps.append("tkinterdnd2")

    # 检查系统工具（使用tools_config）
    try:
        from tools_config import ToolsConfig
        tools_config = ToolsConfig()
        status = tools_config.get_tool_status()

        if not status['7zip']['found']:
            missing_deps.append("7-Zip (未找到)")

        if not status['ffmpeg']['found']:
            missing_deps.append("FFmpeg (未找到)")

    except Exception as e:
        missing_deps.append(f"工具检测失败: {e}")

    return missing_deps


def install_dependencies():
    """显示依赖安装说明"""
    # 检测操作系统类型
    is_windows = os.name == 'nt'
    is_linux = os.name == 'posix'
    
    # 根据不同操作系统显示不同的安装说明
    if is_windows:
        instructions = """
缺少必需的依赖项，请按以下方式安装：

1. 安装Python包（在命令行运行）：
   pip install requests tkinterdnd2

2. 安装系统工具：
   - 7-Zip: 从 https://www.7-zip.org/ 下载并安装
   - FFmpeg: 从 https://ffmpeg.org/download.html 下载并安装

3. 或者直接复制工具文件到项目目录：
   - 7z.exe: 复制到 tools/7z/ 或 tools/ 目录
   - ffmpeg.exe: 复制到 tools/ffmpeg/bin/ 或 tools/ 目录

4. 确保FFmpeg和7-Zip在系统PATH中（如果选择系统安装）

安装完成后请重新启动程序。
"""
    elif is_linux:
        instructions = """
缺少必需的依赖项，请按以下方式安装：

1. 安装Python包（在命令行运行）：
   pip install requests tkinterdnd2

2. 安装系统工具（Linux命令）：
   - 7-Zip: sudo apt-get install p7zip-full 或 sudo yum install p7zip
   - FFmpeg: sudo apt-get install ffmpeg 或 sudo yum install ffmpeg

3. 或者直接复制工具文件到项目目录：
   - 7z: 复制到 tools/7z/ 或 tools/ 目录
   - ffmpeg: 复制到 tools/ffmpeg/bin/ 或 tools/ 目录

4. 确保FFmpeg和7-Zip在系统PATH中（如果选择系统安装）

安装完成后请重新启动程序。
"""
    else:
        # 默认说明
        instructions = """
缺少必需的依赖项，请按以下方式安装：

1. 安装Python包（在命令行运行）：
   pip install requests tkinterdnd2

2. 安装系统工具：
   - 7-Zip: 从 https://www.7-zip.org/ 下载并安装
   - FFmpeg: 从 https://ffmpeg.org/download.html 下载并安装

3. 确保工具在系统PATH中

安装完成后请重新启动程序。
"""

    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("缺少依赖项", instructions)
    root.destroy()


def main():
    """主函数"""
    try:
        # 检查依赖
        missing_deps = check_dependencies()
        if missing_deps:
            print(f"缺少依赖: {', '.join(missing_deps)}")
            install_dependencies()
            return

        # 启动GUI
        app = FileProcessorGUI()
        app.run()

    except Exception as e:
        error_msg = f"启动应用失败: {e}"
        print(error_msg)

        # 尝试显示错误对话框
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("错误", error_msg)
            root.destroy()
        except:
            pass


if __name__ == "__main__":
    main()