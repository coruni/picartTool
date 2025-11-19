#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具模块
"""

import os
import re
import time
from pathlib import Path
from typing import List


class FileNameCleaner:
    """文件名清理类"""

    @staticmethod
    def clean_filename(filename: str) -> str:
        """清理文件名中的特殊标记"""

        # 1. 移除开头的序号（如"40_咬一口兔娘_"、"01 - "、"123-文件名"等）
        filename = re.sub(r'^\d+[_\s-]+', '', filename)

        # 2. 删除#标记内容（从开头到结尾的#之间的所有内容）
        if filename.startswith('#') and '#' in filename[1:]:
            filename = filename[1:].split('#')[0]

        # 3. 移除P数、V数（包括"P"单独出现的情况）
        filename = re.sub(r'\d+P\d*V?', '', filename)
        filename = re.sub(r'P\d+', '', filename)

        # 4. 移除文件大小信息（各种格式）
        size_patterns = [
            r'\d+(?:\.\d+)?\s*(?:KB|MB|GB|TB)\b',  # 1.5MB, 1024KB等
            r'\d+(?:\.\d+)?\s*[MGT]?B\b',        # 500MB, 1.2GB等
            r'_\d+[MGT]?B_?',                   # _500MB_等
            r'^\d+[MGT]?B\b',                    # 开头的500MB等
        ]
        for pattern in size_patterns:
            filename = re.sub(pattern, '', filename, flags=re.IGNORECASE)

        # 5. 移除方括号内容（包括各种类型的括号）
        bracket_patterns = [
            r'\[[^\]]*\]',      # []
            r'【[^】]*】',      # 【】
            r'「[^」]*」',      # 「」
            r'『[^』]*』',      # 『』
            # 注意：保留()与（）中的标注
        ]
        for pattern in bracket_patterns:
            filename = re.sub(pattern, '', filename)

        # 6. 移除数字和下划线组合（如"数字_XX"格式）
        filename = re.sub(r'\d+_[A-Za-z0-9\u4e00-\u9fff]+', '', filename)

        # 7. 移除特殊符号，保留中文、英文、数字、基本符号
        filename = re.sub(r'[^\w\s\u4e00-\u9fff\-\(\)\[\]（）【】「」『』]', '', filename)

        # 8. 清理多余空格和符号
        filename = re.sub(r'\s+', ' ', filename)        # 多个空格替换为一个
        filename = re.sub(r'[-_\s]+$', '', filename)       # 移除末尾的连字符、下划线、空格
        filename = filename.strip()                    # 移除首尾空格

        # 确保文件名不为空
        if not filename:
            filename = f"unnamed_{int(time.time())}"

        return filename


def is_archive_file(file_path: str) -> bool:
    """检查是否为压缩文件"""
    archive_extensions = {'.7z', '.zip', '.rar', '.tar', '.gz', '.bz2'}
    return Path(file_path).suffix.lower() in archive_extensions


def get_file_size(file_path: str) -> int:
    """获取文件大小（字节）"""
    try:
        return os.path.getsize(file_path)
    except OSError:
        return 0


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
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
    """等待文件稳定（大小不再变化）"""
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
            # 文件大小稳定，再等待一次确认
            time.sleep(check_interval)
            final_size = get_file_size(file_path)
            return final_size == current_size

        last_size = current_size

    return False