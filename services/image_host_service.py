#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图床服务 - 处理图片上传到图床
"""

import base64
import os
import time
from typing import List, Optional

import requests


# MIME 类型映射
MIME_TYPES = {
    '.webp': 'image/webp',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.bmp': 'image/bmp',
    '.mp4': 'video/mp4',
    '.webm': 'video/webm',
}


class ImageHostService:
    """
    图床服务

    负责将图片上传到图床并获取URL
    """

    def __init__(self, config, logger=None):
        self.config = config
        self.logger = logger

        # 创建会话
        self.session = requests.Session()

    def is_enabled(self) -> bool:
        """检查图床是否启用"""
        return (
            self.config.image_host_enabled
            and bool(self.config.image_host_api)
            and bool(self.config.image_host_key)
        )

    def _get_mime_type(self, file_path: str) -> str:
        """获取文件的 MIME 类型"""
        ext = os.path.splitext(file_path)[1].lower()
        return MIME_TYPES.get(ext, 'application/octet-stream')

    def upload_file(self, file_path: str) -> Optional[str]:
        """
        上传单个文件到图床

        Args:
            file_path: 文件路径

        Returns:
            上传成功返回URL，失败返回None
        """
        if not self.is_enabled():
            self._log("图床未启用或配置不完整", level="warning")
            return None

        if not os.path.exists(file_path):
            self._log(f"文件不存在: {file_path}", level="error")
            return None

        for attempt in range(self.config.max_retries):
            try:
                self._log(f"[ImageHost] 上传文件: {os.path.basename(file_path)}")

                # 获取文件信息
                filename = os.path.basename(file_path)
                file_size = os.path.getsize(file_path)
                self._log(f"[ImageHost] 文件大小: {file_size} bytes")

                # 读取文件并转为 base64
                with open(file_path, 'rb') as f:
                    file_b64 = base64.b64encode(f.read()).decode()

                # 使用 data 参数发送 base64 编码的数据
                data = {
                    'source': file_b64,
                    'key': self.config.image_host_key,
                    'format': 'txt'
                }

                self._log(f"[ImageHost] 请求URL: {self.config.image_host_api}")

                response = self.session.post(
                    self.config.image_host_api,
                    data=data,
                    timeout=self.config.api_timeout
                )

                self._log(f"[ImageHost] 响应状态码: {response.status_code}")
                self._log(f"[ImageHost] 响应内容: {response.text[:200]}")

                if response.status_code == 200:
                    url = response.text.strip()
                    if url.startswith('http'):
                        self._log(f"[ImageHost] 上传成功: {url}")
                        return url
                    else:
                        self._log(f"[ImageHost] 响应不是有效URL: {url[:100]}", level="warning")
                else:
                    self._log(f"[ImageHost] 上传失败: HTTP {response.status_code}", level="warning")

            except Exception as e:
                self._log(f"[ImageHost] 上传异常: {e}", level="warning")

            if attempt < self.config.max_retries - 1:
                wait_time = (attempt + 1) * 3
                self._log(f"[ImageHost] 等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)

        self._log(f"[ImageHost] 上传失败，已达到最大重试次数", level="error")
        return None

    def upload_files(self, directory: str, extensions: List[str] = None) -> List[str]:
        """
        上传目录中的图片文件

        Args:
            directory: 目录路径
            extensions: 文件扩展名列表，默认为 ['.webp', '.jpg', '.jpeg', '.png']

        Returns:
            上传成功的URL列表
        """
        if extensions is None:
            extensions = ['.webp', '.jpg', '.jpeg', '.png']

        self._log(f"[ImageHost] 开始上传文件，目录: {directory}")

        if not os.path.exists(directory):
            self._log(f"[ImageHost] 目录不存在: {directory}", level="error")
            return []

        # 收集图片文件
        all_images = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in extensions:
                    all_images.append(os.path.join(root, file))

        if not all_images:
            self._log(f"[ImageHost] 没有找到图片文件", level="warning")
            return []

        # 自然排序
        import re
        def natural_sort_key(text: str):
            dirname, filename = os.path.split(text)
            def tryint(s):
                try:
                    return int(s)
                except:
                    return s
            return [dirname] + [tryint(c) for c in re.split('([0-9]+)', filename)]

        all_images.sort(key=natural_sort_key)
        self._log(f"[ImageHost] 找到 {len(all_images)} 张图片待上传")

        # 上传文件
        urls = []
        for i, image_path in enumerate(all_images):
            self._log(f"[ImageHost] 上传进度: {i + 1}/{len(all_images)}")
            url = self.upload_file(image_path)
            if url:
                urls.append(url)
            else:
                self._log(f"[ImageHost] 文件上传失败: {image_path}", level="warning")

        self._log(f"[ImageHost] 上传完成，共 {len(urls)} 个URL")
        return urls

    def test_connection(self) -> tuple:
        """
        测试图床连接

        Returns:
            (success: bool, message: str)
        """
        if not self.config.image_host_api:
            return False, "图床API地址未设置"

        if not self.config.image_host_key:
            return False, "图床API Key未设置"

        try:
            # 创建一个 1x1 的最小 PNG 图片 (base64)
            # 这是一个有效的 PNG 文件
            png_b64 = (
                'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
            )

            data = {
                'source': png_b64,
                'key': self.config.image_host_key,
                'format': 'txt'
            }

            response = self.session.post(
                self.config.image_host_api,
                data=data,
                timeout=30
            )

            if response.status_code == 200:
                url = response.text.strip()
                if url.startswith('http'):
                    return True, f"连接成功！测试URL: {url}"
                else:
                    return True, f"连接成功！响应: {url[:100]}"
            else:
                return False, f"连接失败: HTTP {response.status_code}"

        except Exception as e:
            return False, f"连接错误: {e}"

    def _log(self, message: str, level: str = "info"):
        """记录日志"""
        if self.logger:
            if level == "error":
                self.logger.error(message)
            elif level == "warning":
                self.logger.warning(message)
            else:
                self.logger.info(message)