#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理处理器 - 任务完成后清理临时文件和源文件
"""

import os
import shutil
from typing import TYPE_CHECKING

from core.base import BaseProcessor
from core.context import ProcessingContext

if TYPE_CHECKING:
    pass


class CleanupProcessor(BaseProcessor):
    """
    清理处理器

    负责在任务完成后清理临时文件和源文件
    """

    @property
    def name(self) -> str:
        return "cleanup"

    @property
    def description(self) -> str:
        return "清理临时文件"

    @property
    def priority(self) -> int:
        return 80  # 最后执行

    def can_process(self, context: ProcessingContext) -> bool:
        if not super().can_process(context):
            return False
        # 只要有临时目录或需要删除源文件就执行
        return bool(context.temp_dir) or self._should_delete_source(context)

    def should_skip(self, context: ProcessingContext) -> bool:
        # 永不跳过，总是尝试清理
        return False

    def _should_delete_source(self, context: ProcessingContext) -> bool:
        """检查是否需要删除源文件"""
        if not context.config:
            return False
        return context.config.delete_source_files

    def process(self, context: ProcessingContext) -> ProcessingContext:
        """执行清理"""
        # 1. 清理临时目录
        self._cleanup_temp_dir(context)

        # 2. 清理源文件（如果配置了）
        self._cleanup_source_file(context)

        # 3. 清理压缩后图片目录（如果配置了）
        self._cleanup_processed_dir(context)

        return context

    def _cleanup_temp_dir(self, context: ProcessingContext):
        """清理临时目录"""
        if not context.temp_dir:
            return

        try:
            if os.path.exists(context.temp_dir):
                shutil.rmtree(context.temp_dir)
                self.update_status(context, "已清理临时目录")
        except Exception as e:
            context.add_warning(self.name, f"清理临时目录失败: {e}")

    def _cleanup_source_file(self, context: ProcessingContext):
        """清理源文件"""
        if not self._should_delete_source(context):
            return

        if not context.source_path:
            return

        try:
            if os.path.isfile(context.source_path):
                os.remove(context.source_path)
                self.update_status(context, f"已删除源文件: {os.path.basename(context.source_path)}")
            elif os.path.isdir(context.source_path):
                shutil.rmtree(context.source_path)
                self.update_status(context, f"已删除源目录: {os.path.basename(context.source_path)}")
        except Exception as e:
            context.add_warning(self.name, f"删除源文件失败: {e}")

    def _cleanup_processed_dir(self, context: ProcessingContext):
        """清理处理后的目录"""
        if not context.config:
            return

        # 如果配置了删除压缩后的图片
        if not context.config.delete_compressed_images:
            return

        # 清理解压后的目录
        if context.extracted_dir and os.path.exists(context.extracted_dir):
            try:
                shutil.rmtree(context.extracted_dir)
                self.update_status(context, "已清理解压目录")
            except Exception as e:
                context.add_warning(self.name, f"清理解压目录失败: {e}")

        # 清理处理后的目录
        if context.processed_dir and os.path.exists(context.processed_dir):
            try:
                shutil.rmtree(context.processed_dir)
                self.update_status(context, "已清理处理目录")
            except Exception as e:
                context.add_warning(self.name, f"清理处理目录失败: {e}")