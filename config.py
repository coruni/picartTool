#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块
"""

import json
import os
from dataclasses import dataclass, asdict
from typing import List


@dataclass
class Config:
    """应用配置类"""
    # 目录配置
    output_dir: str = ""  # 输出目录
    temp_dir: str = ""
    log_dir: str = ""

    # 解压配置
    passwords: List[str] = None

    # 重命名配置
    image_prefix: str = "cosfan.cc_"
    video_prefix: str = "video_"

    # 打包配置
    zip_password: str = "cosfan.cc"
    zip_format: str = "7z"  # 压缩格式：7z, zip, zst (zst为双层压缩：内层7z+外层zstd)
    zip_compression_level: int = 9  # 压缩级别：0-9
    zip_solid_mode: bool = True  # 固实压缩模式
    zip_dictionary_size: str = "32m"  # 字典大小
    zip_word_size: int = 64  # 词大小
    zip_block_size: str = "on"  # 块大小

    # 图片压缩配置
    max_height: int = 1920
    max_width: int = 1080
    quality: int = 80
    image_format: str = "webp"  # 图片压缩格式：webp, avif

    # API配置
    upload_api: str = "https://api.cosfan.cc/api/v1/upload/file"
    article_api: str = "https://api.cosfan.cc/api/v1/article"
    login_api: str = "https://api.cosfan.cc/api/v1/user/login"
    category_api: str = "https://api.cosfan.cc/api/v1/category"
    access_token: str = ""
    upload_batch_size: int = 40

    # 登录配置
    login_account: str = "maplene"
    login_password: str = "Sakura010422"
    device_id: str = "fixed_device_id_12345"
    skip_login: bool = False  # 是否跳过登录（跳过后不执行任何API操作）

    # 系统配置
    max_retries: int = 3
    extraction_timeout: int = 60

    # 文件处理配置
    delete_source_files: bool = False  # 是否在压缩完成后删除源文件
    delete_compressed_images: bool = True  # 是否删除压缩后的图片
    enable_upload: bool = True  # 是否启用上传功能
    enable_publish: bool = True  # 是否发布文章（设为False则只上传不创建文章）
    api_timeout: int = 120
    cleanup_retention_days: int = 7

    def __post_init__(self):
        if self.passwords is None:
            self.passwords = [
                "cosfan.cc", "cosplaytele", "123456", "beidewu",
                "TG:@sifangquan", "telegram@asiansts", "telegram@mtldss",
                "t.me/realmtldss", "Discussion", "https://t.me/douza23333",
                "@MarioBase", "@MroHome"
            ]


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = Config()

    def load_config(self) -> Config:
        """加载配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 更新配置
                for key, value in data.items():
                    if hasattr(self.config, key):
                        setattr(self.config, key, value)

                # 如果有token，确保session headers也设置
                if self.config.access_token and hasattr(self, '_update_session_token'):
                    self._update_session_token(self.config.access_token)

            except Exception as e:
                print(f"加载配置失败: {e}")

        return self.config

    def save_config(self) -> bool:
        """保存配置"""
        try:
            # 转换为字典，过滤掉空值
            config_dict = asdict(self.config)

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, ensure_ascii=False, indent=2)

            return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False

    def create_default_directories(self):
        """创建默认目录"""
        if self.config.output_dir:
            base_dir = self.config.output_dir
            self.config.temp_dir = os.path.join(base_dir, "temp")
            self.config.log_dir = os.path.join(base_dir, "logs")

            # 创建目录
            for dir_path in [self.config.output_dir, self.config.temp_dir, self.config.log_dir]:
                os.makedirs(dir_path, exist_ok=True)

            self.save_config()