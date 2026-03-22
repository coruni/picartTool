#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发布处理器 - 发布文章
"""

from typing import TYPE_CHECKING, List, Dict

from core.base import BaseProcessor
from core.context import ProcessingContext
from infrastructure.exceptions import PublishError

if TYPE_CHECKING:
    from services.api_service import APIService


class PublishingProcessor(BaseProcessor):
    """
    发布处理器

    负责发布文章到服务器
    """

    def __init__(self, api_service: 'APIService', event_bus=None):
        super().__init__(event_bus)
        self.api_service = api_service

    @property
    def name(self) -> str:
        return "publishing"

    @property
    def description(self) -> str:
        return "发布文章"

    @property
    def priority(self) -> int:
        return 70  # 在上传之后

    def can_process(self, context: ProcessingContext) -> bool:
        if not super().can_process(context):
            return False
        # 需要有上传的URL
        return bool(context.uploaded_urls)

    def should_skip(self, context: ProcessingContext) -> bool:
        if not context.config:
            return True
        # 跳过登录时不上传
        if context.config.skip_login:
            return True
        # 未启用发布时跳过
        if not context.config.enable_publish:
            return True
        return False

    def process(self, context: ProcessingContext) -> ProcessingContext:
        """执行发布处理"""
        if not context.uploaded_urls:
            raise PublishError("没有上传的文件URL")

        if not context.formatted_title:
            raise PublishError("没有格式化标题")

        self.update_status(context, "正在发布文章...")

        # 发布文章
        success = self.api_service.submit_article(
            title=context.formatted_title,
            images=context.uploaded_urls,
            cover=context.uploaded_urls[0],
            publish=True,
            tag_names=context.tags
        )

        if not success:
            raise PublishError(f"文章发布失败: {context.formatted_title}")

        self.update_status(context, f"文章已发布: {context.formatted_title}")

        return context