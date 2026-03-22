#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
处理管道工厂

创建和配置处理管道
"""

from typing import Optional, Callable

from core.pipeline import Pipeline, PipelineBuilder
from core.events import EventBus, Events
from infrastructure.config import Config
from infrastructure.logger import Logger


class PipelineFactory:
    """
    处理管道工厂

    负责创建和配置处理管道
    """

    @staticmethod
    def create_standard_pipeline(
        config: Config,
        logger: Logger,
        event_bus: EventBus = None,
        status_callback: Callable[[str], None] = None
    ) -> Pipeline:
        """
        创建标准处理管道

        包含完整的处理流程：解压 → 清理 → 重命名 → 标题格式化 → 打包 → 图片压缩 → 上传 → 发布

        Args:
            config: 配置对象
            logger: 日志记录器
            event_bus: 事件总线
            status_callback: 状态回调函数

        Returns:
            配置好的处理管道
        """
        from handlers.archive_handler import ArchiveHandler
        from handlers.image_handler import ImageHandler
        from handlers.tool_locator import ToolLocator

        from services.api_service import APIService
        from services.ai_service import AIService
        from services.image_host_service import ImageHostService
        from services.imgur_service import ImgurService

        from processors.extraction import ExtractionProcessor
        from processors.cleaning import CleaningProcessor
        from processors.renaming import RenamingProcessor
        from processors.title_formatting import TitleFormattingProcessor
        from processors.archiving import ArchivingProcessor
        from processors.compression import ImageCompressionProcessor
        from processors.uploading import UploadingProcessor
        from processors.publishing import PublishingProcessor
        from processors.cleanup import CleanupProcessor

        # 创建事件总线
        event_bus = event_bus or EventBus()

        # 创建工具定位器
        tool_locator = ToolLocator()

        # 创建处理器
        archive_handler = ArchiveHandler(tool_locator, logger)
        image_handler = ImageHandler(tool_locator, logger)

        # 创建服务
        api_service = APIService(config, logger)
        ai_service = AIService(config, logger)
        image_host_service = ImageHostService(config, logger)
        imgur_service = ImgurService(config, logger)

        # 构建管道
        builder = PipelineBuilder(event_bus)

        # 添加处理器（按优先级顺序）
        builder.add(ExtractionProcessor(archive_handler, event_bus))
        builder.add(CleaningProcessor(event_bus))
        builder.add(RenamingProcessor(event_bus))
        builder.add(TitleFormattingProcessor(ai_service, event_bus))
        builder.add(ArchivingProcessor(archive_handler, event_bus))
        builder.add(ImageCompressionProcessor(image_handler, event_bus))
        builder.add(UploadingProcessor(api_service, event_bus, image_host_service, imgur_service))
        builder.add(PublishingProcessor(api_service, event_bus))
        builder.add(CleanupProcessor(event_bus))

        return builder.build()

    @staticmethod
    def create_minimal_pipeline(
        config: Config,
        logger: Logger,
        event_bus: EventBus = None
    ) -> Pipeline:
        """
        创建最小处理管道

        只包含基本处理：解压 → 清理 → 重命名 → 打包

        Args:
            config: 配置对象
            logger: 日志记录器
            event_bus: 事件总线

        Returns:
            配置好的处理管道
        """
        from handlers.archive_handler import ArchiveHandler
        from handlers.tool_locator import ToolLocator

        from processors.extraction import ExtractionProcessor
        from processors.cleaning import CleaningProcessor
        from processors.renaming import RenamingProcessor
        from processors.title_formatting import TitleFormattingProcessor
        from processors.archiving import ArchivingProcessor
        from processors.cleanup import CleanupProcessor

        event_bus = event_bus or EventBus()
        tool_locator = ToolLocator()
        archive_handler = ArchiveHandler(tool_locator, logger)

        # 模拟AI服务（使用默认格式）
        class MockAIService:
            def is_enabled(self):
                return False

        builder = PipelineBuilder(event_bus)
        builder.add(ExtractionProcessor(archive_handler, event_bus))
        builder.add(CleaningProcessor(event_bus))
        builder.add(RenamingProcessor(event_bus))
        builder.add(TitleFormattingProcessor(MockAIService(), event_bus))
        builder.add(ArchivingProcessor(archive_handler, event_bus))
        builder.add(CleanupProcessor(event_bus))

        return builder.build()

    @staticmethod
    def create_custom_pipeline(
        processors: list,
        event_bus: EventBus = None
    ) -> Pipeline:
        """
        创建自定义处理管道

        Args:
            processors: 处理器列表
            event_bus: 事件总线

        Returns:
            配置好的处理管道
        """
        event_bus = event_bus or EventBus()
        builder = PipelineBuilder(event_bus)

        for processor in processors:
            builder.add(processor)

        return builder.sort_by_priority().build()


class FileProcessorFacade:
    """
    文件处理器门面

    提供简化的处理接口
    """

    def __init__(self, config: Config, logger: Logger = None):
        self.config = config
        self.logger = logger or Logger(config.log_dir or "logs")
        self.event_bus = EventBus()
        self.pipeline = PipelineFactory.create_standard_pipeline(
            config, self.logger, self.event_bus
        )

        # 设置事件监听
        self._setup_event_listeners()

    def _setup_event_listeners(self):
        """设置事件监听"""
        self.event_bus.on(Events.PROCESSOR_START, self._on_processor_start)
        self.event_bus.on(Events.PROCESSOR_COMPLETE, self._on_processor_complete)
        self.event_bus.on(Events.PROCESSOR_ERROR, self._on_processor_error)
        self.event_bus.on(Events.STATUS_UPDATE, self._on_status_update)

    def _on_processor_start(self, name: str):
        """处理器开始事件"""
        pass  # 由 update_status 处理

    def _on_processor_complete(self, name: str):
        """处理器完成事件"""
        pass  # 由 update_status 处理

    def _on_processor_error(self, name: str, error: str):
        """处理器错误事件"""
        self.logger.error(f"[{name}] 错误: {error}")

    def _on_status_update(self, message: str):
        """状态更新事件"""
        self.logger.info(message)

    def process(self, file_path: str, status_callback: Callable = None) -> dict:
        """
        处理文件

        Args:
            file_path: 文件路径
            status_callback: 状态回调函数

        Returns:
            处理结果字典
        """
        from core.context import ProcessingContext

        # 创建上下文
        context = ProcessingContext.create(
            source_path=file_path,
            config=self.config,
            status_callback=status_callback
        )

        # 执行管道
        context = self.pipeline.execute(context)

        return context.to_dict()

    def process_async(self, file_path: str,
                      callback: Callable[[dict], None] = None,
                      status_callback: Callable[[str], None] = None):
        """
        异步处理文件

        Args:
            file_path: 文件路径
            callback: 完成回调
            status_callback: 状态回调
        """
        from core.context import ProcessingContext

        def run():
            context = ProcessingContext.create(
                source_path=file_path,
                config=self.config,
                status_callback=status_callback
            )

            context = self.pipeline.execute(context)

            if callback:
                callback(context.to_dict())

        import threading
        thread = threading.Thread(target=run, daemon=True)
        thread.start()

    def add_event_listener(self, event: str, callback: Callable):
        """添加事件监听器"""
        self.event_bus.on(event, callback)

    def remove_event_listener(self, event: str, callback: Callable):
        """移除事件监听器"""
        self.event_bus.off(event, callback)