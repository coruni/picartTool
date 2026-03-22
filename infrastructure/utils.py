#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具函数模块
"""

import os
import re
import time
from pathlib import Path
from typing import List, Optional


class FileNameCleaner:
    """文件名清理类"""

    # 压缩文件扩展名
    ARCHIVE_EXTENSIONS = {'.7z', '.zip', '.rar', '.tar', '.gz', '.bz2', '.zst'}

    @staticmethod
    def clean_filename(filename: str) -> str:
        """
        清理文件名中的特殊标记

        Args:
            filename: 原始文件名

        Returns:
            清理后的文件名
        """
        # 1. 移除开头的序号
        filename = re.sub(r'^\d+[_\s-]+', '', filename)
        filename = re.sub(r'^No\.\d+[_\s-]+', '', filename, flags=re.IGNORECASE)
        filename = re.sub(r'^No_\d+[_\s-]+', '', filename, flags=re.IGNORECASE)

        # 2. 删除#标记内容
        if filename.startswith('#') and '#' in filename[1:]:
            filename = filename[1:].split('#')[0]

        # 3. 移除P数、V数
        filename = re.sub(r'\d+P\d*_\d+_\d+_MB', '', filename)
        filename = re.sub(r'\d+P\d*_?\d+_MB', '', filename)
        filename = re.sub(r'\d+P\d*V?', '', filename)
        filename = re.sub(r'P\d+', '', filename)

        # 4. 移除文件大小信息
        size_patterns = [
            r'\d+(?:\.\d+)?\s*(?:KB|MB|GB|TB)\b',
            r'\d+(?:\.\d+)?\s*[MGT]?B\b',
            r'_\d+[MGT]?B_?',
            r'^\d+[MGT]?B\b',
            r'_\d+_\d+_MB_?',
        ]
        for pattern in size_patterns:
            filename = re.sub(pattern, '', filename, flags=re.IGNORECASE)

        # 5. 移除方括号内容
        bracket_patterns = [
            r'\[[^\]]*\]',
            r'【[^】]*】',
            r'「[^」]*」',
            r'『[^』]*』',
        ]
        for pattern in bracket_patterns:
            filename = re.sub(pattern, '', filename)

        # 6. 移除数字和下划线组合
        filename = re.sub(r'\d+_[A-Za-z0-9\u4e00-\u9fff]+', '', filename)
        filename = re.sub(r'_\d+[a-zA-Z]*$', '', filename)
        filename = re.sub(r'_\d+$', '', filename)

        # 7. 移除特殊符号
        filename = re.sub(r'[^\w\s\u4e00-\u9fff\-\(\)\[\]（）【】「」『』]', '', filename)

        # 8. 清理多余空格和符号
        filename = re.sub(r'\s+', ' ', filename)
        filename = re.sub(r'_+', ' ', filename)
        filename = re.sub(r'[-\s]+$', '', filename)
        filename = filename.strip()

        # 9. 移除压缩文件扩展名
        for ext in FileNameCleaner.ARCHIVE_EXTENSIONS:
            if filename.lower().endswith(ext):
                filename = filename[:-len(ext)]
                break

        # 确保文件名不为空
        if not filename:
            filename = f"unnamed_{int(time.time())}"

        return filename

    @staticmethod
    def make_safe_filename(filename: str, max_length: int = 150) -> str:
        """
        创建安全的文件名

        Args:
            filename: 原始文件名
            max_length: 最大长度

        Returns:
            安全的文件名
        """
        # 替换不安全字符
        unsafe_chars = {
            '<': '_', '>': '_', ':': '_',
            '"': '_', '|': '_', '?': '_',
            '*': '_', '/': '_', '\\': '_'
        }

        safe_name = filename
        for char, replacement in unsafe_chars.items():
            safe_name = safe_name.replace(char, replacement)

        # 限制长度
        if len(safe_name) > max_length:
            safe_name = safe_name[:max_length]

        return safe_name


def is_archive_file(file_path: str) -> bool:
    """
    检查是否为压缩文件

    Args:
        file_path: 文件路径

    Returns:
        是否为压缩文件
    """
    ext = Path(file_path).suffix.lower()
    return ext in FileNameCleaner.ARCHIVE_EXTENSIONS


def get_file_size(file_path: str) -> int:
    """
    获取文件大小（字节）

    Args:
        file_path: 文件路径

    Returns:
        文件大小
    """
    try:
        return os.path.getsize(file_path)
    except OSError:
        return 0


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小

    Args:
        size_bytes: 字节数

    Returns:
        格式化后的字符串
    """
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)

    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1

    return f"{size:.1f} {size_names[i]}"


def wait_for_file_stable(file_path: str, max_wait: int = 60) -> bool:
    """
    等待文件稳定（大小不再变化）

    Args:
        file_path: 文件路径
        max_wait: 最大等待时间（秒）

    Returns:
        文件是否稳定
    """
    if not os.path.exists(file_path):
        return False

    last_size = get_file_size(file_path)
    waited = 0
    check_interval = 2

    while waited < max_wait:
        time.sleep(check_interval)
        waited += check_interval

        if not os.path.exists(file_path):
            return False

        current_size = get_file_size(file_path)
        if current_size == last_size and current_size > 0:
            time.sleep(check_interval)
            final_size = get_file_size(file_path)
            return final_size == current_size

        last_size = current_size

    return False


def natural_sort_key(text: str) -> List:
    """
    自然排序键函数

    Args:
        text: 文本

    Returns:
        排序键
    """
    def tryint(s):
        try:
            return int(s)
        except:
            return s
    return [tryint(c) for c in re.split('([0-9]+)', text)]


def ensure_directory(path: str) -> str:
    """
    确保目录存在

    Args:
        path: 目录路径

    Returns:
        目录路径
    """
    os.makedirs(path, exist_ok=True)
    return path