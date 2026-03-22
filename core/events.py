#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
事件系统 - 模块间通信
"""

from collections import defaultdict
from typing import Callable, Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import threading


@dataclass
class Event:
    """事件对象"""
    name: str
    timestamp: datetime
    data: Any = None
    source: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'timestamp': self.timestamp.isoformat(),
            'data': self.data,
            'source': self.source
        }


class Events:
    """预定义事件常量"""

    # ============ 管道事件 ============
    PIPELINE_START = 'pipeline:start'
    PIPELINE_COMPLETE = 'pipeline:complete'
    PIPELINE_ERROR = 'pipeline:error'

    # ============ 处理器事件 ============
    PROCESSOR_START = 'processor:start'
    PROCESSOR_PROGRESS = 'processor:progress'
    PROCESSOR_COMPLETE = 'processor:complete'
    PROCESSOR_ERROR = 'processor:error'
    PROCESSOR_SKIP = 'processor:skip'

    # ============ 文件事件 ============
    FILE_EXTRACTED = 'file:extracted'
    FILE_CLEANED = 'file:cleaned'
    FILE_RENAMED = 'file:renamed'
    FILE_COMPRESSED = 'file:compressed'
    FILE_ARCHIVED = 'file:archived'
    FILE_UPLOADED = 'file:uploaded'

    # ============ 文章事件 ============
    ARTICLE_PUBLISHING = 'article:publishing'
    ARTICLE_PUBLISHED = 'article:published'
    ARTICLE_DRAFT = 'article:draft'

    # ============ AI事件 ============
    AI_TITLE_GENERATED = 'ai:title_generated'
    AI_TAGS_GENERATED = 'ai:tags_generated'

    # ============ 状态事件 ============
    STATUS_UPDATE = 'status:update'
    LOG_MESSAGE = 'log:message'


class EventBus:
    """
    事件总线 - 发布/订阅模式

    用于模块间的松耦合通信
    """

    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = defaultdict(list)
        self._event_history: List[Event] = []
        self._max_history: int = 100
        self._lock = threading.Lock()

    def on(self, event: str, callback: Callable) -> 'EventBus':
        """
        注册事件监听器

        Args:
            event: 事件名称
            callback: 回调函数

        Returns:
            self（支持链式调用）
        """
        with self._lock:
            self._listeners[event].append(callback)
        return self

    def off(self, event: str, callback: Callable) -> bool:
        """
        移除事件监听器

        Args:
            event: 事件名称
            callback: 要移除的回调函数

        Returns:
            是否成功移除
        """
        with self._lock:
            if callback in self._listeners[event]:
                self._listeners[event].remove(callback)
                return True
        return False

    def once(self, event: str, callback: Callable) -> 'EventBus':
        """
        注册一次性事件监听器（触发一次后自动移除）

        Args:
            event: 事件名称
            callback: 回调函数

        Returns:
            self
        """
        def wrapper(*args, **kwargs):
            self.off(event, wrapper)
            callback(*args, **kwargs)

        return self.on(event, wrapper)

    def emit(self, event: str, *args, **kwargs) -> 'EventBus':
        """
        触发事件

        Args:
            event: 事件名称
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            self
        """
        # 创建事件对象
        event_obj = Event(
            name=event,
            timestamp=datetime.now(),
            data={'args': args, 'kwargs': kwargs}
        )

        # 记录历史
        with self._lock:
            self._event_history.append(event_obj)
            if len(self._event_history) > self._max_history:
                self._event_history.pop(0)

            # 获取监听器副本（避免在回调中修改列表）
            listeners = self._listeners.get(event, []).copy()

        # 调用监听器
        for callback in listeners:
            try:
                callback(*args, **kwargs)
            except Exception as e:
                # 记录错误但不中断其他监听器
                print(f"[EventBus] Error in callback for {event}: {e}")

        return self

    def emit_async(self, event: str, *args, **kwargs) -> None:
        """
        异步触发事件（在后台线程中执行）

        Args:
            event: 事件名称
            *args: 位置参数
            **kwargs: 关键字参数
        """
        thread = threading.Thread(
            target=self.emit,
            args=(event,) + args,
            kwargs=kwargs,
            daemon=True
        )
        thread.start()

    def clear(self, event: str = None):
        """
        清除监听器

        Args:
            event: 事件名称，为None时清除所有
        """
        with self._lock:
            if event:
                self._listeners[event].clear()
            else:
                self._listeners.clear()

    def get_history(self, event: str = None) -> List[Event]:
        """
        获取事件历史

        Args:
            event: 事件名称，为None时返回所有

        Returns:
            事件列表
        """
        with self._lock:
            if event:
                return [e for e in self._event_history if e.name == event]
            return self._event_history.copy()

    def listener_count(self, event: str = None) -> int:
        """
        获取监听器数量

        Args:
            event: 事件名称，为None时返回总数

        Returns:
            监听器数量
        """
        with self._lock:
            if event:
                return len(self._listeners.get(event, []))
            return sum(len(v) for v in self._listeners.values())


# 全局事件总线实例
_global_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """获取全局事件总线实例"""
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus


def set_event_bus(event_bus: EventBus):
    """设置全局事件总线实例"""
    global _global_event_bus
    _global_event_bus = event_bus