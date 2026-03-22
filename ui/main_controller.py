#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主控制器 - 负责协调视图和业务逻辑
"""

import os
import threading
from typing import List, Optional, TYPE_CHECKING

from infrastructure.config import Config
from infrastructure.logger import Logger
from core.events import Events

if TYPE_CHECKING:
    from .main_view import MainView


class MainController:
    """
    主控制器

    负责协调视图和业务逻辑，处理用户操作
    """

    def __init__(self, config: Config, logger: Logger, view: 'MainView'):
        self.config = config
        self.logger = logger
        self.view = view

        # 状态
        self.files: List[str] = []
        self.is_processing = False
        self.should_stop = False

        # 处理器
        self._file_processor = None

    def add_files(self, files: List[str]):
        """添加文件到列表"""
        for file in files:
            if file not in self.files:
                self.files.append(file)

        self._update_file_list()
        self.logger.info(f"添加了 {len(files)} 个文件")

    def remove_files(self, indices: tuple):
        """移除文件"""
        # 从后往前删除，避免索引变化
        for i in sorted(indices, reverse=True):
            if 0 <= i < len(self.files):
                self.files.pop(i)

        self._update_file_list()

    def clear_files(self):
        """清空文件列表"""
        self.files.clear()
        self._update_file_list()
        self.logger.info("文件列表已清空")

    def start_processing(self):
        """开始处理"""
        if self.is_processing:
            self.view.show_message("提示", "正在处理中，请等待完成")
            return

        if not self.files:
            self.view.show_message("提示", "请先添加要处理的文件")
            return

        self.is_processing = True
        self.should_stop = False
        self.view.set_processing(True)
        self.view.clear_log()

        # 在后台线程中处理
        thread = threading.Thread(target=self._process_files, daemon=True)
        thread.start()

    def stop_processing(self):
        """停止处理"""
        self.should_stop = True
        self.logger.info("正在停止处理...")

    def open_settings(self):
        """打开设置窗口"""
        from .settings_view import SettingsView

        settings_view = SettingsView(self.view.parent, self.config)
        settings_view.on_save = self._on_settings_saved
        settings_view.show()

    def _on_settings_saved(self, config: Config):
        """设置保存回调"""
        from infrastructure.config import ConfigManager
        self.config = config
        # 保存配置到文件
        ConfigManager().save_config_with_config(config)
        self.logger.info("设置已保存")

    def open_output_dir(self):
        """打开输出目录"""
        output_dir = self.config.output_dir
        self.logger.info(f"尝试打开输出目录: {output_dir}")

        if not output_dir:
            self.view.show_message("提示", "输出目录未设置", "warning")
            return

        if not os.path.exists(output_dir):
            self.view.show_message("提示", f"输出目录不存在: {output_dir}", "warning")
            return

        try:
            import subprocess
            # 使用绝对路径
            abs_path = os.path.abspath(output_dir)
            self.logger.info(f"打开目录: {abs_path}")

            if os.name == 'nt':
                # Windows 使用 explorer
                subprocess.run(['explorer', abs_path], check=False)
            else:
                # Linux/Mac
                subprocess.run(['xdg-open', abs_path], check=False)
        except Exception as e:
            self.logger.error(f"打开目录失败: {e}")
            self.view.show_message("错误", f"打开目录失败: {e}")

    def _process_files(self):
        """处理文件（后台线程）"""
        from pipeline_factory import FileProcessorFacade

        try:
            # 创建处理器
            processor = FileProcessorFacade(self.config, self.logger)

            # 添加事件监听
            processor.add_event_listener(Events.STATUS_UPDATE, self._on_status_update)
            processor.add_event_listener(Events.PROCESSOR_START, self._on_processor_start)
            processor.add_event_listener(Events.PROCESSOR_COMPLETE, self._on_processor_complete)
            processor.add_event_listener(Events.PROCESSOR_ERROR, self._on_processor_error)

            total = len(self.files)

            for i, file_path in enumerate(self.files, 1):
                if self.should_stop:
                    self._update_status(f"处理已停止")
                    break

                self._update_status(f"处理中 ({i}/{total}): {os.path.basename(file_path)}")

                try:
                    result = processor.process(
                        file_path,
                        status_callback=self._update_status
                    )

                    if result.get('errors'):
                        self._log(f"处理完成但有错误: {result['errors']}")
                    else:
                        self._log(f"处理成功: {os.path.basename(file_path)}")

                except Exception as e:
                    self._log(f"处理失败: {e}")

            self._update_status("处理完成")

        except Exception as e:
            self.logger.exception(f"处理过程出错: {e}")
            self._log(f"处理过程出错: {e}")

        finally:
            self.is_processing = False
            self._run_on_main_thread(lambda: self.view.set_processing(False))

    def _update_file_list(self):
        """更新文件列表视图"""
        self._run_on_main_thread(lambda: self.view.update_file_list(self.files))

    def _update_status(self, message: str):
        """更新状态"""
        self._run_on_main_thread(lambda: self.view.update_status(message))

    def _log(self, message: str):
        """记录日志"""
        self.logger.info(message)
        self._run_on_main_thread(lambda: self.view.append_log(message))

    def _on_status_update(self, message: str):
        """状态更新事件"""
        self._update_status(message)
        self._log(message)

    def _on_processor_start(self, name: str):
        """处理器开始事件"""
        pass  # 由 update_status 处理

    def _on_processor_complete(self, name: str):
        """处理器完成事件"""
        pass  # 由 update_status 处理

    def _on_processor_error(self, name: str, error: str):
        """处理器错误事件"""
        self._log(f"[{name}] 错误: {error}")

    def _run_on_main_thread(self, callback):
        """在主线程中执行回调"""
        # 使用after确保在主线程执行
        self.view.parent.after(0, callback)