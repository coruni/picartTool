#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上传处理器 - 上传文件到服务器
"""

import os
from typing import TYPE_CHECKING

from core.base import BaseProcessor, SkipProcessor
from core.context import ProcessingContext
from infrastructure.exceptions import UploadError

if TYPE_CHECKING:
    from services.api_service import APIService
    from services.image_host_service import ImageHostService
    from services.imgur_service import ImgurService


class UploadingProcessor(BaseProcessor):
    """
    上传处理器

    负责将文件上传到服务器或图床
    """

    def __init__(self, api_service: 'APIService', event_bus=None,
                 image_host_service: 'ImageHostService' = None,
                 imgur_service: 'ImgurService' = None):
        super().__init__(event_bus)
        self.api_service = api_service
        self.image_host_service = image_host_service
        self.imgur_service = imgur_service

    @property
    def name(self) -> str:
        return "uploading"

    @property
    def description(self) -> str:
        return "上传文件到服务器"

    @property
    def priority(self) -> int:
        return 60  # 在图片压缩之后

    def can_process(self, context: ProcessingContext) -> bool:
        if not super().can_process(context):
            return False
        # 检查是否有可用的上传服务
        has_api = self.api_service is not None
        has_image_host = self.image_host_service is not None and self.image_host_service.is_enabled()
        has_imgur = self.imgur_service is not None and self.imgur_service.is_enabled()
        return has_api or has_image_host or has_imgur

    def should_skip(self, context: ProcessingContext) -> bool:
        if not context.config:
            return True
        # 跳过登录时不上传
        if context.config.skip_login:
            return True
        # 未启用上传时跳过
        if not context.config.enable_upload:
            return True
        return False

    def process(self, context: ProcessingContext) -> ProcessingContext:
        """执行上传处理"""
        if not context.processed_dir:
            raise UploadError("没有找到要上传的目录")

        self.update_status(context, "正在上传文件...")

        # 根据配置选择上传方式
        upload_method = context.config.upload_method if context.config else "api"

        if upload_method == "imgur" and self.imgur_service and self.imgur_service.is_enabled():
            self.update_status(context, "[Uploading] 使用 Imgur 上传...")
            uploaded_urls = self._upload_to_imgur(context)
        elif upload_method == "image_host" and self.image_host_service and self.image_host_service.is_enabled():
            self.update_status(context, "[Uploading] 使用图床上传...")
            uploaded_urls = self._upload_to_image_host(context)
        else:
            # 默认使用原有API上传
            self.update_status(context, "[Uploading] 使用API上传...")
            uploaded_urls = self._upload_to_api(context)

        if not uploaded_urls:
            raise UploadError("上传失败，没有获取到URL")

        context.uploaded_urls = uploaded_urls
        self.update_status(context, f"[Uploading] 已上传 {len(uploaded_urls)} 个文件")

        return context

    def _upload_to_image_host(self, context: ProcessingContext) -> list:
        """使用图床上传"""
        # 上传所有压缩后的图片
        urls = self.image_host_service.upload_files(
            context.processed_dir,
            extensions=['.webp', '.jpg', '.jpeg', '.png', '.gif']
        )
        return urls

    def _upload_to_imgur(self, context: ProcessingContext) -> list:
        """使用 Imgur 上传"""
        # Imgur 支持 jpg, png, gif
        urls = self.imgur_service.upload_files(
            context.processed_dir,
            extensions=['.jpg', '.jpeg', '.png', '.gif']
        )
        return urls

    def _upload_to_api(self, context: ProcessingContext) -> list:
        """使用原有API上传"""
        # 确保登录
        if not self.api_service.ensure_login():
            raise UploadError("登录失败，无法上传")

        # 上传文件
        uploaded_urls = self.api_service.upload_files(context.processed_dir)
        return uploaded_urls