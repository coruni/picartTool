#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片处理模块
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Tuple
from logger import Logger
from config import Config
from tools_config import ToolsConfig

# Windows下隐藏控制台窗口的标志
if os.name == 'nt':
    HIDE_WINDOW = subprocess.CREATE_NO_WINDOW
else:
    HIDE_WINDOW = 0


class ImageProcessor:
    """图片处理类"""

    def __init__(self, logger: Logger, config: Config, tools_config: ToolsConfig = None):
        self.logger = logger
        self.config = config
        self.tools_config = tools_config or ToolsConfig()
        self.ffmpeg_path = self.tools_config.ffmpeg_path

        if not self.ffmpeg_path:
            raise Exception("FFmpeg未找到。请将ffmpeg.exe放在项目目录或tools目录中，或安装FFmpeg到系统。")

    def compress_images(self, directory: str) -> Tuple[int, int]:
        """压缩目录中的图片（跳过GIF文件）"""
        self.logger.info(f"开始压缩图片（格式：{self.config.image_format}）")

        # 支持的扩展名，但排除GIF（GIF文件将被跳过）
        supported_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.heic', '.heif'}
        gif_extensions = {'.gif'}
        files_to_process = []
        skipped_gifs = []

        for root, dirs, files in os.walk(directory):
            for file in files:
                file_ext = Path(file).suffix.lower()
                file_path = os.path.join(root, file)

                if file_ext in gif_extensions:
                    skipped_gifs.append(file_path)
                    self.logger.debug(f"跳过GIF文件: {file}")
                elif file_ext in supported_extensions:
                    files_to_process.append(file_path)

        if skipped_gifs:
            self.logger.info(f"跳过 {len(skipped_gifs)} 个GIF文件")

        if not files_to_process:
            self.logger.debug("没有找到需要压缩的图片")
            return 0, 0

        total_files = len(files_to_process)
        self.logger.debug(f"找到 {total_files} 个需要压缩的图片（已排除GIF）")

        compressed_count = 0
        failed_count = 0

        for i, img_path in enumerate(files_to_process, 1):
            if not os.path.exists(img_path):
                self.logger.warning(f"文件在处理前消失: {os.path.basename(img_path)}")
                continue

            self.logger.debug(f"正在处理图片 ({i}/{total_files}): {os.path.basename(img_path)}")

            # 根据配置选择格式
            output_format = self.config.image_format.lower()
            if output_format not in ['webp', 'avif']:
                self.logger.warning(f"不支持的格式 {output_format}，使用默认格式 webp")
                output_format = 'webp'

            # 生成新文件名
            new_path = os.path.splitext(img_path)[0] + f'.{output_format}'

            try:
                # 构建FFmpeg命令
                cmd = [
                    self.ffmpeg_path,
                    '-i', img_path,
                    '-vf', f"scale='min({self.config.max_width},iw)':'min({self.config.max_height},ih)':force_original_aspect_ratio=decrease"
                ]

                # 根据格式添加不同的参数
                if output_format == 'webp':
                    cmd.extend([
                        '-q:v', str(self.config.quality),
                        '-compression_level', '6'
                    ])
                elif output_format == 'avif':
                    # AVIF使用crf参数，范围0-63，值越小质量越高
                    # 将quality (0-100) 转换为crf (0-63)
                    crf = int((100 - self.config.quality) * 63 / 100)
                    cmd.extend([
                        '-c:v', 'libaom-av1',
                        '-crf', str(crf),
                        '-cpu-used', '8',  # 速度优先（0-8，8最快）
                        '-row-mt', '1'  # 启用多线程
                    ])

                cmd.extend(['-y', new_path])

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                             creationflags=HIDE_WINDOW)

                if result.returncode == 0 and os.path.exists(new_path) and os.path.getsize(new_path) > 0:
                    os.remove(img_path)
                    compressed_count += 1
                else:
                    self.logger.warning(f"转换后文件异常: {os.path.basename(new_path)}")
                    if os.path.exists(new_path):
                        os.remove(new_path)
                    failed_count += 1
            except subprocess.TimeoutExpired:
                self.logger.error(f"图片压缩超时: {os.path.basename(img_path)}")
                if os.path.exists(new_path):
                    os.remove(new_path)
                failed_count += 1
            except Exception as e:
                self.logger.error(f"图片压缩失败: {os.path.basename(img_path)}, 错误: {e}")
                if os.path.exists(new_path):
                    os.remove(new_path)
                failed_count += 1

        self.logger.info(f"图片压缩完成: 成功 {compressed_count} 张，失败 {failed_count} 张")
        return compressed_count, failed_count

    def get_image_info(self, image_path: str) -> dict:
        """获取图片信息"""
        try:
            cmd = [
                self.ffmpeg_path,
                '-i', image_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            # 解析输出获取图片信息
            output = result.stderr
            info = {
                'width': 0,
                'height': 0,
                'format': '',
                'size': os.path.getsize(image_path) if os.path.exists(image_path) else 0
            }

            # 使用正则表达式提取分辨率
            import re
            match = re.search(r'(\d+)x(\d+)', output)
            if match:
                info['width'] = int(match.group(1))
                info['height'] = int(match.group(2))

            # 提取格式
            match = re.search(r'Video: (\w+)', output)
            if match:
                info['format'] = match.group(1)

            return info
        except Exception as e:
            self.logger.error(f"获取图片信息失败: {e}")
            return {
                'width': 0,
                'height': 0,
                'format': '',
                'size': 0
            }

    def is_image_file(self, file_path: str) -> bool:
        """检查是否为图片文件"""
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.heic', '.heif'}
        return Path(file_path).suffix.lower() in image_extensions