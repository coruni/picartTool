#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API处理模块
"""

import os
import re
import time
import requests
from pathlib import Path
from typing import List, Dict, Any
from logger import Logger
from config import Config


class APIHandler:
    """API处理类"""

    def __init__(self, logger: Logger, config: Config):
        self.logger = logger
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Linux; U; Android 4.0.3; ko-kr; LG-L160L Build/IML74K) AppleWebkit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30',
            'Device-Id': config.device_id
        })

    def is_token_valid(self) -> bool:
        """检查token是否存在且有效"""
        if not self.config.access_token:
            return False

        # 确保session headers中有token
        if 'Authorization' not in self.session.headers:
            self.session.headers['Authorization'] = f'Bearer {self.config.access_token}'

        return True

    def ensure_login(self) -> bool:
        """确保已登录（优先使用已有token，无效时才重新登录）"""
        # 如果已有token，先尝试使用
        if self.is_token_valid():
            self.logger.info("使用已有token，跳过登录")
            return True

        # 没有token或token无效，重新登录
        return self.login()

    def login(self) -> bool:
        """登录获取token"""
        self.logger.info("开始登录获取token")

        for attempt in range(self.config.max_retries):
            try:
                login_data = {
                    'account': self.config.login_account,
                    'password': self.config.login_password
                }

                response = self.session.post(
                    self.config.login_api,
                    json=login_data,
                    timeout=self.config.api_timeout
                )

                if response.status_code in [200, 201]:
                    data = response.json()
                    if data.get('code') in [0, 200, 201]:
                        token = data.get('data', {}).get('token')
                        if token:
                            self.config.access_token = token
                            self.session.headers['Authorization'] = f'Bearer {token}'
                            self.logger.info("登录成功，获取到token")
                            return True

                self.logger.warning(f"登录失败 (第 {attempt + 1} 次): {response.text}")
            except Exception as e:
                self.logger.warning(f"登录请求失败 (第 {attempt + 1} 次): {e}")

            if attempt < self.config.max_retries - 1:
                time.sleep((attempt + 1) * 5)

        self.logger.error("登录失败，已达到最大重试次数")
        return False

    def _handle_auth_error(self, response_status_code: int = None) -> bool:
        """处理认证错误，尝试重新登录"""
        if response_status_code in [401, 403]:
            self.logger.warning(f"认证失败 ({response_status_code})，尝试重新登录")
            # 清除旧的token
            self.config.access_token = ""
            if 'Authorization' in self.session.headers:
                del self.session.headers['Authorization']
            # 重新登录
            return self.login()
        return False

    def upload_files(self, directory: str) -> List[str]:
        """上传文件（排除GIF文件）"""
        # 收集所有图片文件，但排除GIF
        image_extensions = {'.jpg', '.jpeg', '.png', '.webp'}  # 排除gif
        gif_extensions = {'.gif'}
        all_images = []
        skipped_gifs = []

        for root, dirs, files in os.walk(directory):
            for file in files:
                file_ext = Path(file).suffix.lower()
                file_path = os.path.join(root, file)

                if file_ext in gif_extensions:
                    skipped_gifs.append(file_path)
                    self.logger.debug(f"跳过GIF文件上传: {file}")
                elif file_ext in image_extensions:
                    all_images.append(file_path)

        if skipped_gifs:
            self.logger.info(f"上传时跳过 {len(skipped_gifs)} 个GIF文件")

        if not all_images:
            self.logger.error("没有找到可上传的图片")
            return []

        # 使用自然排序确保文件按正确顺序上传
        all_images.sort(key=self._natural_sort_key)
        total_images = len(all_images)
        self.logger.info(f"总共找到 {total_images} 张图片（已排除GIF），将分批上传")

        all_uploaded_urls = []
        batch_size = self.config.upload_batch_size

        for i in range(0, total_images, batch_size):
            current_batch = all_images[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_images + batch_size - 1) // batch_size

            self.logger.info(f"开始上传第 {batch_num}/{total_batches} 批 ({len(current_batch)} 张图片)")

            for attempt in range(self.config.max_retries):
                try:
                    files = []
                    for img_path in current_batch:
                        files.append(('file', open(img_path, 'rb')))

                    response = self.session.post(
                        self.config.upload_api,
                        files=files,
                        timeout=self.config.api_timeout
                    )

                    # 关闭文件
                    for _, file_obj in files:
                        file_obj.close()

                    if response.status_code in [200, 201]:  # 200和201都表示成功
                        data = response.json()
                        if data.get('code') in [0, 200, 201]:
                            urls = [item.get('url') for item in data.get('data', []) if item.get('url')]
                            if urls:
                                all_uploaded_urls.extend(urls)
                                self.logger.info(f"第 {batch_num} 批上传成功")
                                break
                        self.logger.warning(f"第 {batch_num} 批上传失败 (第 {attempt + 1} 次): {data}")
                    elif response.status_code in [401, 403]:
                        # 认证失败，尝试重新登录
                        if self._handle_auth_error(response.status_code):
                            # 重新登录成功，重试此批次上传
                            continue
                        else:
                            self.logger.error(f"重新登录失败，第 {batch_num} 批上传失败")
                            return []
                    else:
                        self.logger.warning(f"第 {batch_num} 批上传请求失败 (第 {attempt + 1} 次): {response.status_code}")

                except Exception as e:
                    self.logger.warning(f"第 {batch_num} 批上传请求失败 (第 {attempt + 1} 次): {e}")

                if attempt < self.config.max_retries - 1:
                    time.sleep((attempt + 1) * 5)
            else:
                self.logger.error(f"第 {batch_num} 批上传失败，已达到最大重试次数")
                return []

        self.logger.info(f"所有图片上传完成，共收集 {len(all_uploaded_urls)} 个URL")
        return all_uploaded_urls

    def submit_article(self, title: str, images: List[str], cover: str) -> bool:
        """提交文章"""
        self.logger.info(f"准备提交文章: {title}")

        for attempt in range(self.config.max_retries):
            try:
                article_data = {
                    'title': title,
                    'images': images,
                    'cover': cover,
                    'categoryId': 2,
                    'type': 'image',
                    'requireMembership': True,
                    'status': 'pending'
                }

                response = self.session.post(
                    self.config.article_api,
                    json=article_data,
                    timeout=self.config.api_timeout
                )

                if response.status_code in [200, 201]:  # 处理HTTP成功状态
                    data = response.json()
                    # 检查API响应中的code和success字段
                    api_code = data.get('code')
                    api_success = data.get('data', {}).get('success', False)

                    # 成功条件：API code为成功值 或者 success为true
                    if api_code in [0, 200, 201] or api_success:
                        self.logger.info(f"文章提交成功: {title}")
                        # 记录文章ID（如果有）
                        article_data = data.get('data', {}).get('data', {})
                        article_id = article_data.get('id')
                        if article_id:
                            self.logger.info(f"文章ID: {article_id}")
                        return True
                    else:
                        self.logger.warning(f"文章提交失败 (第 {attempt + 1} 次): API返回code={api_code}, success={api_success}")
                elif response.status_code in [401, 403]:
                    # 认证失败，尝试重新登录
                    if self._handle_auth_error(response.status_code):
                        # 重新登录成功，重试提交
                        continue
                    else:
                        self.logger.error(f"重新登录失败，文章提交失败")
                        return False
                else:
                    self.logger.warning(f"文章提交失败 (第 {attempt + 1} 次): HTTP状态码 {response.status_code}")

                # 只有在真正失败时才记录完整响应
                self.logger.debug(f"完整响应: {response.text}")
            except Exception as e:
                self.logger.warning(f"文章提交请求失败 (第 {attempt + 1} 次): {e}")

            if attempt < self.config.max_retries - 1:
                time.sleep((attempt + 1) * 5)

        self.logger.error("文章提交失败，已达到最大重试次数")
        return False

    def _natural_sort_key(self, text: str) -> List:
        """自然排序键函数，确保数字按数值排序而不是字符串排序"""
        # 分割路径和文件名
        dirname, filename = os.path.split(text)
        # 将文件名中的数字部分分离出来
        def tryint(s):
            try:
                return int(s)
            except:
                return s
        return [dirname] + [tryint(c) for c in re.split('([0-9]+)', filename)]

    def test_connection(self) -> bool:
        """测试API连接"""
        try:
            response = self.session.get(self.config.login_api, timeout=10)
            self.logger.info(f"API连接测试响应状态码: {response}")
            return response.status_code in [200, 404,201]  # 404也表示连接正常
        except Exception as e:
            self.logger.error(f"API连接测试失败: {e}")
            return False