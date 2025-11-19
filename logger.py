#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志管理模块
"""

import logging
import os
from datetime import datetime
from pathlib import Path


class Logger:
    """日志管理类"""

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / f"processing_{datetime.now().strftime('%Y%m%d')}.log"

        # 配置日志
        logging.basicConfig(
            level=logging.INFO,
            format='[%(asctime)s] [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(self.log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

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

    def get_log_file_path(self) -> str:
        """获取日志文件路径"""
        return str(self.log_file)