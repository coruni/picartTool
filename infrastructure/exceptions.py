#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自定义异常模块
"""

class PicartToolError(Exception):
    """基础异常类"""
    def __init__(self, message: str, details: str = None):
        self.message = message
        self.details = details
        super().__init__(self.message)

    def __str__(self):
        if self.details:
            return f"{self.message} - {self.details}"
        return self.message


class CriticalError(PicartToolError):
    """关键错误 - 需要停止处理"""
    pass


class ExtractionError(CriticalError):
    """解压错误"""
    pass


class CompressionError(PicartToolError):
    """压缩错误"""
    pass


class UploadError(PicartToolError):
    """上传错误"""
    pass


class PublishError(PicartToolError):
    """发布错误"""
    pass


class ConfigurationError(PicartToolError):
    """配置错误"""
    pass


class ValidationError(PicartToolError):
    """验证错误"""
    pass


class ToolNotFoundError(CriticalError):
    """工具未找到错误"""
    pass


class AuthenticationError(CriticalError):
    """认证错误"""
    pass


class NetworkError(PicartToolError):
    """网络错误"""
    pass