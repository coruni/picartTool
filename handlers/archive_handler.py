#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
压缩包处理器 - 处理压缩文件的解压和创建
"""

import os
import shutil
import subprocess
from typing import List, Optional

from .tool_locator import ToolLocator


# Windows下隐藏控制台窗口的标志
if os.name == 'nt':
    HIDE_WINDOW = subprocess.CREATE_NO_WINDOW
else:
    HIDE_WINDOW = 0


class ArchiveHandler:
    """
    压缩包处理器

    负责压缩文件的解压和创建
    """

    def __init__(self, tool_locator: ToolLocator = None, logger=None):
        self.tool_locator = tool_locator or ToolLocator()
        self.logger = logger

        # 查找7-Zip
        self.seven_zip_path = self.tool_locator.find_7zip()
        if not self.seven_zip_path:
            raise RuntimeError("7-Zip未找到")

    def extract_file(self, file_path: str, dest_dir: str,
                     passwords: List[str] = None,
                     original_name: str = "",
                     timeout: int = 120) -> bool:
        """
        解压文件

        Args:
            file_path: 压缩文件路径
            dest_dir: 目标目录
            passwords: 密码列表
            original_name: 原始文件名（用于猜测密码）
            timeout: 超时时间（秒）

        Returns:
            是否成功
        """
        self._log(f"开始解压: {os.path.basename(file_path)}")

        # 确保目标目录存在
        os.makedirs(dest_dir, exist_ok=True)

        # 准备密码列表
        all_passwords = list(passwords or [])
        if original_name:
            all_passwords.extend([
                original_name,
                os.path.splitext(original_name)[0]
            ])
        all_passwords.extend(["", "123"])  # 空密码和常见密码

        # 先尝试无密码解压
        if self._try_extract(file_path, dest_dir, "", timeout):
            return True

        # 尝试各个密码
        for password in all_passwords:
            if self._try_extract(file_path, dest_dir, password, timeout):
                self._log(f"密码解压成功")
                return True

        self._log("所有密码尝试均失败", level="error")
        return False

    def _try_extract(self, file_path: str, dest_dir: str, password: str, timeout: int = 120) -> bool:
        """尝试解压"""
        try:
            cmd = [self.seven_zip_path, 'x', file_path, f'-o{dest_dir}', '-y']
            if password:
                cmd.append(f'-p{password}')

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                creationflags=HIDE_WINDOW
            )

            if result.returncode == 0:
                # 检查是否有文件
                for root, dirs, files in os.walk(dest_dir):
                    if files:
                        return True

            return False

        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False

    def create_archive(self, source_dir: str, output_file: str,
                       password: str = "",
                       format_type: str = "7z",
                       compression_level: int = 9,
                       solid_mode: bool = True,
                       dictionary_size: str = "32m",
                       **kwargs) -> bool:
        """
        创建压缩包

        Args:
            source_dir: 源目录
            output_file: 输出文件路径
            password: 密码
            format_type: 格式类型 (7z, zip, zst)
            compression_level: 压缩级别 (0-9)
            solid_mode: 固实模式
            dictionary_size: 字典大小
            **kwargs: 其他参数

        Returns:
            是否成功
        """
        self._log(f"创建压缩包: {os.path.basename(output_file)}")

        # zst格式需要特殊处理
        if format_type.lower() == 'zst':
            return self._create_zst_archive(
                source_dir, output_file, password,
                compression_level, solid_mode, dictionary_size,
                **kwargs
            )

        return self._create_standard_archive(
            source_dir, output_file, password,
            format_type, compression_level, solid_mode, dictionary_size
        )

    def _create_standard_archive(self, source_dir: str, output_file: str,
                                  password: str, format_type: str,
                                  compression_level: int,
                                  solid_mode: bool,
                                  dictionary_size: str) -> bool:
        """创建标准格式压缩包"""
        try:
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_file), exist_ok=True)

            cmd = [self.seven_zip_path, 'a', f'-t{format_type}']

            # 根据格式设置参数
            if format_type.lower() == '7z':
                cmd.extend([
                    '-m0=lzma2',
                    f'-mx={compression_level}',
                    f'-md={dictionary_size}'
                ])
                if solid_mode:
                    cmd.append('-ms=on')
            elif format_type.lower() == 'zip':
                cmd.extend([
                    '-m0=deflate',
                    f'-mx={compression_level}'
                ])

            # 密码
            if password:
                cmd.append(f'-p{password}')

            cmd.extend([output_file, f'{source_dir}{os.sep}*'])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                creationflags=HIDE_WINDOW
            )

            return (result.returncode == 0 and
                    os.path.exists(output_file) and
                    os.path.getsize(output_file) > 0)

        except Exception as e:
            self._log(f"创建压缩包失败: {e}", level="error")
            return False

    def _create_zst_archive(self, source_dir: str, output_file: str,
                            password: str, compression_level: int,
                            solid_mode: bool, dictionary_size: str,
                            zstd_level: int = 19, **kwargs) -> bool:
        """创建zst格式压缩包（双层压缩）"""
        try:
            # 内层7z文件
            if output_file.lower().endswith('.zst'):
                inner_7z = output_file[:-4]
            else:
                inner_7z = os.path.splitext(output_file)[0] + ".7z"

            # 创建内层7z
            if not self._create_standard_archive(
                source_dir, inner_7z, password,
                "7z", compression_level, solid_mode, dictionary_size
            ):
                return False

            # 外层zstd压缩
            cmd = [
                self.seven_zip_path, 'a', '-tzstd',
                f'-mx={zstd_level}',
                '-mmt=on',
                output_file, inner_7z
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                creationflags=HIDE_WINDOW
            )

            # 清理临时文件
            if os.path.exists(inner_7z):
                os.remove(inner_7z)

            return (result.returncode == 0 and
                    os.path.exists(output_file) and
                    os.path.getsize(output_file) > 0)

        except Exception as e:
            self._log(f"创建zst压缩包失败: {e}", level="error")
            return False

    def get_archive_info(self, file_path: str) -> Optional[dict]:
        """获取压缩包信息"""
        try:
            cmd = [self.seven_zip_path, 'l', file_path]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=HIDE_WINDOW
            )

            if result.returncode == 0:
                # 解析文件列表
                lines = result.stdout.split('\n')
                files = []
                for line in lines:
                    if line.strip() and not line.startswith('---'):
                        parts = line.split()
                        if len(parts) >= 6:
                            files.append(' '.join(parts[5:]))

                return {'total_files': len(files), 'files': files}

        except Exception:
            pass

        return None

    def _log(self, message: str, level: str = "info"):
        """记录日志"""
        if self.logger:
            if level == "error":
                self.logger.error(message)
            else:
                self.logger.info(message)