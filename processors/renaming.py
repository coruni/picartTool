#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重命名处理器 - 重命名文件
"""

import os
import re
import shutil
from pathlib import Path
from typing import List, Set

from core.base import BaseProcessor
from core.context import ProcessingContext


class RenamingProcessor(BaseProcessor):
    """
    重命名处理器

    负责将文件重命名为统一格式
    """

    # 图片扩展名
    IMAGE_EXTENSIONS: Set[str] = {
        '.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.gif'
    }

    # 视频扩展名
    VIDEO_EXTENSIONS: Set[str] = {
        '.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.3gp', '.m4v'
    }

    def __init__(self, event_bus=None):
        super().__init__(event_bus)

    @property
    def name(self) -> str:
        return "renaming"

    @property
    def description(self) -> str:
        return "重命名文件为统一格式"

    @property
    def priority(self) -> int:
        return 30  # 在清理之后

    def process(self, context: ProcessingContext) -> ProcessingContext:
        """执行重命名处理"""
        if not context.processed_dir:
            return context

        self.update_status(context, "正在重命名文件...")

        # 获取配置
        image_prefix = "img_"
        video_prefix = "video_"
        if context.config:
            image_prefix = context.config.image_prefix or "img_"
            video_prefix = context.config.video_prefix or "video_"

        # 收集所有文件
        all_files = self._collect_files(context.processed_dir)

        # 按自然排序
        all_files.sort(key=self._natural_sort_key)

        # 重命名
        img_count = 1
        video_count = 1
        renamed_count = 0

        for file_path in all_files:
            ext = Path(file_path).suffix.lower()

            if ext in self.IMAGE_EXTENSIONS:
                new_name = f"{image_prefix}{img_count:03d}{ext}"
                img_count += 1
            elif ext in self.VIDEO_EXTENSIONS:
                new_name = f"{video_prefix}{video_count:03d}{ext}"
                video_count += 1
            else:
                continue

            # 执行重命名
            new_path = os.path.join(os.path.dirname(file_path), new_name)
            if file_path != new_path:
                try:
                    shutil.move(file_path, new_path)
                    renamed_count += 1
                except Exception:
                    pass  # 忽略单个文件重命名失败

        self.update_status(context, f"已重命名 {renamed_count} 个文件")

        return context

    def _collect_files(self, directory: str) -> List[str]:
        """收集所有文件"""
        files = []
        for root, dirs, filenames in os.walk(directory):
            for filename in filenames:
                files.append(os.path.join(root, filename))
        return files

    def _natural_sort_key(self, text: str) -> List:
        """自然排序键"""
        def tryint(s):
            try:
                return int(s)
            except:
                return s
        return [tryint(c) for c in re.split('([0-9]+)', text)]