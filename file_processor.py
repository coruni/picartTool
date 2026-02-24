#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件处理核心模块
"""

import os
import re
import shutil
import time
import threading
from pathlib import Path
from typing import Optional, Callable

from config import Config
from logger import Logger
from utils import FileNameCleaner
from compression_handler import CompressionHandler
from image_processor import ImageProcessor
from api_handler import APIHandler
from tools_config import ToolsConfig


class FileProcessor:
    """文件处理主类"""

    def __init__(self, config: Config, logger: Logger, status_callback: Optional[Callable] = None):
        self.config = config
        self.logger = logger
        self.status_callback = status_callback

        # 初始化工具配置
        self.tools_config = ToolsConfig()

        # 初始化各个处理模块
        self.compression_handler = CompressionHandler(logger, self.tools_config)
        self.image_processor = ImageProcessor(logger, config, self.tools_config)
        self.api_handler = APIHandler(logger, config)
        self.filename_cleaner = FileNameCleaner()

        # 临时目录列表，用于清理
        self.temp_dirs_to_cleanup = []

    def update_status(self, message: str):
        """更新状态信息"""
        if self.status_callback:
            self.status_callback(message)
        self.logger.info(message)

    def process_file(self, file_path: str) -> bool:
        """处理单个文件或文件夹"""
        self.update_status(f"开始处理: {os.path.basename(file_path)}")

        # 检查是否跳过登录
        if self.config.skip_login:
            self.logger.info("已跳过登录，将不执行任何API操作")
        else:
            # 确保登录并获取分类信息
            if not self.api_handler.ensure_login():
                self.logger.error("登录失败，无法继续处理")
                return False
            
            # 预先获取分类信息（用于后续匹配）
            self.api_handler.fetch_categories()

        # 判断是文件夹还是压缩文件
        if os.path.isdir(file_path):
            return self.process_folder(file_path)
        else:
            return self.process_archive(file_path)

    def process_folder(self, folder_path: str) -> bool:
        """处理文件夹（直接打包）"""
        self.update_status(f"开始处理文件夹: {os.path.basename(folder_path)}")

        # 验证文件夹
        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            self.logger.error(f"文件夹不存在: {folder_path}")
            return False

        # 获取文件夹名称
        folder_name = os.path.basename(folder_path)
        original_name = folder_name

        # 创建临时处理目录
        temp_process_dir = os.path.join(self.config.temp_dir, f"process_{int(time.time())}_{os.getpid()}")
        os.makedirs(temp_process_dir, exist_ok=True)
        self.temp_dirs_to_cleanup.append(temp_process_dir)
        self._add_cleanup_marker(temp_process_dir)

        try:
            # 清理文件名
            clean_name = self.filename_cleaner.clean_filename(original_name)
            processed_dir = os.path.join(temp_process_dir, clean_name)
            
            # 复制文件夹内容到处理目录
            shutil.copytree(folder_path, processed_dir)

            # 清理不需要的文件
            self._clean_unwanted_files(processed_dir)

            # 重命名文件
            self._rename_files(processed_dir)

            # 准备标题信息
            formatted_title = self._format_title_with_stats(processed_dir, clean_name)

            # 步骤1: 创建最终压缩包
            self.update_status("正在创建最终压缩包...")
            safe_title = self._make_safe_filename(formatted_title)
            
            # 根据格式生成正确的文件扩展名
            if self.config.zip_format.lower() == 'zst':
                zip_extension = ".7z.zst"  # zst格式使用双扩展名
            else:
                zip_extension = f".{self.config.zip_format}"
            
            zip_name = os.path.join(self.config.output_dir, f"{safe_title}{zip_extension}")
            os.makedirs(self.config.output_dir, exist_ok=True)

            self.logger.info(f"创建压缩包: {zip_name} (格式: {self.config.zip_format}, 级别: {self.config.zip_compression_level})")
            if not self.compression_handler.create_archive(
                processed_dir, zip_name, self.config.zip_password,
                self.config.zip_format, self.config.zip_compression_level,
                self.config.zip_solid_mode, self.config.zip_dictionary_size
            ):
                self.logger.error("创建最终压缩包失败")
                return False

            self.update_status(f"压缩包已创建: {os.path.basename(zip_name)}")

            # 步骤2: 压缩图片
            self.update_status("正在压缩图片...")
            self.image_processor.compress_images(processed_dir)

            # 根据配置决定是否上传（跳过登录时不上传）
            if self.config.skip_login:
                self.update_status("已跳过登录，不执行API操作")
                self.logger.info("跳过登录模式，不执行上传和发布操作")
            elif self.config.enable_upload:
                # 步骤3: 上传文件
                self.update_status("正在上传文件...")
                uploaded_urls = self.api_handler.upload_files(processed_dir)
                if not uploaded_urls:
                    self.logger.error("上传失败")
                    return False

                # 根据配置决定是否发布文章
                if self.config.enable_publish:
                    # 步骤4: 提交文章
                    self.update_status("正在发布文章...")
                    if not self.api_handler.submit_article(formatted_title, uploaded_urls, uploaded_urls[0], True):
                        self.logger.error("文章发布失败")
                        return False
                else:
                    self.update_status("已跳过发布文章（发布功能已禁用）")
                    self.logger.info("发布功能已禁用，跳过文章发布步骤")
            else:
                self.update_status("已跳过上传（上传功能已禁用）")
                self.logger.info("上传功能已禁用，跳过上传步骤")

            # 根据配置决定是否删除压缩后的图片
            if self.config.delete_compressed_images:
                self.update_status("正在清理压缩后的图片...")
                self._cleanup_compressed_images(processed_dir)
            else:
                # 将压缩后的图片移动到输出目录
                self.update_status("正在保存压缩后的图片...")
                self._save_compressed_images(processed_dir, clean_name)

            self.update_status(f"文件夹处理成功: {os.path.basename(folder_path)}")
            return True

        except Exception as e:
            self.logger.error(f"处理文件夹时出错: {e}")
            return False
        finally:
            # 清理所有跟踪的临时目录
            self.cleanup_temp_directories()

    def process_archive(self, file_path: str) -> bool:
        """处理压缩文件"""
        # 验证文件
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            self.logger.error(f"文件不存在或为空: {file_path}")
            return False

        # 获取原始文件名
        original_name = os.path.splitext(os.path.basename(file_path))[0]

        # 创建临时解压目录
        temp_extract_dir = os.path.join(self.config.temp_dir, f"extract_{int(time.time())}_{os.getpid()}")
        os.makedirs(temp_extract_dir, exist_ok=True)
        self.temp_dirs_to_cleanup.append(temp_extract_dir)
        self._add_cleanup_marker(temp_extract_dir)

        try:
            # 解压文件
            if not self.compression_handler.extract_file(
                file_path, temp_extract_dir, self.config.passwords, original_name
            ):
                self.logger.error(f"解压失败: {os.path.basename(file_path)}")
                return False

            # 处理解压后的文件
            processed_dir = self._process_extracted_files(temp_extract_dir, original_name)
            if not processed_dir:
                self.logger.error("文件处理失败")
                return False

            # 准备标题信息
            clean_name = self.filename_cleaner.clean_filename(original_name)
            formatted_title = self._format_title_with_stats(processed_dir, clean_name)

            # 步骤1: 创建最终压缩包（按process.sh顺序，打包在压缩图片之前）
            self.update_status("正在创建最终压缩包...")
            safe_title = self._make_safe_filename(formatted_title)
            
            # 根据格式生成正确的文件扩展名
            if self.config.zip_format.lower() == 'zst':
                zip_extension = ".7z.zst"  # zst格式使用双扩展名
            else:
                zip_extension = f".{self.config.zip_format}"
            
            zip_name = os.path.join(self.config.output_dir, f"{safe_title}{zip_extension}")
            os.makedirs(self.config.output_dir, exist_ok=True)

            self.logger.info(f"创建压缩包: {zip_name} (格式: {self.config.zip_format}, 级别: {self.config.zip_compression_level})")
            if not self.compression_handler.create_archive(
                processed_dir, zip_name, self.config.zip_password,
                self.config.zip_format, self.config.zip_compression_level,
                self.config.zip_solid_mode, self.config.zip_dictionary_size
            ):
                self.logger.error("创建最终压缩包失败")
                return False

            self.update_status(f"压缩包已创建: {os.path.basename(zip_name)}")

            # 步骤2: 压缩图片（在已打包的目录中进行压缩）
            self.update_status("正在压缩图片...")
            self.image_processor.compress_images(processed_dir)

            # 根据配置决定是否上传（跳过登录时不上传）
            if self.config.skip_login:
                self.update_status("已跳过登录，不执行API操作")
                self.logger.info("跳过登录模式，不执行上传和发布操作")
            elif self.config.enable_upload:
                # 步骤3: 上传文件
                self.update_status("正在上传文件...")
                uploaded_urls = self.api_handler.upload_files(processed_dir)
                if not uploaded_urls:
                    self.logger.error("上传失败")
                    return False

                # 根据配置决定是否发布文章
                if self.config.enable_publish:
                    # 步骤4: 提交文章
                    self.update_status("正在发布文章...")
                    if not self.api_handler.submit_article(formatted_title, uploaded_urls, uploaded_urls[0], True):
                        self.logger.error("文章发布失败")
                        return False
                else:
                    self.update_status("已跳过发布文章（发布功能已禁用）")
                    self.logger.info("发布功能已禁用，跳过文章发布步骤")
            else:
                self.update_status("已跳过上传（上传功能已禁用）")
                self.logger.info("上传功能已禁用，跳过上传步骤")

            # 根据配置决定是否删除压缩后的图片
            if self.config.delete_compressed_images:
                self.update_status("正在清理压缩后的图片...")
                self._cleanup_compressed_images(processed_dir)
            else:
                # 将压缩后的图片移动到输出目录
                self.update_status("正在保存压缩后的图片...")
                self._save_compressed_images(processed_dir, clean_name)

            # 根据配置决定是否删除原始文件
            if self.config.delete_source_files:
                try:
                    os.remove(file_path)
                    self.update_status(f"删除原始文件: {os.path.basename(file_path)}")
                    self.logger.info(f"已删除原始文件: {os.path.basename(file_path)}")
                except Exception as e:
                    self.logger.warning(f"删除原始文件失败: {e}")
            else:
                self.update_status(f"保留原始文件: {os.path.basename(file_path)}")
                self.logger.info(f"保留原始文件: {os.path.basename(file_path)}")

            self.update_status(f"文件处理流程成功: {os.path.basename(file_path)}")
            return True

        except Exception as e:
            self.logger.error(f"处理文件时出错: {e}")
            return False
        finally:
            # 清理所有跟踪的临时目录
            self.cleanup_temp_directories()

    def _process_extracted_files(self, temp_dir: str, original_name: str) -> Optional[str]:
        """处理解压后的文件"""
        # 检查解压内容
        if not os.path.exists(temp_dir):
            self.logger.error("解压目录不存在")
            return None

        content_items = os.listdir(temp_dir)
        if not content_items:
            self.logger.error("解压后没有找到任何文件")
            return None

        # 创建最终处理目录
        clean_name = self.filename_cleaner.clean_filename(original_name)
        final_dir = os.path.join(self.config.temp_dir, f"final_{int(time.time())}_{os.getpid()}")
        processed_dir = os.path.join(final_dir, clean_name)
        os.makedirs(processed_dir, exist_ok=True)
        self.temp_dirs_to_cleanup.append(final_dir)
        self._add_cleanup_marker(final_dir)

        # 处理解压结构
        if len(content_items) == 1:
            # 单一文件或目录
            item = os.path.join(temp_dir, content_items[0])
            if os.path.isdir(item):
                # 移动子目录内容
                for subitem in os.listdir(item):
                    shutil.move(os.path.join(item, subitem), processed_dir)
            else:
                # 移动单一文件
                shutil.move(item, processed_dir)
        else:
            # 多个文件/目录
            for item in content_items:
                item_path = os.path.join(temp_dir, item)
                if os.path.isdir(item_path):
                    shutil.move(item_path, processed_dir)
                else:
                    shutil.move(item_path, processed_dir)

        # 清理不需要的文件
        self._clean_unwanted_files(processed_dir)

        # 重命名文件
        self._rename_files(processed_dir)

        return processed_dir

    def _clean_unwanted_files(self, directory: str):
        """清理不需要的文件"""
        unwanted_extensions = {'.html', '.htm', '.txt', '.url', '.lnk', '.nfo', '.diz'}
        unwanted_names = {'ewm', 'thumbs.db', '.ds_store'}

        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                if (Path(file).suffix.lower() in unwanted_extensions or
                    file.lower().startswith('ewm') or
                    file.lower() in unwanted_names):
                    try:
                        os.remove(file_path)
                        self.logger.debug(f"删除不需要的文件: {file}")
                    except Exception:
                        pass

    def _natural_sort_key(self, text: str) -> List:
        """自然排序键函数，确保数字按数值排序而不是字符串排序"""
        def tryint(s):
            try:
                return int(s)
            except:
                return s
        return [tryint(c) for c in re.split('([0-9]+)', text)]

    def _rename_files(self, directory: str):
        """重命名文件（包含GIF文件，使用自然排序）"""
        img_count = 1
        video_count = 1

        image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.gif'}  # 包含gif
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.3gp', '.m4v'}

        # 收集所有文件，使用自然排序
        all_files = []

        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                all_files.append(file_path)

        # 使用自然排序（包含GIF文件）
        all_files.sort(key=self._natural_sort_key)

        for file_path in all_files:
            file = os.path.basename(file_path)
            ext = Path(file).suffix.lower()

            new_name = None
            if ext in image_extensions:
                if ext == '.gif':
                    # GIF文件也按图片序列重命名
                    new_name = f"{self.config.image_prefix}{img_count:03d}{ext}"
                    self.logger.debug(f"重命名GIF文件: {file} -> {new_name}")
                else:
                    new_name = f"{self.config.image_prefix}{img_count:03d}{ext}"
                img_count += 1
            elif ext in video_extensions:
                new_name = f"{self.config.video_prefix}{video_count:03d}{ext}"
                video_count += 1

            if new_name and new_name != file:
                new_path = os.path.join(os.path.dirname(file_path), new_name)
                try:
                    shutil.move(file_path, new_path)
                    self.logger.debug(f"重命名文件: {file} -> {new_name}")
                except Exception as e:
                    self.logger.warning(f"重命名失败: {file} -> {new_name}, 错误: {e}")

    def _format_title_with_stats(self, directory: str, base_title: str) -> str:
        """格式化标题，添加文件统计信息"""
        try:
            # 统计图片和视频数量
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'}
            video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.3gp', '.m4v'}

            image_count = 0
            video_count = 0
            total_size = 0

            for root, dirs, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    if os.path.exists(file_path):
                        ext = Path(file).suffix.lower()
                        file_size = os.path.getsize(file_path)
                        total_size += file_size

                        if ext in image_extensions:
                            image_count += 1
                        elif ext in video_extensions:
                            video_count += 1

            # 转换大小为MB，并取整
            total_mb = int(total_size / (1024 * 1024))

            # 构建统计信息
            if video_count > 0:
                stats = f"[{image_count}P+{video_count}V - {total_mb}MB]"
            else:
                stats = f"[{image_count}P - {total_mb}MB]"

            # 组合标题
            formatted_title = f"{base_title} {stats}"
            self.logger.info(f"格式化标题: {formatted_title}")

            return formatted_title

        except Exception as e:
            self.logger.warning(f"格式化标题失败，使用原标题: {e}")
            return base_title

    def _make_safe_filename(self, filename: str) -> str:
        """创建安全的文件名，只替换真正不安全的字符"""
        try:
            # 只替换文件系统真正不安全的字符，保留空格和基本符号
            unsafe_chars = {
                '<': '_',
                '>': '_',
                ':': '_',
                '"': '_',
                '|': '_',
                '?': '_',
                '*': '_',
                '/': '_',
                '\\': '_'
            }

            safe_name = filename
            for char, replacement in unsafe_chars.items():
                safe_name = safe_name.replace(char, replacement)

            # 限制文件名长度（避免过长）
            if len(safe_name) > 150:  # 增加长度限制以容纳统计信息
                safe_name = safe_name[:150]

            self.logger.debug(f"安全文件名: {filename} -> {safe_name}")
            return safe_name

        except Exception as e:
            self.logger.warning(f"创建安全文件名失败: {e}")
            return "unnamed_file"

    def cleanup_temp_directories(self):
        """清理所有临时目录（包含强化的异常处理）"""
        cleaned_count = 0
        failed_count = 0
        skipped_count = 0
        retry_count = 0

        # 使用set去重，避免重复清理
        unique_dirs = list(set(self.temp_dirs_to_cleanup))

        self.logger.info(f"开始清理 {len(unique_dirs)} 个临时目录")

        for temp_dir in unique_dirs:
            if not os.path.exists(temp_dir):
                self.logger.debug(f"临时目录不存在，跳过: {os.path.basename(temp_dir)}")
                skipped_count += 1
                continue

            # 尝试多种清理方法
            cleanup_success = self._try_cleanup_directory(temp_dir)

            if cleanup_success:
                cleaned_count += 1
                self.logger.debug(f"成功清理临时目录: {os.path.basename(temp_dir)}")
            else:
                failed_count += 1
                self.logger.warning(f"临时目录清理失败: {os.path.basename(temp_dir)}")

        # 记录清理结果
        if cleaned_count > 0:
            self.logger.info(f"已清理 {cleaned_count} 个临时目录")
        if failed_count > 0:
            self.logger.warning(f"有 {failed_count} 个临时目录清理失败")
            self._schedule_background_cleanup(unique_dirs)
        if skipped_count > 0:
            self.logger.debug(f"跳过 {skipped_count} 个不存在的临时目录")

        # 清空跟踪列表
        self.temp_dirs_to_cleanup.clear()

    def _try_cleanup_directory(self, temp_dir: str) -> bool:
        """尝试多种方法清理目录"""
        cleanup_methods = [
            self._cleanup_direct_rmtree,
            self._cleanup_recursive_delete,
            self._cleanup_file_by_file,
            self._cleanup_force_delete,
        ]

        for i, method in enumerate(cleanup_methods, 1):
            try:
                self.logger.debug(f"尝试清理方法 {i}: {method.__name__}")
                if method(temp_dir):
                    return True
            except Exception as e:
                self.logger.debug(f"清理方法 {i} 失败: {e}")
                continue

        return False

    def _cleanup_direct_rmtree(self, temp_dir: str) -> bool:
        """使用shutil.rmtree清理"""
        try:
            shutil.rmtree(temp_dir)
            return not os.path.exists(temp_dir)
        except Exception:
            return False

    def _cleanup_recursive_delete(self, temp_dir: str) -> bool:
        """递归删除文件和目录"""
        try:
            for root, dirs, files in os.walk(temp_dir, topdown=False):
                # 先删除文件
                for name in files:
                    file_path = os.path.join(root, name)
                    try:
                        os.chmod(file_path, 0o777)  # 修改权限
                        os.remove(file_path)
                    except:
                        pass

                # 再删除目录
                for name in dirs:
                    dir_path = os.path.join(root, name)
                    try:
                        os.chmod(dir_path, 0o777)  # 修改权限
                        os.rmdir(dir_path)
                    except:
                        pass

            # 最后删除根目录
            os.chmod(temp_dir, 0o777)
            os.rmdir(temp_dir)
            return not os.path.exists(temp_dir)
        except Exception:
            return False

    def _cleanup_file_by_file(self, temp_dir: str) -> bool:
        """逐个文件删除"""
        try:
            for root, dirs, files in os.walk(temp_dir, topdown=True):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        os.remove(file_path)
                    except:
                        pass
            return True
        except Exception:
            return False

    def _cleanup_force_delete(self, temp_dir: str) -> bool:
        """强制删除（Windows专用）"""
        if os.name != 'nt':
            return False

        try:
            import subprocess
            # 使用Windows命令强制删除
            result = subprocess.run(
                ['cmd', '/c', 'rd', '/s', '/q', temp_dir],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return result.returncode == 0
        except Exception:
            return False

    def _schedule_background_cleanup(self, failed_dirs):
        """安排后台清理任务"""
        try:
            import threading
            import time

            def background_cleanup():
                """后台清理线程"""
                self.logger.info("启动后台清理任务...")
                time.sleep(2)  # 等待主程序完成

                for temp_dir in failed_dirs:
                    if os.path.exists(temp_dir):
                        self.logger.debug(f"后台清理: {os.path.basename(temp_dir)}")
                        try:
                            self._try_cleanup_directory(temp_dir)
                        except Exception as e:
                            self.logger.warning(f"后台清理失败: {e}")

                self.logger.info("后台清理任务完成")

            # 启动后台线程
            cleanup_thread = threading.Thread(target=background_cleanup, daemon=True)
            cleanup_thread.start()

        except Exception as e:
            self.logger.error(f"启动后台清理失败: {e}")

    def _add_cleanup_marker(self, directory: str):
        """添加清理标记文件"""
        try:
            marker_file = os.path.join(directory, '.cleanup_marker')
            with open(marker_file, 'w', encoding='utf-8') as f:
                f.write(f"临时目录，可安全删除\n创建时间: {time.ctime()}\n")
        except Exception:
            pass

    def _cleanup_compressed_images(self, directory: str):
        """清理压缩后的图片"""
        try:
            image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff'}
            deleted_count = 0
            
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if Path(file).suffix.lower() in image_extensions:
                        file_path = os.path.join(root, file)
                        try:
                            os.remove(file_path)
                            deleted_count += 1
                        except Exception as e:
                            self.logger.warning(f"删除压缩图片失败: {file}, 错误: {e}")
            
            if deleted_count > 0:
                self.logger.info(f"已删除 {deleted_count} 张压缩后的图片")
        except Exception as e:
            self.logger.error(f"清理压缩图片时出错: {e}")

    def _save_compressed_images(self, source_dir: str, base_name: str):
        """保存压缩后的图片到输出目录"""
        try:
            # 创建压缩图片保存目录
            compressed_images_dir = os.path.join(self.config.output_dir, f"{base_name}_compressed")
            os.makedirs(compressed_images_dir, exist_ok=True)
            
            # 包含所有可能的压缩格式
            image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.avif'}
            saved_count = 0
            
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    if Path(file).suffix.lower() in image_extensions:
                        src_path = os.path.join(root, file)
                        dst_path = os.path.join(compressed_images_dir, file)
                        try:
                            shutil.copy2(src_path, dst_path)
                            saved_count += 1
                            self.logger.debug(f"已保存压缩图片: {file}")
                        except Exception as e:
                            self.logger.warning(f"保存压缩图片失败: {file}, 错误: {e}")
            
            if saved_count > 0:
                self.logger.info(f"已保存 {saved_count} 张压缩后的图片到: {compressed_images_dir}")
                self.update_status(f"压缩图片已保存到: {os.path.basename(compressed_images_dir)}")
            else:
                self.logger.warning(f"没有找到压缩图片可保存（目录: {source_dir}）")
        except Exception as e:
            self.logger.error(f"保存压缩图片时出错: {e}")

    def validate_file(self, file_path: str) -> bool:
        """验证文件是否可以处理"""
        if not os.path.exists(file_path):
            return False

        if os.path.getsize(file_path) == 0:
            return False

        # 检查是否为压缩文件
        archive_extensions = {'.7z', '.zip', '.rar', '.tar', '.gz', '.bz2'}
        return Path(file_path).suffix.lower() in archive_extensions

    def get_file_info(self, file_path: str) -> dict:
        """获取文件信息"""
        try:
            stat = os.stat(file_path)
            return {
                'name': os.path.basename(file_path),
                'size': stat.st_size,
                'modified': stat.st_mtime,
                'is_archive': self.validate_file(file_path)
            }
        except Exception:
            return {
                'name': os.path.basename(file_path),
                'size': 0,
                'modified': 0,
                'is_archive': False
            }