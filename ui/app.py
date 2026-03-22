#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用程序主类 - 负责初始化和协调MVC组件
"""

import os
import tkinter as tk
from tkinter import ttk

from infrastructure.config import Config
from infrastructure.logger import Logger

# 拖拽支持
try:
    from tkinterdnd2 import TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False


class Application:
    """
    应用程序主类

    负责初始化MVC组件并协调它们之间的交互
    """

    def __init__(self, config: Config, logger: Logger):
        self.config = config
        self.logger = logger

        # 创建主窗口（支持拖拽）
        if HAS_DND:
            self.root = TkinterDnD.Tk()
        else:
            self.root = tk.Tk()
            self.logger.warning("tkinterdnd2未安装，拖拽功能不可用")

        self.root.title("文件处理工具 v2.0 - 模块化架构")
        self.root.geometry("900x700")

        # 设置样式
        self._setup_styles()

        # 初始化MVC组件
        self._init_mvc()

        # 设置关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_styles(self):
        """设置样式"""
        style = ttk.Style()
        style.configure('TButton', padding=6, relief='flat')
        style.configure('TFrame', background='#f0f0f0')
        style.configure('TLabel', background='#f0f0f0')

    def _init_mvc(self):
        """初始化MVC组件"""
        # 延迟导入避免循环依赖
        from .main_view import MainView
        from .main_controller import MainController

        # 创建视图
        self.view = MainView(self.root, self.config)

        # 创建控制器
        self.controller = MainController(
            config=self.config,
            logger=self.logger,
            view=self.view
        )

        # 连接视图和控制器
        self.view.set_controller(self.controller)

    def run(self):
        """运行应用程序"""
        self.logger.info("应用程序启动")
        self.root.mainloop()

    def _on_close(self):
        """关闭事件处理"""
        self.logger.info("应用程序关闭")
        self.root.destroy()


def create_application(config: Config = None, logger: Logger = None) -> Application:
    """
    创建应用程序实例

    Args:
        config: 配置对象
        logger: 日志记录器

    Returns:
        Application实例
    """
    if config is None:
        from infrastructure.config import ConfigManager
        config = ConfigManager().load_config()

    if logger is None:
        from infrastructure.logger import LogManager
        logger = LogManager.get_logger()

    return Application(config, logger)