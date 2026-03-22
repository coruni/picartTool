#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标题格式化处理器 - 格式化标题并生成标签
"""

import os
import re
from pathlib import Path
from typing import TYPE_CHECKING

from core.base import BaseProcessor
from core.context import ProcessingContext, FileStats, AIResult

if TYPE_CHECKING:
    from services.ai_service import AIService


class TitleFormattingProcessor(BaseProcessor):
    """
    标题格式化处理器

    负责格式化标题、统计文件信息、生成标签
    """

    def __init__(self, ai_service: 'AIService' = None, event_bus=None):
        super().__init__(event_bus)
        self.ai_service = ai_service

    @property
    def name(self) -> str:
        return "title_formatting"

    @property
    def description(self) -> str:
        return "格式化标题并生成标签"

    @property
    def priority(self) -> int:
        return 35  # 在重命名之后，打包之前

    def process(self, context: ProcessingContext) -> ProcessingContext:
        """执行标题格式化处理"""
        if not context.processed_dir:
            return context

        self.update_status(context, "正在统计文件信息...")

        # 统计文件信息
        context.stats = self._calculate_stats(context.processed_dir)

        # 获取基础标题
        from infrastructure.utils import FileNameCleaner
        if not context.clean_name:
            context.clean_name = FileNameCleaner.clean_filename(context.original_name)

        # 尝试AI生成标题
        if self.ai_service and self.ai_service.is_enabled():
            self.update_status(context, "正在使用AI生成标题...")
            ai_result = self.ai_service.generate_title(
                original_filename=context.original_name,
                image_count=context.stats.image_count,
                video_count=context.stats.video_count,
                total_mb=context.stats.total_size_mb
            )

            if ai_result:
                context.ai_result = AIResult(
                    coser_name=ai_result.get('coser_name'),
                    work_name=ai_result.get('work_name')
                )

                # 格式化标题
                context.formatted_title = self.ai_service.format_ai_title(
                    ai_result['coser_name'],
                    ai_result['work_name'],
                    context.stats.image_count,
                    context.stats.video_count,
                    context.stats.total_size_mb
                )

                # 生成标签
                context.tags = self.ai_service.generate_tags(
                    ai_result['coser_name'],
                    ai_result['work_name'],
                    context.original_name
                )

        # 如果没有AI结果，使用默认格式
        if not context.formatted_title:
            context.formatted_title = self._format_default_title(
                context.clean_name,
                context.stats
            )

        self.update_status(context, f"标题: {context.formatted_title}")

        return context

    def _calculate_stats(self, directory: str) -> FileStats:
        """计算文件统计信息"""
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'}
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.3gp', '.m4v'}

        stats = FileStats()

        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.exists(file_path):
                    ext = Path(file).suffix.lower()
                    file_size = os.path.getsize(file_path)
                    stats.total_size_bytes += file_size

                    if ext in image_extensions:
                        stats.image_count += 1
                    elif ext in video_extensions:
                        stats.video_count += 1

        return stats

    def _format_default_title(self, base_name: str, stats: FileStats) -> str:
        """格式化默认标题"""
        if stats.video_count > 0:
            stats_str = f"[{stats.image_count}P+{stats.video_count}V - {stats.total_size_mb}MB]"
        else:
            stats_str = f"[{stats.image_count}P - {stats.total_size_mb}MB]"

        return f"{base_name} {stats_str}"