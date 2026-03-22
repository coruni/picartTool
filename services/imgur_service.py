#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Imgur上传服务 - 将图片上传到Imgur图床
"""

import base64
import os
import time
from typing import List, Optional

import requests


class ImgurService:
    """
    Imgur图床服务

    负责将图片上传到Imgur并获取URL
    """

    # Imgur API 端点
    UPLOAD_API = "https://api.imgur.com/3/image"

    # 支持的图片格式
    SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}

    def __init__(self, config, logger=None):
        self.config = config
        self.logger = logger

        # 创建会话
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Client-ID {self.config.imgur_client_id}'
        })

    def is_enabled(self) -> bool:
        """检查Imgur服务是否启用"""
        return bool(self.config.imgur_client_id)

    def upload_file(self, file_path: str) -> Optional[str]:
        """
        上传单个文件到Imgur

        Args:
            file_path: 文件路径

        Returns:
            上传成功返回URL，失败返回None
        """
        if not self.is_enabled():
            self._log("Imgur未配置Client ID", level="warning")
            return None

        if not os.path.exists(file_path):
            self._log(f"文件不存在: {file_path}", level="error")
            return None

        for attempt in range(self.config.max_retries):
            try:
                self._log(f"[Imgur] 上传文件: {os.path.basename(file_path)}")

                # 读取文件并转为 base64
                with open(file_path, 'rb') as f:
                    file_b64 = base64.b64encode(f.read()).decode()

                # 构建请求数据
                data = {
                    'image': file_b64,
                    'type': 'base64'
                }

                response = self.session.post(
                    self.UPLOAD_API,
                    data=data,
                    timeout=self.config.api_timeout
                )

                self._log(f"[Imgur] 响应状态码: {response.status_code}")

                if response.status_code == 200:
                    result = response.json()
                    if result.get('success') and result.get('data', {}).get('link'):
                        url = result['data']['link']
                        self._log(f"[Imgur] 上传成功: {url}")
                        return url
                    else:
                        error_msg = result.get('data', {}).get('error', '未知错误')
                        self._log(f"[Imgur] 上传失败: {error_msg}", level="warning")
                elif response.status_code == 429:
                    # 速率限制，等待更长时间
                    wait_time = 60  # 等待60秒
                    self._log(f"[Imgur] 达到速率限制，等待 {wait_time} 秒...", level="warning")
                    time.sleep(wait_time)
                    continue
                else:
                    self._log(f"[Imgur] 上传失败: HTTP {response.status_code}", level="warning")
                    # 打印响应内容以便调试
                    try:
                        self._log(f"[Imgur] 响应: {response.text[:200]}", level="warning")
                    except:
                        pass

            except Exception as e:
                self._log(f"[Imgur] 上传异常: {e}", level="warning")

            if attempt < self.config.max_retries - 1:
                wait_time = (attempt + 1) * 5
                self._log(f"[Imgur] 等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)

        self._log(f"[Imgur] 上传失败，已达到最大重试次数", level="error")
        return None

    def upload_files(self, directory: str, extensions: List[str] = None) -> List[str]:
        """
        上传目录中的图片文件

        Args:
            directory: 目录路径
            extensions: 文件扩展名列表，默认为 ['.jpg', '.jpeg', '.png']

        Returns:
            上传成功的URL列表
        """
        if extensions is None:
            extensions = ['.jpg', '.jpeg', '.png']

        self._log(f"[Imgur] 开始上传文件，目录: {directory}")

        if not os.path.exists(directory):
            self._log(f"[Imgur] 目录不存在: {directory}", level="error")
            return []

        # 收集图片文件
        all_images = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in extensions:
                    all_images.append(os.path.join(root, file))

        if not all_images:
            self._log(f"[Imgur] 没有找到图片文件", level="warning")
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
        self._log(f"[Imgur] 找到 {len(all_images)} 张图片待上传")

        # 上传文件
        urls = []
        for i, image_path in enumerate(all_images):
            self._log(f"[Imgur] 上传进度: {i + 1}/{len(all_images)}")
            url = self.upload_file(image_path)
            if url:
                urls.append(url)
            else:
                self._log(f"[Imgur] 文件上传失败: {image_path}", level="warning")

            # 添加延迟以避免速率限制
            # Imgur 免费API有限制：约1250次上传/天
            if i < len(all_images) - 1:
                time.sleep(1)

        self._log(f"[Imgur] 上传完成，共 {len(urls)} 个URL")
        return urls

    def test_connection(self) -> tuple:
        """
        测试Imgur连接

        Returns:
            (success: bool, message: str)
        """
        if not self.config.imgur_client_id:
            return False, "Imgur Client ID 未设置"

        try:
            # 创建一个 1x1 的最小 PNG 图片 (base64)
            png_b64 = (
                'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
            )

            data = {
                'image': png_b64,
                'type': 'base64'
            }

            # 使用临时会话测试
            test_session = requests.Session()
            test_session.headers.update({
                'Authorization': f'Client-ID {self.config.imgur_client_id}'
            })

            response = test_session.post(
                self.UPLOAD_API,
                data=data,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    url = result.get('data', {}).get('link', '')
                    return True, f"连接成功！测试URL: {url}"
                else:
                    error = result.get('data', {}).get('error', '未知错误')
                    return False, f"认证失败: {error}"
            elif response.status_code == 403:
                return False, "认证失败：请检查 Client ID 是否正确"
            elif response.status_code == 429:
                return False, "达到速率限制，请稍后再试"
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