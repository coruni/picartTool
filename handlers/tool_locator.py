#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具定位器 - 查找外部工具路径
"""

import os
import shutil
from pathlib import Path
from typing import Optional, Dict, List


class ToolLocator:
    """
    工具定位器

    负责查找外部工具（7-Zip、FFmpeg）的路径
    """

    def __init__(self, project_dir: str = None):
        self.project_dir = Path(project_dir or os.path.dirname(__file__)).parent
        self.tools_dir = self.project_dir / "tools"

        # 工具名称
        self._7zip_name = "7z.exe" if os.name == 'nt' else "7z"
        self._ffmpeg_name = "ffmpeg.exe" if os.name == 'nt' else "ffmpeg"

        # 缓存
        self._7zip_path: Optional[str] = None
        self._ffmpeg_path: Optional[str] = None

    def find_7zip(self) -> Optional[str]:
        """查找7-Zip路径"""
        if self._7zip_path:
            return self._7zip_path

        search_paths = self._get_7zip_search_paths()

        for path in search_paths:
            if os.path.exists(path):
                self._7zip_path = path
                return path

        return None

    def find_ffmpeg(self) -> Optional[str]:
        """查找FFmpeg路径"""
        if self._ffmpeg_path:
            return self._ffmpeg_path

        search_paths = self._get_ffmpeg_search_paths()

        for path in search_paths:
            if os.path.exists(path):
                self._ffmpeg_path = path
                return path

        return None

    def find_all(self) -> Dict[str, Optional[str]]:
        """查找所有工具"""
        return {
            '7zip': self.find_7zip(),
            'ffmpeg': self.find_ffmpeg()
        }

    def get_status(self) -> Dict[str, Dict]:
        """获取工具状态"""
        return {
            '7zip': {
                'found': self.find_7zip() is not None,
                'path': self.find_7zip() or "未找到",
                'suggested_locations': self._get_7zip_search_paths()[:3]
            },
            'ffmpeg': {
                'found': self.find_ffmpeg() is not None,
                'path': self.find_ffmpeg() or "未找到",
                'suggested_locations': self._get_ffmpeg_search_paths()[:3]
            }
        }

    def _get_7zip_search_paths(self) -> List[str]:
        """获取7-Zip搜索路径"""
        paths = []

        # 项目目录
        paths.append(str(self.tools_dir / "7z" / self._7zip_name))
        paths.append(str(self.tools_dir / self._7zip_name))
        paths.append(str(self.project_dir / self._7zip_name))

        # 系统 PATH
        system_path = shutil.which(self._7zip_name)
        if system_path:
            paths.append(system_path)

        # Windows 安装路径
        if os.name == 'nt':
            paths.extend([
                r"C:\Program Files\7-Zip\7z.exe",
                r"C:\Program Files (x86)\7-Zip\7z.exe",
            ])

        return [p for p in paths if p]

    def _get_ffmpeg_search_paths(self) -> List[str]:
        """获取FFmpeg搜索路径"""
        paths = []

        # 项目目录
        paths.append(str(self.tools_dir / "ffmpeg" / "bin" / self._ffmpeg_name))
        paths.append(str(self.tools_dir / "ffmpeg" / self._ffmpeg_name))
        paths.append(str(self.tools_dir / self._ffmpeg_name))
        paths.append(str(self.project_dir / self._ffmpeg_name))

        # 系统 PATH
        system_path = shutil.which(self._ffmpeg_name)
        if system_path:
            paths.append(system_path)

        # Windows 安装路径
        if os.name == 'nt':
            paths.extend([
                r"C:\Program Files\FFmpeg\bin\ffmpeg.exe",
                r"C:\Program Files (x86)\FFmpeg\bin\ffmpeg.exe",
                r"C:\ffmpeg\bin\ffmpeg.exe",
            ])

        return [p for p in paths if p]

    def set_7zip_path(self, path: str) -> bool:
        """手动设置7-Zip路径"""
        if os.path.exists(path):
            self._7zip_path = path
            return True
        return False

    def set_ffmpeg_path(self, path: str) -> bool:
        """手动设置FFmpeg路径"""
        if os.path.exists(path):
            self._ffmpeg_path = path
            return True
        return False