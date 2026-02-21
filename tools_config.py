#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具配置模块 - 管理7z和FFmpeg路径
"""

import os
import shutil
from pathlib import Path


class ToolsConfig:
    """工具配置管理类"""

    def __init__(self):
        # 项目目录中的工具路径（优先级最高）
        self.project_dir = Path(__file__).parent.absolute()
        self.project_tools_dir = self.project_dir / "tools"

        # 默认工具名称和目录结构
        self.seven_zip_name = "7z.exe" if os.name == 'nt' else "7z"
        self.ffmpeg_name = "ffmpeg.exe" if os.name == 'nt' else "ffmpeg"

        # 工具路径
        self.seven_zip_path = None
        self.ffmpeg_path = None

        # 自动查找工具
        self.find_tools()

    def find_tools(self):
        """查找7z和FFmpeg"""
        self.seven_zip_path = self.find_7zip()
        self.ffmpeg_path = self.find_ffmpeg()

        return {
            '7zip': self.seven_zip_path,
            'ffmpeg': self.ffmpeg_path
        }

    def find_7zip(self):
        """查找7-Zip，优先使用项目目录中的版本"""
        # 1. 优先检查 tools/7z/7z.exe (你的目录结构)
        seven_zip_dir = self.project_tools_dir / "7z"
        seven_zip_exe = seven_zip_dir / self.seven_zip_name
        if seven_zip_exe.exists():
            return str(seven_zip_exe)

        # 2. 检查项目tools目录
        project_7z = self.project_tools_dir / self.seven_zip_name
        if project_7z.exists():
            return str(project_7z)

        # 3. 检查项目根目录
        root_7z = self.project_dir / self.seven_zip_name
        if root_7z.exists():
            return str(root_7z)

        # 4. 检查系统PATH
        system_7z = shutil.which(self.seven_zip_name)
        if system_7z:
            return system_7z

        # 5. 检查Windows常见安装路径
        if os.name == 'nt':
            common_paths = [
                r"C:\Program Files\7-Zip\7z.exe",
                r"C:\Program Files (x86)\7-Zip\7z.exe",
            ]
            for path in common_paths:
                if os.path.exists(path):
                    return path

        return None

    def find_ffmpeg(self):
        """查找FFmpeg，优先使用项目目录中的版本"""
        # 1. 优先检查 tools/ffmpeg/bin/ffmpeg.exe (标准目录结构)
        ffmpeg_dir = self.project_tools_dir / "ffmpeg" / "bin"
        ffmpeg_exe = ffmpeg_dir / self.ffmpeg_name
        if ffmpeg_exe.exists():
            return str(ffmpeg_exe)

        # 2. 检查 tools/ffmpeg/ffmpeg.exe (直接放在ffmpeg目录)
        ffmpeg_in_dir = self.project_tools_dir / "ffmpeg" / self.ffmpeg_name
        if ffmpeg_in_dir.exists():
            return str(ffmpeg_in_dir)

        # 3. 检查项目tools目录
        project_ffmpeg = self.project_tools_dir / self.ffmpeg_name
        if project_ffmpeg.exists():
            return str(project_ffmpeg)

        # 4. 检查项目根目录
        root_ffmpeg = self.project_dir / self.ffmpeg_name
        if root_ffmpeg.exists():
            return str(root_ffmpeg)

        # 5. 检查系统PATH
        system_ffmpeg = shutil.which(self.ffmpeg_name)
        if system_ffmpeg:
            return system_ffmpeg

        # 6. 检查Windows常见安装路径
        if os.name == 'nt':
            common_paths = [
                r"C:\Program Files\FFmpeg\bin\ffmpeg.exe",
                r"C:\Program Files (x86)\FFmpeg\bin\ffmpeg.exe",
                r"C:\ffmpeg\bin\ffmpeg.exe",
            ]
            for path in common_paths:
                if os.path.exists(path):
                    return path

        return None

    def set_custom_7zip_path(self, path: str):
        """手动设置7-Zip路径"""
        if os.path.exists(path):
            self.seven_zip_path = path
            return True
        return False

    def set_custom_ffmpeg_path(self, path: str):
        """手动设置FFmpeg路径"""
        if os.path.exists(path):
            self.ffmpeg_path = path
            return True
        return False

    def create_tools_directory(self):
        """创建tools目录和说明文件"""
        tools_dir = self.project_tools_dir
        tools_dir.mkdir(exist_ok=True)

        # 创建说明文件
        readme_content = """工具目录说明
