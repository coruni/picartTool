#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打包处理器 - 创建压缩包
"""

import os
from typing import TYPE_CHECKING

from core.base import BaseProcessor
from core.context import ProcessingContext
from infrastructure.exceptions import CompressionError
from infrastructure.utils import FileNameCleaner

if TYPE_CHECKING:
    from handlers.archive_handler import ArchiveHandler


class ArchivingProcessor(BaseProcessor):
    """
    打包处理器

    负责创建最终压缩包
    """

    def __init__(self, archive_handler: 'ArchiveHandler', event_bus=None):
        super().__init__(event_bus)
        self.archive_handler = archive_handler

    @property
    def name(self) -> str:
        return "archiving"

    @property
    def description(self) -> str:
        return "创建压缩包"

    @property
    def priority(self) -> int:
        return 40  # 在标题格式化之后

    @property
    def required_config(self) -> list:
        return ['output_dir']

    def process(self, context: ProcessingContext) -> ProcessingContext:
        """执行打包处理"""
        if not context.processed_dir:
            raise CompressionError("没有找到要打包的目录")

        # 获取配置
        config = context.config
        if not config:
            raise CompressionError("缺少配置")

        # 生成输出文件名
        safe_title = FileNameCleaner.make_safe_filename(context.formatted_title or context.clean_name)

        # 根据格式确定扩展名
        zip_format = config.zip_format.lower()
        if zip_format == 'zst':
            extension = ".7z.zst"
        else:
            extension = f".{zip_format}"

        output_file = os.path.join(config.output_dir, f"{safe_title}{extension}")
        os.makedirs(config.output_dir, exist_ok=True)

        self.update_status(context, f"正在创建压缩包: {os.path.basename(output_file)}")

        # 创建压缩包
        success = self.archive_handler.create_archive(
            source_dir=context.processed_dir,
            output_file=output_file,
            password=config.zip_password,
            format_type=config.zip_format,
            compression_level=config.zip_compression_level,
            solid_mode=config.zip_solid_mode,
            dictionary_size=config.zip_dictionary_size,
            zstd_level=config.zstd_compression_level,
            zstd_long_distance=config.zstd_long_distance_mode,
            zstd_ldm_distance=config.zstd_ldm_distance,
            zstd_strategy=config.zstd_strategy,
            zstd_window_log=config.zstd_window_log
        )

        if not success:
            raise CompressionError(f"创建压缩包失败: {output_file}")

        context.output_archive = output_file
        self.update_status(context, f"压缩包已创建: {os.path.basename(output_file)}")

        return context