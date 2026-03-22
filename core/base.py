#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基础处理器接口
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from .context import ProcessingContext
from .events import Events, EventBus, get_event_bus


class BaseProcessor(ABC):
    """
    基础处理器接口

    所有处理器都应该继承此类并实现 process 方法
    """

    def __init__(self, event_bus: EventBus = None):
        self._event_bus = event_bus or get_event_bus()

    @property
    @abstractmethod
    def name(self) -> str:
        """
        处理器名称

        Returns:
            处理器名称字符串
        """
        pass

    @property
    def description(self) -> str:
        """
        处理器描述

        Returns:
            描述字符串
        """
        return ""

    @property
    def priority(self) -> int:
        """
        处理器优先级（数字越小优先级越高）

        Returns:
            优先级值
        """
        return 100

    @property
    def required_config(self) -> List[str]:
        """
        需要的配置项列表

        Returns:
            配置项名称列表
        """
        return []

    @abstractmethod
    def process(self, context: ProcessingContext) -> ProcessingContext:
        """
        执行处理

        Args:
            context: 处理上下文

        Returns:
            更新后的处理上下文
        """
        pass

    def can_process(self, context: ProcessingContext) -> bool:
        """
        检查是否可以处理

        Args:
            context: 处理上下文

        Returns:
            是否可以处理
        """
        # 检查是否有阻止性错误
        if context.has_critical_errors:
            return False

        # 检查必需的配置项
        if self.required_config and context.config:
            for config_key in self.required_config:
                if not getattr(context.config, config_key, None):
                    context.add_warning(
                        self.name,
                        f"缺少配置项: {config_key}"
                    )
                    return False

        return True

    def should_skip(self, context: ProcessingContext) -> bool:
        """
        检查是否应该跳过

        用于实现可选功能的跳过逻辑

        Args:
            context: 处理上下文

        Returns:
            是否跳过
        """
        return False

    def before_process(self, context: ProcessingContext) -> None:
        """
        处理前钩子

        Args:
            context: 处理上下文
        """
        self._emit_event(Events.PROCESSOR_START, self.name)

    def after_process(self, context: ProcessingContext) -> None:
        """
        处理后钩子

        Args:
            context: 处理上下文
        """
        self._emit_event(Events.PROCESSOR_COMPLETE, self.name)

    def on_error(self, context: ProcessingContext, error: Exception) -> None:
        """
        错误处理钩子

        Args:
            context: 处理上下文
            error: 异常对象
        """
        context.add_error(self.name, str(error))
        self._emit_event(Events.PROCESSOR_ERROR, self.name, str(error))

    def update_progress(self, context: ProcessingContext,
                        progress: int, total: int,
                        message: str = None) -> None:
        """
        更新处理进度

        Args:
            context: 处理上下文
            progress: 当前进度
            total: 总数
            message: 进度消息
        """
        self._emit_event(
            Events.PROCESSOR_PROGRESS,
            self.name, progress, total, message
        )

    def update_status(self, context: ProcessingContext, message: str) -> None:
        """
        更新状态消息

        Args:
            context: 处理上下文
            message: 状态消息
        """
        formatted_message = f"[{self.name}] {message}"
        context.update_status(formatted_message)
        self._emit_event(Events.STATUS_UPDATE, formatted_message)

    def _emit_event(self, event: str, *args) -> None:
        """触发事件"""
        if self._event_bus:
            self._event_bus.emit(event, *args)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name='{self.name}' priority={self.priority}>"


class SkipProcessor(Exception):
    """
    跳过处理器异常

    抛出此异常表示当前处理器应该被跳过
    """
    def __init__(self, reason: str = ""):
        self.reason = reason
        super().__init__(reason)


class StopPipeline(Exception):
    """
    停止管道异常

    抛出此异常表示应该停止整个处理管道
    """
    def __init__(self, reason: str = "", context: ProcessingContext = None):
        self.reason = reason
        self.context = context
        super().__init__(reason)