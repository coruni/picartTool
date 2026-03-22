#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块
"""

import json
import os
from dataclasses import dataclass, asdict, field
from typing import List, Optional


@dataclass
class Config:
    """应用配置类"""

    # ============ 目录配置 ============
    output_dir: str = ""
    temp_dir: str = ""
    log_dir: str = ""

    # ============ 解压配置 ============
    passwords: List[str] = field(default_factory=lambda: [
        "cosfan.cc", "cosplaytele", "123456", "beidewu",
        "TG:@sifangquan", "telegram@asiansts", "telegram@mtldss",
        "t.me/realmtldss", "Discussion", "https://t.me/douza23333",
        "@MarioBase", "@MroHome"
    ])

    # ============ 重命名配置 ============
    image_prefix: str = "cosfan.cc_"
    video_prefix: str = "video_"

    # ============ 打包配置 ============
    zip_password: str = "cosfan.cc"
    zip_format: str = "7z"  # 7z, zip, zst
    zip_compression_level: int = 9
    zip_solid_mode: bool = True
    zip_dictionary_size: str = "32m"
    zip_word_size: int = 64
    zip_block_size: str = "on"

    # ============ zstd配置 ============
    zstd_compression_level: int = 19
    zstd_long_distance_mode: bool = True
    zstd_ldm_distance: int = 28
    zstd_strategy: str = "default"
    zstd_window_log: int = 27

    # ============ 图片压缩配置 ============
    enable_compression: bool = True  # 是否启用图片压缩
    max_height: int = 1920
    max_width: int = 1080
    quality: int = 80
    image_format: str = "webp"  # webp, avif, jpg, png
    lossless_compression: bool = False
    max_upload_size_mb: int = 10  # 单个图片最大上传大小（MB），超过则强制压缩

    # ============ 上传方式配置 ============
    upload_method: str = "api"  # api, image_host, imgur

    # ============ API配置 ============
    upload_api: str = "https://api.cosfan.cc/api/v1/upload/file"
    article_api: str = "https://api.cosfan.cc/api/v1/article"
    login_api: str = "https://api.cosfan.cc/api/v1/user/login"
    category_api: str = "https://api.cosfan.cc/api/v1/category"
    access_token: str = ""
    upload_batch_size: int = 20

    # ============ 登录配置 ============
    login_account: str = ""
    login_password: str = ""
    device_id: str = "fixed_device_id_12345"
    skip_login: bool = False

    # ============ 系统配置 ============
    max_retries: int = 3
    extraction_timeout: int = 60
    api_timeout: int = 120
    cleanup_retention_days: int = 7

    # ============ 文件处理配置 ============
    delete_source_files: bool = False
    delete_compressed_images: bool = True
    enable_upload: bool = True
    enable_publish: bool = True

    # ============ AI配置 ============
    ai_enabled: bool = False
    ai_api_endpoint: str = "https://api.openai.com/v1"
    ai_api_key: str = ""
    ai_model: str = "gpt-4o"
    ai_temperature: float = 0.7
    ai_max_tokens: int = 4096

    # ============ 图床配置 ============
    image_host_enabled: bool = False  # 是否启用图床上传
    image_host_api: str = ""  # 图床API地址，如 http://mysite.com/api/1/upload
    image_host_key: str = ""  # 图床API Key

    # ============ Imgur配置 ============
    imgur_client_id: str = ""  # Imgur Client ID

    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'Config':
        """从字典创建"""
        # 过滤掉不存在的字段
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_file: str = None):
        # 获取配置文件的绝对路径，确保无论从哪个目录运行都能找到
        if config_file is None:
            # 获取当前文件所在目录的父目录（项目根目录）
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.config_file = os.path.join(project_root, "config.json")
        else:
            # 如果传入的是相对路径，转换为绝对路径
            if not os.path.isabs(config_file):
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                self.config_file = os.path.join(project_root, config_file)
            else:
                self.config_file = config_file
        self.config = Config()

    def load_config(self) -> Config:
        """加载配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.config = Config.from_dict(data)
            except Exception as e:
                print(f"加载配置失败: {e}")
        return self.config

    def save_config(self) -> bool:
        """保存配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config.to_dict(), f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False

    def save_config_with_config(self, config: Config) -> bool:
        """保存指定的配置对象"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config.to_dict(), f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False

    def update_config(self, **kwargs) -> Config:
        """更新配置"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        return self.config

    def create_default_directories(self) -> None:
        """创建默认目录"""
        if self.config.output_dir:
            base_dir = self.config.output_dir
            self.config.temp_dir = os.path.join(base_dir, "temp")
            self.config.log_dir = os.path.join(base_dir, "logs")

            for dir_path in [self.config.output_dir, self.config.temp_dir, self.config.log_dir]:
                os.makedirs(dir_path, exist_ok=True)

            self.save_config()

    def get_temp_dir(self) -> str:
        """获取临时目录"""
        if not self.config.temp_dir:
            self.config.temp_dir = os.path.join(self.config.output_dir, "temp")
        os.makedirs(self.config.temp_dir, exist_ok=True)
        return self.config.temp_dir

    def get_log_dir(self) -> str:
        """获取日志目录"""
        if not self.config.log_dir:
            self.config.log_dir = os.path.join(self.config.output_dir, "logs")
        os.makedirs(self.config.log_dir, exist_ok=True)
        return self.config.log_dir

    def validate(self) -> List[str]:
        """验证配置"""
        errors = []

        if not self.config.output_dir:
            errors.append("输出目录未设置")

        if self.config.enable_upload and not self.config.skip_login:
            if not self.config.login_account:
                errors.append("登录账号未设置")
            if not self.config.login_password:
                errors.append("登录密码未设置")

        if self.config.ai_enabled:
            if not self.config.ai_api_key:
                errors.append("AI API Key 未设置")

        return errors