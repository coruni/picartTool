#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新版入口文件 - 使用模块化架构
"""

import os
import sys

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def check_dependencies():
    """检查依赖项"""
    missing_deps = []

    # 检查Python包
    try:
        import requests
    except ImportError:
        missing_deps.append("requests")

    try:
        import tkinterdnd2
    except ImportError:
        missing_deps.append("tkinterdnd2")

    # 检查外部工具
    try:
        from handlers.tool_locator import ToolLocator
        locator = ToolLocator()

        if not locator.find_7zip():
            missing_deps.append("7-Zip (未找到)")

        if not locator.find_ffmpeg():
            missing_deps.append("FFmpeg (未找到)")

    except Exception as e:
        missing_deps.append(f"工具检测失败: {e}")

    return missing_deps


def show_dependency_error(missing_deps: list):
    """显示依赖错误"""
    import tkinter as tk
    from tkinter import messagebox

    instructions = """
缺少必需的依赖项，请按以下方式安装：

1. 安装Python包：
   pip install requests tkinterdnd2

2. 安装系统工具：
   - 7-Zip: 从 https://www.7-zip.org/ 下载
   - FFmpeg: 从 https://ffmpeg.org/download.html 下载

3. 或将工具文件复制到项目的 tools 目录

安装完成后请重新启动程序。
"""

    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("缺少依赖项", instructions)
    root.destroy()


def main():
    """主函数"""
    import tkinter as tk
    from tkinter import messagebox

    try:
        # 检查依赖
        missing = check_dependencies()
        if missing:
            show_dependency_error(missing)
            return

        # 导入配置
        from infrastructure.config import ConfigManager
        from infrastructure.logger import LogManager

        # 加载配置
        config_manager = ConfigManager()
        config = config_manager.load_config()

        # 设置日志
        log_dir = config.log_dir or os.path.join(config.output_dir, "logs") if config.output_dir else "logs"
        logger = LogManager.get_logger(log_dir=log_dir)

        # 导入GUI
        from ui.app import Application

        # 启动应用
        app = Application(config, logger)
        app.run()

    except Exception as e:
        error_msg = f"启动应用失败: {e}"
        print(error_msg)

        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("错误", error_msg)
            root.destroy()
        except:
            pass


if __name__ == "__main__":
    main()