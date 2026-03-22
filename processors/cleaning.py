#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理处理器 - 清理不需要的文件
"""

import os
from pathlib import Path
from typing import Set

from core.base import BaseProcessor
from core.context import ProcessingContext


class CleaningProcessor(BaseProcessor):
    """
    清理处理器

    负责清理不需要的文件和目录
    """

    # 不需要的文件扩展名
    UNWANTED_EXTENSIONS: Set[str] = {
        '.html', '.htm', '.txt', '.url', '.lnk', '.nfo', '.diz'
    }

    # 不需要的文件名
    UNWANTED_NAMES: Set[str] = {
        'ewm', 'thumbs.db', '.ds_store'
    }

    def __init__(self, event_bus=None):
        super().__init__(event_bus)

    @property
    def name(self) -> str:
        return "cleaning"

    @property
    def description(self) -> str:
        return "清理不需要的文件"

    @property
    def priority(self) -> int:
        return 20  # 在解压之后

    def process(self, context: ProcessingContext) -> ProcessingContext:
        """执行清理处理"""
        # 确定要清理的目录
        target_dir = context.extracted_dir or context.source_path

        if context.is_directory:
            # 对于目录，先复制到临时目录
            target_dir = self._copy_to_temp(context)

        self.update_status(context, "正在清理不需要的文件...")

        cleaned_count = self._clean_unwanted_files(target_dir)

        context.processed_dir = target_dir

        if cleaned_count > 0:
            self.update_status(context, f"已清理 {cleaned_count} 个不需要的文件")

        return context

    def _copy_to_temp(self, context: ProcessingContext) -> str:
        """将目录复制到临时目录"""
        import shutil
        import time

        # 获取临时目录基础路径
        if context.config and context.config.temp_dir:
            temp_base = context.config.temp_dir
        elif context.config and context.config.output_dir:
            temp_base = os.path.join(context.config.output_dir, "temp")
        else:
            temp_base = "temp"

        # 确保基础目录存在
        os.makedirs(temp_base, exist_ok=True)

        temp_dir = os.path.join(
            temp_base,
            f"process_{int(time.time())}_{os.getpid()}"
        )
        os.makedirs(temp_dir, exist_ok=True)
        context.temp_dir = temp_dir

        # 清理文件名
        from infrastructure.utils import FileNameCleaner
        clean_name = FileNameCleaner.clean_filename(context.original_name)

        # 复制目录
        processed_dir = os.path.join(temp_dir, clean_name)
        shutil.copytree(context.source_path, processed_dir)

        context.clean_name = clean_name
        return processed_dir

    def _clean_unwanted_files(self, directory: str) -> int:
        """清理不需要的文件"""
        cleaned_count = 0

        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)

                if self._is_unwanted_file(file):
                    try:
                        os.remove(file_path)
                        cleaned_count += 1
                    except Exception as e:
                        pass  # 忽略单个文件删除失败

        return cleaned_count

    def _is_unwanted_file(self, filename: str) -> bool:
        """判断是否为不需要的文件"""
        ext = Path(filename).suffix.lower()
        name_lower = filename.lower()

        # 检查扩展名
        if ext in self.UNWANTED_EXTENSIONS:
            return True

        # 检查文件名
        if name_lower in self.UNWANTED_NAMES:
            return True

        # 检查以ewm开头的文件
        if name_lower.startswith('ewm'):
            return True

        return False