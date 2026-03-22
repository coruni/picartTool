#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
处理管道 - 编排处理器执行
"""

from typing import List, Optional, Callable
from .context import ProcessingContext
from .base import BaseProcessor, StopPipeline
from .events import Events, EventBus, get_event_bus


class Pipeline:
    """
    处理管道

    编排多个处理器的执行顺序
    """

    def __init__(self, event_bus: EventBus = None):
        self._processors: List[BaseProcessor] = []
        self._event_bus = event_bus or get_event_bus()
        self._on_error: Optional[Callable] = None
        self._stop_on_error: bool = True

    def add_processor(self, processor: BaseProcessor) -> 'Pipeline':
        """
        添加处理器

        Args:
            processor: 处理器实例

        Returns:
            self（支持链式调用）
        """
        self._processors.append(processor)
        return self

    def remove_processor(self, name: str) -> bool:
        """
        移除处理器

        Args:
            name: 处理器名称

        Returns:
            是否成功移除
        """
        for i, processor in enumerate(self._processors):
            if processor.name == name:
                self._processors.pop(i)
                return True
        return False

    def get_processor(self, name: str) -> Optional[BaseProcessor]:
        """
        获取处理器

        Args:
            name: 处理器名称

        Returns:
            处理器实例或None
        """
        for processor in self._processors:
            if processor.name == name:
                return processor
        return None

    def sort_by_priority(self) -> 'Pipeline':
        """
        按优先级排序处理器

        Returns:
            self
        """
        self._processors.sort(key=lambda p: p.priority)
        return self

    def set_stop_on_error(self, stop: bool) -> 'Pipeline':
        """
        设置是否在错误时停止

        Args:
            stop: 是否停止

        Returns:
            self
        """
        self._stop_on_error = stop
        return self

    def on_error(self, callback: Callable) -> 'Pipeline':
        """
        设置错误回调

        Args:
            callback: 回调函数 (processor_name, error) -> bool

        Returns:
            self
        """
        self._on_error = callback
        return self

    def execute(self, context: ProcessingContext) -> ProcessingContext:
        """
        执行管道

        Args:
            context: 处理上下文

        Returns:
            处理后的上下文
        """
        # 触发管道开始事件
        self._emit_event(Events.PIPELINE_START, context)

        # 按优先级排序
        sorted_processors = sorted(self._processors, key=lambda p: p.priority)

        for processor in sorted_processors:
            try:
                # 检查是否可以处理
                if not processor.can_process(context):
                    self._emit_event(Events.PROCESSOR_SKIP, processor.name, "无法处理")
                    continue

                # 检查是否应该跳过
                if processor.should_skip(context):
                    self._emit_event(Events.PROCESSOR_SKIP, processor.name, "配置跳过")
                    continue

                # 处理前钩子
                processor.before_process(context)

                # 执行处理
                context = processor.process(context)

                # 处理后钩子
                processor.after_process(context)

            except StopPipeline as e:
                # 停止管道
                context.add_error(processor.name, f"管道停止: {e.reason}")
                self._emit_event(Events.PIPELINE_ERROR, processor.name, e.reason)
                break

            except Exception as e:
                # 错误处理
                processor.on_error(context, e)

                # 调用错误回调
                should_continue = False
                if self._on_error:
                    try:
                        should_continue = self._on_error(processor.name, e)
                    except Exception:
                        pass

                # 决定是否继续
                if self._stop_on_error and not should_continue:
                    self._emit_event(Events.PIPELINE_ERROR, processor.name, str(e))
                    break

        # 标记完成
        context.complete()

        # 触发管道完成事件
        self._emit_event(Events.PIPELINE_COMPLETE, context)

        return context

    def execute_async(self, context: ProcessingContext,
                      callback: Callable[[ProcessingContext], None] = None) -> None:
        """
        异步执行管道

        Args:
            context: 处理上下文
            callback: 完成回调
        """
        import threading

        def run():
            result = self.execute(context)
            if callback:
                callback(result)

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

    @property
    def processors(self) -> List[BaseProcessor]:
        """获取处理器列表"""
        return self._processors.copy()

    @property
    def processor_count(self) -> int:
        """获取处理器数量"""
        return len(self._processors)

    def clear(self) -> 'Pipeline':
        """清空处理器"""
        self._processors.clear()
        return self

    def _emit_event(self, event: str, *args) -> None:
        """触发事件"""
        if self._event_bus:
            self._event_bus.emit(event, *args)

    def __len__(self) -> int:
        return len(self._processors)

    def __iter__(self):
        return iter(self._processors)

    def __repr__(self) -> str:
        processor_names = [p.name for p in self._processors]
        return f"<Pipeline processors={processor_names}>"


class PipelineBuilder:
    """
    管道构建器

    提供流畅的API来构建处理管道
    """

    def __init__(self, event_bus: EventBus = None):
        self._pipeline = Pipeline(event_bus)

    def add(self, processor: BaseProcessor) -> 'PipelineBuilder':
        """添加处理器"""
        self._pipeline.add_processor(processor)
        return self

    def add_all(self, *processors: BaseProcessor) -> 'PipelineBuilder':
        """添加多个处理器"""
        for processor in processors:
            self._pipeline.add_processor(processor)
        return self

    def stop_on_error(self, stop: bool = True) -> 'PipelineBuilder':
        """设置是否在错误时停止"""
        self._pipeline.set_stop_on_error(stop)
        return self

    def on_error(self, callback: Callable) -> 'PipelineBuilder':
        """设置错误回调"""
        self._pipeline.on_error(callback)
        return self

    def sort_by_priority(self) -> 'PipelineBuilder':
        """按优先级排序"""
        self._pipeline.sort_by_priority()
        return self

    def build(self) -> Pipeline:
        """构建管道"""
        return self._pipeline

    @classmethod
    def create(cls, event_bus: EventBus = None) -> 'PipelineBuilder':
        """创建构建器"""
        return cls(event_bus)