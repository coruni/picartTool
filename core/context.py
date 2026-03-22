#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
处理上下文 - 在管道中传递数据
"""

import os
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable

# 延迟导入避免循环依赖
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from infrastructure.config import Config


@dataclass
class FileStats:
    """文件统计信息"""
    image_count: int = 0
    video_count: int = 0
    total_size_bytes: int = 0

    @property
    def total_size_mb(self) -> int:
        return int(self.total_size_bytes / (1024 * 1024))

    def to_dict(self) -> Dict[str, Any]:
        return {
            'image_count': self.image_count,
            'video_count': self.video_count,
            'total_size_bytes': self.total_size_bytes,
            'total_size_mb': self.total_size_mb
        }


@dataclass
class AIResult:
    """AI处理结果"""
    coser_name: Optional[str] = None
    work_name: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class ProcessingContext:
    """
    处理上下文 - 在管道中传递数据

    包含处理过程中的所有状态和数据
    """

    # ============ 输入信息 ============
    source_path: str = ""                     # 原始文件路径
    original_name: str = ""                   # 原始文件名
    is_directory: bool = False                # 是否为目录

    # ============ 中间状态 ============
    temp_dir: Optional[str] = None            # 临时目录
    extracted_dir: Optional[str] = None       # 解压后目录
    processed_dir: Optional[str] = None       # 处理后目录
    clean_name: Optional[str] = None          # 清理后的名称

    # ============ 统计信息 ============
    stats: FileStats = field(default_factory=FileStats)

    # ============ AI处理结果 ============
    ai_result: Optional[AIResult] = None

    # ============ 标题和标签 ============
    formatted_title: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    # ============ 输出结果 ============
    output_archive: Optional[str] = None      # 输出压缩包路径
    uploaded_urls: List[str] = field(default_factory=list)  # 上传的URL列表
    article_id: Optional[str] = None          # 发布的文章ID

    # ============ 错误和警告 ============
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # ============ 元数据 ============
    metadata: Dict[str, Any] = field(default_factory=dict)
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None

    # ============ 配置引用 ============
    config: Optional['Config'] = None

    # ============ 回调函数 ============
    status_callback: Optional[Callable[[str], None]] = None

    def update_status(self, message: str):
        """更新状态"""
        if self.status_callback:
            self.status_callback(message)

    def add_error(self, processor_name: str, error: str):
        """添加错误"""
        self.errors.append(f"[{processor_name}] {error}")

    def add_warning(self, processor_name: str, warning: str):
        """添加警告"""
        self.warnings.append(f"[{processor_name}] {warning}")

    @property
    def has_errors(self) -> bool:
        """是否有错误"""
        return len(self.errors) > 0

    @property
    def has_critical_errors(self) -> bool:
        """是否有严重错误"""
        # 检查是否有阻止继续处理的错误
        critical_keywords = ['解压失败', '登录失败', '工具未找到']
        for error in self.errors:
            for keyword in critical_keywords:
                if keyword in error:
                    return True
        return False

    @property
    def processing_time(self) -> float:
        """处理耗时（秒）"""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time

    def complete(self):
        """标记处理完成"""
        self.end_time = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'source_path': self.source_path,
            'original_name': self.original_name,
            'is_directory': self.is_directory,
            'clean_name': self.clean_name,
            'formatted_title': self.formatted_title,
            'stats': self.stats.to_dict(),
            'tags': self.tags,
            'output_archive': self.output_archive,
            'uploaded_urls': self.uploaded_urls,
            'article_id': self.article_id,
            'errors': self.errors,
            'warnings': self.warnings,
            'processing_time': self.processing_time
        }

    @classmethod
    def create(cls, source_path: str, config: 'Config' = None,
               status_callback: Callable[[str], None] = None) -> 'ProcessingContext':
        """
        创建处理上下文的工厂方法

        Args:
            source_path: 源文件/目录路径
            config: 配置对象
            status_callback: 状态回调函数

        Returns:
            ProcessingContext 实例
        """
        context = cls(
            source_path=source_path,
            original_name=os.path.basename(source_path),
            is_directory=os.path.isdir(source_path),
            config=config,
            status_callback=status_callback
        )

        # 移除扩展名（如果是压缩文件）
        if not context.is_directory:
            name = os.path.splitext(context.original_name)[0]
            # 移除可能的第二个扩展名（如 .7z.zst）
            if name.lower().endswith('.7z'):
                name = name[:-3]
            context.original_name = name

        return context