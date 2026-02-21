#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
压缩/解压处理模块（重命名以避免与第三方包 `compression` 冲突）
"""

import os
import shutil
import subprocess
import sys
from typing import List, Optional
from logger import Logger
from tools_config import ToolsConfig

# Windows下隐藏控制台窗口的标志
if os.name == 'nt':
    HIDE_WINDOW = subprocess.CREATE_NO_WINDOW
else:
    HIDE_WINDOW = 0


class CompressionHandler:
    """压缩/解压处理类"""

    def __init__(self, logger: Logger, tools_config: ToolsConfig = None):
        self.logger = logger
        self.tools_config = tools_config or ToolsConfig()
        self.seven_zip_path = self.tools_config.seven_zip_path

        if not self.seven_zip_path:
            raise Exception("7-Zip未找到。请将7z.exe放在项目目录或tools目录中，或安装7-Zip到系统。")

    def check_password_required(self, file_path: str) -> bool:
        """检查文件是否需要密码"""
        try:
            cmd = [self.seven_zip_path, 'l', file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30,
                                     creationflags=HIDE_WINDOW)

            self.logger.debug(f"检查密码需求 - 返回码: {result.returncode}")
            if result.stderr:
                self.logger.debug(f"检查密码需求 - 错误输出: {result.stderr}")

            # 检查是否需要密码
            password_keywords = ['enter password', 'wrong password', 'encrypted archive', '需要密码', '密码错误']

            if result.returncode != 0:
                # 如果返回非零，检查错误信息中是否包含密码相关关键词
                if any(keyword in result.stderr.lower() for keyword in password_keywords):
                    self.logger.debug("文件需要密码")
                    return True
                else:
                    self.logger.warning(f"列出文件内容失败，可能需要密码: {result.stderr}")
                    return True
            else:
                # 即使返回成功，也要检查输出中是否有密码提示
                if any(keyword in result.stderr.lower() for keyword in password_keywords):
                    self.logger.debug("文件需要密码")
                    return True
                else:
                    self.logger.debug("文件不需要密码")
                    return False

        except subprocess.TimeoutExpired:
            self.logger.error("检查密码需求超时")
            return True
        except Exception as e:
            self.logger.error(f"检查密码需求异常: {e}")
            return True

    def extract_file(self, file_path: str, dest_dir: str, passwords: List[str],
                    original_name: str = "") -> bool:
        """解压文件"""
        self.logger.info(f"开始解压文件: {os.path.basename(file_path)}")

        # 确保目标目录存在且为空
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir)
        os.makedirs(dest_dir, exist_ok=True)

        # 准备密码列表
        all_passwords = passwords.copy()
        if original_name:
            all_passwords.extend([original_name, os.path.splitext(original_name)[0]])
        all_passwords.extend(["", "123"])  # 包含空密码和常见密码

        # 尝试无密码解压
        try:
            cmd = [self.seven_zip_path, 'x', file_path, f'-o{dest_dir}', '-y']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                                     creationflags=HIDE_WINDOW)  # 2分钟超时，给大文件足够时间
            self.logger.debug(f"7z命令: {' '.join(cmd)}")
            self.logger.debug(f"返回码: {result.returncode}")

            if result.returncode == 0:
                # 检查解压结果
                extracted_files = []
                for root, dirs, files in os.walk(dest_dir):
                    extracted_files.extend([os.path.join(root, f) for f in files])

                if extracted_files:
                    self.logger.info(f"无密码解压成功，解压了 {len(extracted_files)} 个文件")
                    return True
                else:
                    self.logger.warning("解压完成但未找到文件")
            else:
                # 无密码解压失败，立即尝试密码（有密码文件会立即失败）
                self.logger.debug(f"无密码解压失败，返回码: {result.returncode}")
                if result.stderr:
                    # 检查是否是密码相关错误
                    stderr_lower = result.stderr.lower()
                    if 'wrong password' in stderr_lower or 'password required' in stderr_lower:
                        self.logger.debug("检测到需要密码，开始尝试密码解压")
                    else:
                        self.logger.debug(f"其他错误: {result.stderr}")

        except subprocess.TimeoutExpired:
            # 真正的超时情况，可能是非常大的文件或系统问题
            self.logger.warning("无密码解压超时，可能是大文件或系统问题，尝试密码解压")
        except Exception as e:
            self.logger.debug(f"无密码解压异常: {e}")
            # 继续尝试密码解压

        # 尝试各种密码
        for password in all_passwords:
            self.logger.debug(f"尝试密码: {password[:3]}***")
            try:
                # 清空目标目录
                for item in os.listdir(dest_dir):
                    item_path = os.path.join(dest_dir, item)
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)

                cmd = [self.seven_zip_path, 'x', file_path, f'-o{dest_dir}', f'-p{password}', '-y']
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60,
                                         creationflags=HIDE_WINDOW)

                self.logger.debug(f"7z命令: {' '.join(cmd)}")
                self.logger.debug(f"返回码: {result.returncode}")
                if result.stdout:
                    self.logger.debug(f"标准输出: {result.stdout[:500]}...")  # 限制输出长度
                if result.stderr:
                    self.logger.debug(f"错误输出: {result.stderr[:500]}...")  # 限制输出长度

                if result.returncode == 0:
                    # 检查解压结果
                    extracted_files = []
                    for root, dirs, files in os.walk(dest_dir):
                        extracted_files.extend([os.path.join(root, f) for f in files])

                    if extracted_files:
                        self.logger.info(f"密码 '{password[:3]}***' 解压成功，解压了 {len(extracted_files)} 个文件")
                        return True
                    else:
                        self.logger.warning(f"密码 '{password[:3]}***' 解压完成但未找到文件")
                else:
                    self.logger.debug(f"密码 '{password[:3]}***' 解压失败，返回码: {result.returncode}")
                    if result.stderr and ('wrong password' in result.stderr.lower() or 'password required' in result.stderr.lower()):
                        self.logger.debug(f"密码错误提示: {result.stderr[:100]}")
            except subprocess.TimeoutExpired:
                self.logger.debug(f"密码 '{password[:3]}***' 解压超时，尝试下一个密码")
                continue  # 直接进入下一个密码
            except Exception as e:
                self.logger.debug(f"密码 '{password[:3]}***' 解压异常: {e}")
                continue  # 直接进入下一个密码

        self.logger.error("所有密码尝试均失败")
        return False

    def create_archive(self, source_dir: str, output_file: str, password: str,
                        format_type: str = "7z", compression_level: int = 9,
                        solid_mode: bool = True, dictionary_size: str = "32m") -> bool:
        """创建压缩包（支持zst双层压缩）"""
        try:
            # 如果是zst格式，需要先创建内层压缩包，再用zstd压缩
            if format_type.lower() == 'zst':
                return self._create_zst_archive(source_dir, output_file, password, 
                                               compression_level, solid_mode, dictionary_size)
            
            # 其他格式的正常处理
            return self._create_standard_archive(source_dir, output_file, password,
                                                 format_type, compression_level, 
                                                 solid_mode, dictionary_size)
        except Exception as e:
            self.logger.error(f"打包过程中出错: {e}")
            return False

    def _create_zst_archive(self, source_dir: str, output_file: str, password: str,
                           compression_level: int = 9, solid_mode: bool = True, 
                           dictionary_size: str = "32m") -> bool:
        """创建zst格式压缩包（双层压缩：内层7z，外层zst）"""
        try:
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_file), exist_ok=True)

            # 步骤1: 先创建内层7z压缩包
            base_name = os.path.splitext(output_file)[0]
            inner_7z_file = f"{base_name}.7z"
            
            self.logger.info(f"创建内层7z压缩包: {os.path.basename(inner_7z_file)}")
            
            # 创建7z压缩包
            if not self._create_standard_archive(source_dir, inner_7z_file, password,
                                                 "7z", compression_level, 
                                                 solid_mode, dictionary_size):
                self.logger.error("创建内层7z压缩包失败")
                return False

            # 步骤2: 用zstd压缩7z文件
            self.logger.info(f"使用zstd压缩: {os.path.basename(inner_7z_file)}")
            
            # 使用7-Zip的zstd支持（7-Zip 21.07+支持zstd）
            cmd = [self.seven_zip_path, 'a', '-tzstd', 
                   f'-mx={compression_level}', output_file, inner_7z_file]
            
            self.logger.debug(f"zstd压缩命令: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300,
                                   creationflags=HIDE_WINDOW)

            # 检查是否成功
            if result.returncode == 0 and os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                self.logger.info(f"zst打包成功: {os.path.basename(output_file)}")
                
                # 删除临时的内层7z文件
                try:
                    os.remove(inner_7z_file)
                    self.logger.debug(f"已删除临时文件: {os.path.basename(inner_7z_file)}")
                except Exception as e:
                    self.logger.warning(f"删除临时文件失败: {e}")
                
                return True
            else:
                self.logger.error(f"zst打包失败: {result.stderr}")
                # 清理临时文件
                if os.path.exists(inner_7z_file):
                    try:
                        os.remove(inner_7z_file)
                    except:
                        pass
                return False

        except Exception as e:
            self.logger.error(f"创建zst压缩包时出错: {e}")
            return False

    def _create_standard_archive(self, source_dir: str, output_file: str, password: str,
                                 format_type: str = "7z", compression_level: int = 9,
                                 solid_mode: bool = True, dictionary_size: str = "32m") -> bool:
        """创建标准格式压缩包（7z, zip等）"""
        try:
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_file), exist_ok=True)

            # 构建压缩命令
            cmd = [self.seven_zip_path, 'a', f'-t{format_type}']

            # 根据格式设置不同的压缩方法
            if format_type.lower() == '7z':
                cmd.extend(['-m0=lzma2', f'-mx={compression_level}',
                           f'-md={dictionary_size}'])
                if solid_mode:
                    cmd.append('-ms=on')
                cmd.append(f'-mfb={min(64, max(32, compression_level * 8))}')
            elif format_type.lower() == 'zip':
                cmd.extend(['-m0=deflate', f'-mx={compression_level}'])

            # 添加密码和文件参数
            if password:
                cmd.append(f'-p{password}')
            cmd.extend([output_file, f'{source_dir}{os.sep}*'])

            self.logger.debug(f"压缩命令: {' '.join(cmd)}")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300,
                             creationflags=HIDE_WINDOW)

            if result.returncode == 0 and os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                self.logger.info(f"打包成功: {os.path.basename(output_file)} (格式: {format_type}, 压缩级别: {compression_level})")
                return True
            else:
                self.logger.error(f"打包失败: {result.stderr}")
                return False
        except Exception as e:
            self.logger.error(f"打包过程中出错: {e}")
            return False

    def get_archive_info(self, file_path: str) -> Optional[dict]:
        """获取压缩包信息"""
        try:
            cmd = [self.seven_zip_path, 'l', file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30,
                             creationflags=HIDE_WINDOW)

            if result.returncode == 0:
                # 解析输出获取文件信息
                lines = result.stdout.split('\n')
                files = []
                for line in lines:
                    if line.strip() and not line.startswith('---') and not line.startswith('7-Zip'):
                        parts = line.split()
                        if len(parts) >= 6:
                            # 尝试提取文件名
                            filename = ' '.join(parts[5:])
                            if filename and not filename.startswith('-'):
                                files.append(filename)

                return {
                    'total_files': len(files),
                    'files': files
                }
        except Exception as e:
            self.logger.error(f"获取压缩包信息失败: {e}")

        return None

