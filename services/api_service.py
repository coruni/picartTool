#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API服务 - 处理与服务器API的交互
"""

import os
import re
import time
from typing import List, Dict, Any, Optional

import requests


class APIService:
    """
    API服务

    负责与服务器API交互：登录、上传、发布等
    """

    def __init__(self, config, logger=None):
        self.config = config
        self.logger = logger

        # 创建会话
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Linux; U; Android 4.0.3; ko-kr; LG-L160L Build/IML74K) AppleWebkit/534.30',
            'Device-Id': config.device_id,
            'Connection': 'close'  # 禁用 keep-alive，避免连接复用问题
        })

        # 缓存
        self._categories_cache = None

    def ensure_login(self) -> bool:
        """确保已登录"""
        if self.is_token_valid():
            return True
        return self.login()

    def is_token_valid(self) -> bool:
        """检查token是否有效"""
        if not self.config.access_token:
            return False

        if 'Authorization' not in self.session.headers:
            self.session.headers['Authorization'] = f'Bearer {self.config.access_token}'

        return True

    def login(self) -> bool:
        """登录获取token"""
        self._log("开始登录...")

        for attempt in range(self.config.max_retries):
            try:
                # 打印请求信息
                self._log(f"========== 登录请求 ==========")
                self._log(f"请求URL: {self.config.login_api}")
                self._log(f"请求Headers: {dict(self.session.headers)}")
                self._log(f"请求Body: account={self.config.login_account}, deviceId={self.config.device_id}")

                response = self.session.post(
                    self.config.login_api,
                    json={
                        'account': self.config.login_account,
                        'password': self.config.login_password,
                        'deviceId': self.config.device_id
                    },
                    timeout=self.config.api_timeout
                )

                # 打印响应信息
                self._log(f"========== 登录响应 ==========")
                self._log(f"响应状态码: HTTP {response.status_code}")
                self._log(f"响应内容: {response.text[:500] if len(response.text) > 500 else response.text}")

                if response.status_code in [200, 201]:
                    data = response.json()
                    if data.get('code') in [0, 200, 201]:
                        token = data.get('data', {}).get('token')
                        if token:
                            self.config.access_token = token
                            self.session.headers['Authorization'] = f'Bearer {token}'
                            self._log(f"登录成功, token: {token[:20]}...")
                            return True
                    self._log(f"登录失败: code={data.get('code')}, message={data.get('message')}", level="warning")
                else:
                    self._log(f"登录失败: HTTP {response.status_code}", level="warning")

            except Exception as e:
                self._log(f"登录请求失败: {e}", level="warning")

            if attempt < self.config.max_retries - 1:
                time.sleep((attempt + 1) * 5)

        self._log("登录失败，已达到最大重试次数", level="error")
        return False

    def upload_files(self, directory: str) -> List[str]:
        """
        上传目录中的图片文件（只上传压缩后的 webp 文件）

        Args:
            directory: 目录路径

        Returns:
            上传成功的URL列表
        """
        self._log(f"开始上传文件，目录: {directory}")

        # 检查目录是否存在
        if not os.path.exists(directory):
            self._log(f"目录不存在: {directory}", level="error")
            return []

        # 只收集 webp 文件（压缩后的文件）
        all_images = []

        for root, dirs, files in os.walk(directory):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext == '.webp':
                    all_images.append(os.path.join(root, file))

        if not all_images:
            self._log(f"没有找到 webp 文件，目录内容: {os.listdir(directory)[:10]}", level="error")
            return []

        # 自然排序
        all_images.sort(key=self._natural_sort_key)
        self._log(f"找到 {len(all_images)} 张 webp 图片待上传")

        # 分批上传
        all_urls = []
        batch_size = self.config.upload_batch_size

        for i in range(0, len(all_images), batch_size):
            batch = all_images[i:i + batch_size]
            batch_num = (i // batch_size) + 1

            self._log(f"上传第 {batch_num} 批 ({len(batch)} 张)")

            urls = self._upload_batch(batch)
            if urls:
                all_urls.extend(urls)
            else:
                self._log(f"第 {batch_num} 批上传失败", level="error")
                return []

        self._log(f"上传完成，共 {len(all_urls)} 个URL")
        return all_urls

    def _upload_batch(self, files: List[str]) -> Optional[List[str]]:
        """上传一批文件"""
        for attempt in range(self.config.max_retries):
            try:
                files_data = [('file', open(f, 'rb')) for f in files]

                try:
                    # 打印请求信息
                    self._log(f"========== 上传请求 ==========")
                    self._log(f"请求URL: {self.config.upload_api}")
                    self._log(f"请求Headers: {dict(self.session.headers)}")
                    self._log(f"上传文件数: {len(files)}")

                    response = self.session.post(
                        self.config.upload_api,
                        files=files_data,
                        timeout=self.config.api_timeout
                    )

                    # 打印响应信息
                    self._log(f"========== 上传响应 ==========")
                    self._log(f"响应状态码: HTTP {response.status_code}")
                    self._log(f"响应Headers: {dict(response.headers)}")
                    self._log(f"响应内容: {response.text[:1000] if len(response.text) > 1000 else response.text}")

                    if response.status_code in [200, 201]:
                        data = response.json()
                        self._log(f"解析后数据: code={data.get('code')}, message={data.get('message')}")
                        self._log(f"data字段内容: {data.get('data')}")

                        if data.get('code') in [0, 200, 201]:
                            response_data = data.get('data', [])
                            if isinstance(response_data, list):
                                urls = [item.get('url') for item in response_data if isinstance(item, dict)]
                                valid_urls = [u for u in urls if u]
                                self._log(f"获取到 {len(valid_urls)} 个URL: {valid_urls[:3]}...")
                                return valid_urls
                            else:
                                self._log(f"响应data不是列表: {response_data}", level="warning")
                        else:
                            self._log(f"API返回错误: code={data.get('code')}, message={data.get('message', data)}", level="warning")

                    # 认证错误
                    if response.status_code in [401, 403]:
                        self._log("认证失败，尝试重新登录", level="warning")
                        if self.login():
                            continue
                        return None

                    # 其他错误
                    self._log(f"上传失败: {response.text[:500]}", level="warning")

                finally:
                    for _, f in files_data:
                        f.close()

            except (ConnectionResetError, ConnectionError) as e:
                self._log(f"连接被重置: {e}", level="warning")
                # 连接错误时创建新session
                self._reset_session()

            except Exception as e:
                self._log(f"上传异常: {e}", level="warning")

            if attempt < self.config.max_retries - 1:
                wait_time = (attempt + 1) * 10  # 增加等待时间
                self._log(f"等待重试 ({attempt + 2}/{self.config.max_retries})，{wait_time}秒后重试...")
                time.sleep(wait_time)

        return None

    def _reset_session(self):
        """重置会话"""
        try:
            self.session.close()
        except:
            pass

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Linux; U; Android 4.0.3; ko-kr; LG-L160L Build/IML74K) AppleWebkit/534.30',
            'Device-Id': self.config.device_id,
            'Connection': 'close'  # 禁用 keep-alive
        })

        if self.config.access_token:
            self.session.headers['Authorization'] = f'Bearer {self.config.access_token}'

    def submit_article(self, title: str, images: List[str],
                       cover: str, publish: bool = True,
                       tag_names: List[str] = None,
                       downloads: List[Dict] = None) -> bool:
        """
        提交文章

        Args:
            title: 标题
            images: 图片URL列表
            cover: 封面URL
            publish: 是否发布
            tag_names: 标签列表
            downloads: 下载链接列表

        Returns:
            是否成功
        """
        self._log(f"提交文章: {title}")

        for attempt in range(self.config.max_retries):
            try:
                # 每次重试都重新获取分类（防止分类不存在）
                category_id = self._find_or_create_category(title, images[0] if images else None)
                self._log(f"[APIService] 使用分类ID: {category_id}")

                article_data = {
                    'title': title,
                    'images': images,
                    'cover': cover,
                    'categoryId': category_id,
                    'type': 'image',
                    'requireMembership': True,
                    'status': 'pending' if publish else 'draft'
                }

                if tag_names:
                    article_data['tagNames'] = tag_names

                # 添加下载链接
                if downloads:
                    article_data['downloads'] = downloads

                self._log(f"[APIService] 提交文章请求: {self.config.article_api}")
                response = self.session.post(
                    self.config.article_api,
                    json=article_data,
                    timeout=self.config.api_timeout
                )

                self._log(f"[APIService] 响应状态码: {response.status_code}")
                self._log(f"[APIService] 响应内容: {response.text[:500]}")

                if response.status_code in [200, 201]:
                    data = response.json()
                    if data.get('code') in [0, 200, 201] or data.get('data', {}).get('success'):
                        self._log("文章提交成功")
                        return True
                    else:
                        self._log(f"[APIService] API返回错误: code={data.get('code')}, message={data.get('message')}")

                # 分类不存在错误，下次重试会重新获取分类
                if response.status_code == 404:
                    self._log("[APIService] 分类不存在，下次重试将重新获取分类", level="warning")
                    continue

                # 认证错误
                if response.status_code in [401, 403]:
                    self._log("[APIService] 认证失败，尝试重新登录")
                    if self.login():
                        continue
                    return False

            except Exception as e:
                self._log(f"提交文章失败: {e}", level="warning")
                import traceback
                self._log(f"异常堆栈: {traceback.format_exc()}", level="warning")

            if attempt < self.config.max_retries - 1:
                time.sleep((attempt + 1) * 5)

        self._log("提交文章失败", level="error")
        return False

    def _find_or_create_category(self, title: str, first_image_url: str = None) -> int:
        """查找或创建分类"""
        # 提取分类名
        category_name = self._extract_category_name(title)
        self._log(f"[APIService] 提取分类名: {category_name}")

        if not category_name:
            return self._get_default_category_id()

        # 搜索分类
        category_id = self._search_category(category_name)
        if category_id:
            self._log(f"[APIService] 找到分类: {category_name} -> {category_id}")
            return category_id

        # 创建分类
        self._log(f"[APIService] 分类不存在，尝试创建: {category_name}")
        new_id = self._create_category(category_name, first_image_url)
        if new_id:
            self._log(f"[APIService] 创建分类成功: {category_name} -> {new_id}")
            return new_id

        # 创建失败，使用默认分类
        self._log(f"[APIService] 创建分类失败，使用默认分类", level="warning")
        return self._get_default_category_id()

    def _get_default_category_id(self) -> int:
        """获取默认分类ID（分类列表中的第一个）"""
        try:
            response = self.session.get(
                self.config.category_api,
                params={'page': 0, 'size': 1},
                timeout=self.config.api_timeout
            )

            if response.status_code == 200:
                data = response.json()
                categories = data.get('data', {}).get('data', [])
                if categories:
                    first_id = categories[0].get('id')
                    self._log(f"[APIService] 使用默认分类: {first_id}")
                    return first_id
        except Exception as e:
            self._log(f"[APIService] 获取默认分类失败: {e}", level="warning")

        return 1  # 兜底

    def _extract_category_name(self, title: str) -> str:
        """从标题提取分类名"""
        # 移除统计信息
        name = re.sub(r'\s*\[\d+P(\+\d+V)?\s*-\s*\d+MB\]\s*', ' ', title)

        # 提取方括号中的名字
        match = re.match(r'^\[([^\]]+)\]', name)
        if match:
            return match.group(1).strip()

        # 提取下划线前的部分
        if '_' in name:
            return name.split('_')[0].strip()

        # 移除方括号
        name = re.sub(r'\[[^\]]*\]', '', name)
        return name.strip()

    def _search_category(self, name: str) -> Optional[int]:
        """搜索分类"""
        try:
            self._log(f"[APIService] 搜索分类: {name}")
            response = self.session.get(
                self.config.category_api,
                params={'name': name},
                timeout=self.config.api_timeout
            )

            self._log(f"[APIService] 搜索分类响应: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                categories = data.get('data', {}).get('data', [])
                self._log(f"[APIService] 搜索结果数量: {len(categories)}")
                if categories:
                    return categories[0].get('id')

        except Exception as e:
            self._log(f"[APIService] 搜索分类异常: {e}", level="warning")

        return None

    def _create_category(self, name: str, avatar_url: str = None) -> Optional[int]:
        """创建分类"""
        try:
            self._log(f"[APIService] 创建分类: {name}")
            response = self.session.post(
                self.config.category_api,
                json={
                    'name': name,
                    'avatar': avatar_url or '',
                    'cover': avatar_url or '',
                    'background': avatar_url or '',
                    'description': '',
                    'link': '',
                    'sort': 0,
                    'status': 'ENABLED'
                },
                timeout=self.config.api_timeout
            )

            self._log(f"[APIService] 创建分类响应: {response.status_code}, {response.text[:200]}")
            if response.status_code in [200, 201]:
                data = response.json()
                if data.get('code') in [0, 200, 201]:
                    return data.get('data', {}).get('data', {}).get('id')

        except Exception as e:
            self._log(f"[APIService] 创建分类异常: {e}", level="warning")

        return None

    def fetch_categories(self) -> Optional[Dict]:
        """获取分类列表"""
        try:
            response = self.session.get(
                self.config.category_api,
                timeout=self.config.api_timeout
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('code') in [0, 200]:
                    self._categories_cache = data.get('data', {})
                    return self._categories_cache

        except Exception:
            pass

        return None

    def test_connection(self) -> bool:
        """测试连接"""
        try:
            response = self.session.get(self.config.login_api, timeout=10)
            return response.status_code in [200, 404, 201]
        except Exception:
            return False

    def _natural_sort_key(self, text: str):
        """自然排序键"""
        dirname, filename = os.path.split(text)
        def tryint(s):
            try:
                return int(s)
            except:
                return s
        return [dirname] + [tryint(c) for c in re.split('([0-9]+)', filename)]

    def _log(self, message: str, level: str = "info"):
        """记录日志"""
        if self.logger:
            if level == "error":
                self.logger.error(message)
            elif level == "warning":
                self.logger.warning(message)
            else:
                self.logger.info(message)