============

可以将以下工具文件放置在此目录：

1. FFmpeg (Windows) - 必需
   放置位置（任选其一）：
   - tools/ffmpeg/bin/ffmpeg.exe （推荐）
   - tools/ffmpeg/ffmpeg.exe
   - tools/ffmpeg.exe
   下载地址：https://ffmpeg.org/download.html
   或使用：https://github.com/BtbN/FFmpeg-Builds/releases

2. 7-Zip (Windows) - 必需
   放置位置（任选其一）：
   - tools/7z/7z.exe
   - tools/7z.exe
   下载地址：https://www.7-zip.org/download.html

3. Linux/Mac用户
   - FFmpeg: sudo apt install ffmpeg 或 brew install ffmpeg
   - 7-Zip: sudo apt install p7zip-full 或 brew install p7zip

注意：
- 下载FFmpeg后，将bin目录下的ffmpeg.exe复制到上述任一位置
- 放置在此目录的工具会优先被使用
- 也可以将工具安装到系统PATH中
"""

        readme_path = tools_dir / "README.txt"
        if not readme_path.exists():
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(readme_content)

        return str(tools_dir)

    def get_tool_status(self):
        """获取工具状态信息"""
        # 检测操作系统类型
        is_windows = os.name == 'nt'
        is_linux = os.name == 'posix'
        
        # 根据操作系统设置建议位置
        if is_windows:
            seven_zip_locations = [
                f"{self.project_tools_dir}/7z/7z.exe",
                f"{self.project_tools_dir}/7z.exe",
                f"{self.project_dir}/7z.exe",
                r"C:\Program Files\7-Zip\7z.exe"
            ]
            ffmpeg_locations = [
                f"{self.project_tools_dir}/ffmpeg/bin/ffmpeg.exe",
                f"{self.project_tools_dir}/ffmpeg.exe",
                f"{self.project_dir}/ffmpeg.exe",
                r"C:\Program Files\FFmpeg\bin\ffmpeg.exe"
            ]
        elif is_linux:
            seven_zip_locations = [
                f"{self.project_tools_dir}/7z/7z",
                f"{self.project_tools_dir}/7z",
                f"{self.project_dir}/7z",
                "/usr/bin/7z"
            ]
            ffmpeg_locations = [
                f"{self.project_tools_dir}/ffmpeg/bin/ffmpeg",
                f"{self.project_tools_dir}/ffmpeg",
                f"{self.project_dir}/ffmpeg",
                "/usr/bin/ffmpeg"
            ]
        else:
            # 默认位置
            seven_zip_locations = [
                f"{self.project_tools_dir}/7z/7z",
                f"{self.project_tools_dir}/7z",
                f"{self.project_dir}/7z"
            ]
            ffmpeg_locations = [
                f"{self.project_tools_dir}/ffmpeg/bin/ffmpeg",
                f"{self.project_tools_dir}/ffmpeg",
                f"{self.project_dir}/ffmpeg"
            ]
        
        status = {
            '7zip': {
                'found': self.seven_zip_path is not None,
                'path': self.seven_zip_path or "未找到",
                'suggested_locations': seven_zip_locations
            },
            'ffmpeg': {
                'found': self.ffmpeg_path is not None,
                'path': self.ffmpeg_path or "未找到",
                'suggested_locations': ffmpeg_locations
            }
        }

        return status