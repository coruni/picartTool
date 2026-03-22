#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志管理模块
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from io import StringIO


class Logger:
    """
    日志管理类

    支持文件日志、控制台日志和内存日志
    """

    def __init__(self, log_dir: str = "logs", name: str = None, level: int = logging.INFO):
        """
        初始化日志管理器

        Args:
            log_dir: 日志目录
            name: 日志器名称
            level: 日志级别
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 日志文件名
        timestamp = datetime.now().strftime('%Y%m%d')
        self.log_file = self.log_dir / f"processing_{timestamp}.log"

        # 创建日志器
        self.name = name or __name__
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(level)

        # 避免重复添加handler
        if not self.logger.handlers:
            self._setup_handlers()

        # 内存日志缓存
        self._memory_handler = StringIO()
        self._memory_logger = logging.StreamHandler(self._memory_handler)
        self._memory_logger.setFormatter(
            logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s')
        )
        self.logger.addHandler(self._memory_logger)

    def _setup_handlers(self):
        """设置日志处理器"""
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 文件处理器
        file_handler = logging.FileHandler(
            self.log_file,
            encoding='utf-8',
            mode='a'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def info(self, message: str):
        """记录信息日志"""
        self.logger.info(message)

    def error(self, message: str):
        """记录错误日志"""
        self.logger.error(message)

    def warning(self, message: str):
        """记录警告日志"""
        self.logger.warning(message)

    def debug(self, message: str):
        """记录调试日志"""
        self.logger.debug(message)

    def critical(self, message: str):
        """记录严重错误日志"""
        self.logger.critical(message)

    def exception(self, message: str):
        """记录异常日志（包含堆栈信息）"""
        self.logger.exception(message)

    def get_log_file_path(self) -> str:
        """获取日志文件路径"""
        return str(self.log_file)

    def get_memory_logs(self) -> str:
        """获取内存中的日志"""
        return self._memory_handler.getvalue()

    def clear_memory_logs(self) -> None:
        """清空内存日志"""
        self._memory_handler.truncate(0)
        self._memory_handler.seek(0)

    def get_recent_logs(self, lines: int = 100) -> List[str]:
        """
        获取最近的日志

        Args:
            lines: 行数

        Returns:
            日志行列表
        """
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                return all_lines[-lines:]
        except Exception:
            return []


class LogManager:
    """
    日志管理器

    提供全局日志管理功能
    """

    _instance: Optional['LogManager'] = None
    _loggers: dict = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_logger(cls, name: str = None, log_dir: str = "logs") -> Logger:
        """
        获取日志器

        Args:
            name: 日志器名称
            log_dir: 日志目录

        Returns:
            Logger实例
        """
        instance = cls()
        key = name or "default"

        if key not in instance._loggers:
            instance._loggers[key] = Logger(log_dir=log_dir, name=name)

        return instance._loggers[key]

    @classmethod
    def set_log_dir(cls, log_dir: str) -> None:
        """
        设置日志目录

        Args:
            log_dir: 日志目录
        """
        instance = cls()
        instance._loggers.clear()  # 清除缓存，下次获取时重新创建
        os.makedirs(log_dir, exist_ok=True)