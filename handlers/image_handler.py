#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片处理器 - 处理图片压缩
"""

import os
import subprocess
from pathlib import Path
from typing import Tuple, Set

from .tool_locator import ToolLocator


# Windows下隐藏控制台窗口的标志
if os.name == 'nt':
    HIDE_WINDOW = subprocess.CREATE_NO_WINDOW
else:
    HIDE_WINDOW = 0


class ImageHandler:
    """
    图片处理器

    负责图片压缩和格式转换
    """

    # 支持的图片格式
    SUPPORTED_EXTENSIONS: Set[str] = {
        '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.heic', '.heif', '.webp'
    }

    # GIF格式（跳过）
    GIF_EXTENSIONS: Set[str] = {'.gif'}

    def __init__(self, tool_locator: ToolLocator = None, logger=None):
        self.tool_locator = tool_locator or ToolLocator()
        self.logger = logger

        # 查找FFmpeg
        self.ffmpeg_path = self.tool_locator.find_ffmpeg()
        if not self.ffmpeg_path:
            raise RuntimeError("FFmpeg未找到")

    def compress_images(self, directory: str,
                        max_width: int = 1080,
                        max_height: int = 1920,
                        quality: int = 80,
                        output_format: str = "webp",
                        lossless: bool = False,
                        timeout: int = 120,
                        max_size_mb: int = 10) -> Tuple[int, int, int]:
        """
        压缩目录中的图片

        Args:
            directory: 目录路径
            max_width: 最大宽度
            max_height: 最大高度
            quality: 质量 (0-100)
            output_format: 输出格式 (webp, avif)
            lossless: 是否无损压缩
            timeout: 超时时间（秒）
            max_size_mb: 单个图片最大大小（MB），超过会进一步降低质量

        Returns:
            (成功数量, 失败数量, 超大文件数量)
        """
        # 收集要处理的文件
        files_to_process = []
        skipped_gifs = []

        for root, dirs, files in os.walk(directory):
            for file in files:
                ext = Path(file).suffix.lower()
                file_path = os.path.join(root, file)

                if ext in self.GIF_EXTENSIONS:
                    skipped_gifs.append(file_path)
                elif ext in self.SUPPORTED_EXTENSIONS:
                    files_to_process.append(file_path)

        if skipped_gifs:
            self._log(f"跳过 {len(skipped_gifs)} 个GIF文件")

        if not files_to_process:
            self._log("没有找到需要压缩的图片")
            return 0, 0, 0

        self._log(f"找到 {len(files_to_process)} 张图片需要压缩")

        max_size_bytes = max_size_mb * 1024 * 1024
        compressed_count = 0
        failed_count = 0
        oversized_count = 0

        for img_path in files_to_process:
            try:
                result = self._compress_single_image(
                    img_path, max_width, max_height,
                    quality, output_format, lossless, timeout, max_size_bytes
                )
                if result == 'success':
                    compressed_count += 1
                elif result == 'oversized':
                    compressed_count += 1
                    oversized_count += 1
                    self._log(f"图片压缩后仍较大: {os.path.basename(img_path)}", level="warning")
                else:
                    failed_count += 1
            except Exception as e:
                self._log(f"压缩失败: {os.path.basename(img_path)} - {e}", level="warning")
                failed_count += 1

        self._log(f"图片压缩完成: 成功 {compressed_count}，失败 {failed_count}，超大 {oversized_count}")
        return compressed_count, failed_count, oversized_count

    def _compress_single_image(self, img_path: str,
                                max_width: int, max_height: int,
                                quality: int, output_format: str,
                                lossless: bool, timeout: int = 120,
                                max_size_bytes: int = None) -> str:
        """
        压缩单张图片

        Returns:
            'success' - 成功
            'oversized' - 成功但超过大小限制
            'failed' - 失败
        """
        # 生成新文件名
        new_path = os.path.splitext(img_path)[0] + f'.{output_format}'

        # 如果输入输出路径相同（同格式压缩），需要使用临时文件
        same_format = (img_path.lower() == new_path.lower())
        if same_format:
            temp_path = os.path.splitext(img_path)[0] + f'_temp.{output_format}'
        else:
            temp_path = new_path

        # 尝试压缩，如果超过大小限制则逐步降低质量
        current_quality = quality
        min_quality = 20  # 最低质量

        self._log(f"开始压缩: {os.path.basename(img_path)} -> {os.path.basename(temp_path)}")

        while True:
            result = self._do_compress(
                img_path, temp_path, max_width, max_height,
                current_quality, output_format, lossless, timeout
            )

            if not result:
                # 压缩失败
                self._log(f"压缩失败: {os.path.basename(img_path)}", level="warning")
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except:
                        pass
                return 'failed'

            # 检查文件是否存在
            if not os.path.exists(temp_path):
                self._log(f"压缩后文件不存在: {temp_path}", level="warning")
                return 'failed'

            # 检查文件大小
            if max_size_bytes is None:
                break

            compressed_size = os.path.getsize(temp_path)
            if compressed_size <= max_size_bytes:
                break

            # 超过大小限制，降低质量重试
            if current_quality <= min_quality:
                # 已经是最低质量，记录为超大文件
                self._log(f"图片 {os.path.basename(img_path)} 压缩后 {compressed_size / (1024*1024):.2f}MB 仍超过限制")
                break

            current_quality -= 20
            self._log(f"图片过大，降低质量到 {current_quality} 重试: {os.path.basename(img_path)}")

        # 删除原文件（带重试机制）
        if self._delete_file_with_retry(img_path):
            if same_format:
                # 同格式：重命名临时文件
                try:
                    os.rename(temp_path, new_path)
                except Exception as e:
                    self._log(f"重命名文件失败: {temp_path} -> {new_path}, {e}", level="warning")

            # 检查最终大小
            final_size = os.path.getsize(new_path)
            self._log(f"压缩完成: {os.path.basename(new_path)} ({final_size / 1024:.1f}KB)")
            if max_size_bytes and final_size > max_size_bytes:
                return 'oversized'
            return 'success'
        else:
            # 删除原文件失败，但保留压缩后的文件
            self._log(f"警告：无法删除原文件，但压缩文件已保留: {os.path.basename(new_path)}", level="warning")

            # 如果是同格式，需要重命名临时文件
            if same_format:
                try:
                    os.rename(temp_path, new_path)
                except Exception as e:
                    self._log(f"重命名文件失败: {temp_path} -> {new_path}, {e}", level="warning")

            # 检查压缩后的文件是否存在
            if os.path.exists(new_path):
                final_size = os.path.getsize(new_path)
                self._log(f"压缩文件已就绪: {os.path.basename(new_path)} ({final_size / 1024:.1f}KB)")
                return 'success'

            return 'failed'

    def _do_compress(self, img_path: str, output_path: str,
                     max_width: int, max_height: int,
                     quality: int, output_format: str,
                     lossless: bool, timeout: int) -> bool:
        """执行实际的压缩操作"""
        # 构建FFmpeg命令
        cmd = [
            self.ffmpeg_path,
            '-i', img_path,
            '-vf', f"scale='min({max_width},iw)':'min({max_height},ih)':force_original_aspect_ratio=decrease"
        ]

        # 根据格式添加参数
        if output_format == 'webp':
            if lossless:
                cmd.extend(['-lossless', '1', '-compression_level', '6'])
            else:
                cmd.extend(['-q:v', str(quality), '-compression_level', '6'])

        elif output_format == 'avif':
            crf = int((100 - quality) * 63 / 100)
            cmd.extend([
                '-c:v', 'libaom-av1',
                '-crf', str(crf),
                '-cpu-used', '8',
                '-row-mt', '1'
            ])

        elif output_format == 'jpg' or output_format == 'jpeg':
            cmd.extend([
                '-q:v', str(min(31, int((100 - quality) * 31 / 100))),
                '-huffman', 'optimal'
            ])

        elif output_format == 'png':
            cmd.extend([
                '-pred', 'mixed',
                '-compression_level', '9'
            ])

        cmd.extend(['-y', output_path])

        # 执行命令 - 使用二进制模式避免编码问题
        self._log(f"执行FFmpeg: {' '.join(cmd[:5])}... 输出: {os.path.basename(output_path)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout,
            creationflags=HIDE_WINDOW
        )

        if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            self._log(f"FFmpeg执行成功: {os.path.basename(output_path)}")
            return True
        else:
            # 打印错误信息
            error_msg = result.stderr.decode('utf-8', errors='ignore')[:500] if result.stderr else '无错误信息'
            self._log(f"FFmpeg执行失败 (返回码={result.returncode}): {error_msg}", level="warning")
            return False

    def _delete_file_with_retry(self, file_path: str, max_retries: int = 5) -> bool:
        """删除文件（带重试机制）"""
        import time
        import gc
        import stat

        for i in range(max_retries):
            try:
                # 强制垃圾回收，释放可能的文件句柄
                gc.collect()

                # 检查文件是否存在
                if not os.path.exists(file_path):
                    return True

                # 尝试修改文件属性为可写
                try:
                    os.chmod(file_path, stat.S_IWRITE | stat.S_IREAD)
                except:
                    pass

                os.remove(file_path)
                return True

            except PermissionError as e:
                if i < max_retries - 1:
                    wait_time = 0.5 * (i + 1)  # 递增等待时间
                    self._log(f"文件被占用，等待重试 ({i+1}/{max_retries}): {os.path.basename(file_path)}")
                    time.sleep(wait_time)
                else:
                    # 最后一次尝试：使用 shutil 强制删除
                    try:
                        import shutil
                        shutil.rmtree(file_path, ignore_errors=True)
                        if not os.path.exists(file_path):
                            return True
                    except:
                        pass
                    self._log(f"无法删除文件: {os.path.basename(file_path)}, 错误: {e}", level="warning")

            except FileNotFoundError:
                # 文件已经不存在，视为成功
                return True

            except Exception as e:
                self._log(f"删除文件异常: {file_path}, {e}", level="warning")
                break

        return False

    def get_image_info(self, image_path: str) -> dict:
        """获取图片信息"""
        try:
            import re

            cmd = [self.ffmpeg_path, '-i', image_path]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=HIDE_WINDOW
            )

            output = result.stderr
            info = {
                'width': 0,
                'height': 0,
                'format': '',
                'size': os.path.getsize(image_path) if os.path.exists(image_path) else 0
            }

            # 提取分辨率
            match = re.search(r'(\d+)x(\d+)', output)
            if match:
                info['width'] = int(match.group(1))
                info['height'] = int(match.group(2))

            # 提取格式
            match = re.search(r'Video: (\w+)', output)
            if match:
                info['format'] = match.group(1)

            return info

        except Exception:
            return {'width': 0, 'height': 0, 'format': '', 'size': 0}

    def is_image_file(self, file_path: str) -> bool:
        """检查是否为图片文件"""
        ext = Path(file_path).suffix.lower()
        return ext in self.SUPPORTED_EXTENSIONS or ext in self.GIF_EXTENSIONS

    def _log(self, message: str, level: str = "info"):
        """记录日志"""
        if self.logger:
            if level == "error":
                self.logger.error(message)
            elif level == "warning":
                self.logger.warning(message)
            else:
                self.logger.info(message)