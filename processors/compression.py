#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片压缩处理器 - 压缩图片
"""

import os
from typing import TYPE_CHECKING

from core.base import BaseProcessor
from core.context import ProcessingContext

if TYPE_CHECKING:
    from handlers.image_handler import ImageHandler


class ImageCompressionProcessor(BaseProcessor):
    """
    图片压缩处理器

    负责压缩目录中的图片
    """

    def __init__(self, image_handler: 'ImageHandler', event_bus=None):
        super().__init__(event_bus)
        self.image_handler = image_handler

    @property
    def name(self) -> str:
        return "image_compression"

    @property
    def description(self) -> str:
        return "压缩图片"

    @property
    def priority(self) -> int:
        return 50  # 在打包之后

    def should_skip(self, context: ProcessingContext) -> bool:
        """检查是否应该跳过图片压缩"""
        if not context.config:
            self.update_status(context, "未找到配置，跳过图片压缩")
            return False

        # 打印配置状态用于调试
        self.update_status(context, f"enable_compression = {context.config.enable_compression}")

        # 如果未启用压缩，跳过
        if not context.config.enable_compression:
            self.update_status(context, "图片压缩已禁用，跳过")
            return True
        return False

    def process(self, context: ProcessingContext) -> ProcessingContext:
        """执行图片压缩处理"""
        self.update_status(context, f"开始图片压缩处理，processed_dir={context.processed_dir}")

        if not context.processed_dir:
            self.update_status(context, "没有 processed_dir，跳过图片压缩")
            return context

        # 列出目录内容
        import os
        try:
            files = os.listdir(context.processed_dir)
            self.update_status(context, f"目录内容: {files[:10]}...")
        except Exception as e:
            self.update_status(context, f"无法列出目录: {e}")
            return context

        self.update_status(context, "正在压缩图片...")

        # 从配置获取压缩参数
        config = context.config
        max_width = config.max_width if config else 1080
        max_height = config.max_height if config else 1920
        quality = config.quality if config else 80
        output_format = config.image_format if config else "webp"
        lossless = config.lossless_compression if config else False
        timeout = config.api_timeout if config else 120
        max_upload_size_mb = config.max_upload_size_mb if config else 10

        # 如果上传方式为 imgur，强制使用 jpg 格式
        upload_method = config.upload_method if config else "api"
        if upload_method == "imgur":
            if output_format != "jpg":
                self.update_status(context, f"[ImageCompression] 上传方式为 Imgur，强制使用 jpg 格式（原格式: {output_format}）")
                output_format = "jpg"

        # 检查并记录压缩前的大小
        total_size_before = self._calculate_total_size(context.processed_dir)
        self.update_status(context, f"压缩前总大小: {total_size_before / (1024*1024):.2f} MB")

        # 执行压缩
        compressed, failed, oversized = self.image_handler.compress_images(
            directory=context.processed_dir,
            max_width=max_width,
            max_height=max_height,
            quality=quality,
            output_format=output_format,
            lossless=lossless,
            timeout=timeout,
            max_size_mb=max_upload_size_mb
        )

        # 检查压缩后的大小
        total_size_after = self._calculate_total_size(context.processed_dir)
        saved_mb = (total_size_before - total_size_after) / (1024*1024)

        if compressed > 0:
            self.update_status(context, f"已压缩 {compressed} 张图片，节省 {saved_mb:.2f} MB")
        if oversized > 0:
            context.add_warning(self.name, f"{oversized} 张图片压缩后仍超过 {max_upload_size_mb}MB")
        if failed > 0:
            context.add_warning(self.name, f"{failed} 张图片压缩失败")

        return context

    def _calculate_total_size(self, directory: str) -> int:
        """计算目录中所有图片的总大小"""
        total_size = 0
        image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.gif'}
        for root, dirs, files in os.walk(directory):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in image_extensions:
                    file_path = os.path.join(root, file)
                    try:
                        total_size += os.path.getsize(file_path)
                    except Exception:
                        pass
        return total_size