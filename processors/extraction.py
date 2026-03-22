#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
解压处理器 - 处理压缩文件解压
"""

import os
import shutil
from typing import TYPE_CHECKING

from core.base import BaseProcessor
from core.context import ProcessingContext
from infrastructure.exceptions import ExtractionError

if TYPE_CHECKING:
    from handlers.archive_handler import ArchiveHandler


class ExtractionProcessor(BaseProcessor):
    """
    解压处理器

    负责解压各种格式的压缩文件
    """

    def __init__(self, archive_handler: 'ArchiveHandler', event_bus=None):
        super().__init__(event_bus)
        self.archive_handler = archive_handler

    @property
    def name(self) -> str:
        return "extraction"

    @property
    def description(self) -> str:
        return "解压压缩文件"

    @property
    def priority(self) -> int:
        return 10  # 最高优先级

    def can_process(self, context: ProcessingContext) -> bool:
        # 目录不需要解压
        if context.is_directory:
            return False
        return super().can_process(context)

    def should_skip(self, context: ProcessingContext) -> bool:
        return context.is_directory

    def process(self, context: ProcessingContext) -> ProcessingContext:
        """执行解压处理"""
        self.update_status(context, f"正在解压: {os.path.basename(context.source_path)}")

        # 创建临时目录
        context.temp_dir = self._create_temp_dir(context)
        extract_dir = os.path.join(context.temp_dir, "extracted")
        os.makedirs(extract_dir, exist_ok=True)

        # 获取配置
        config = context.config
        passwords = config.passwords if config else []
        timeout = config.extraction_timeout if config else 60

        # 解压文件
        success = self.archive_handler.extract_file(
            file_path=context.source_path,
            dest_dir=extract_dir,
            passwords=passwords,
            original_name=context.original_name,
            timeout=timeout
        )

        if not success:
            raise ExtractionError(
                f"解压失败: {os.path.basename(context.source_path)}"
            )

        context.extracted_dir = extract_dir
        self.update_status(context, f"解压完成: {os.path.basename(context.source_path)}")

        return context

    def _create_temp_dir(self, context: ProcessingContext) -> str:
        """创建临时目录"""
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
        return temp_dir