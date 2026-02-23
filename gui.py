#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI界面模块
"""

import os
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import ttk, filedialog, messagebox, scrolledtext
import tkinter.font as tkFont
from tkinterdnd2 import DND_FILES, TkinterDnD

from config import Config, ConfigManager
from logger import Logger
from file_processor import FileProcessor
from utils import is_archive_file, format_file_size
from tools_config import ToolsConfig


class FileProcessorGUI:
    """文件处理GUI界面"""

    def __init__(self):
        self.root = TkinterDnD.Tk()
        self.root.title("文件处理工具 v1.0 - 拖拽压缩包或文件夹处理")
        self.root.geometry("800x600")

        # 设置窗口接收拖拽文件
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.on_file_drop)

        # 配置样式
        self.style = ttk.Style()
        self.style.configure('TButton', padding=6, relief='flat')

        # 初始化配置管理器
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_config()

        # 初始化组件
        self.logger = Logger(self.config.log_dir)
        self.tools_config = ToolsConfig()
        self.file_processor = None
        self.processing_thread = None
        self.dropped_files = []  # 存储拖拽的文件

        # 如果已有token，提前创建file_processor并设置token
        if self.config.access_token:
            try:
                self.file_processor = FileProcessor(self.config, self.logger, self.update_status)
                self.file_processor.api_handler.session.headers['Authorization'] = f'Bearer {self.config.access_token}'
                self.logger.info("已加载保存的token")
            except Exception as e:
                self.logger.warning(f"加载token失败: {e}")

        # 创建tools目录
        self.tools_config.create_tools_directory()

        self.create_widgets()

        # 设置窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        """创建GUI组件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="8")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 配置行列权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        # 标题
        title_font = tkFont.Font(family="Arial", size=14, weight="bold")
        title_label = ttk.Label(main_frame, text="文件处理工具 - 拖拽压缩包或文件夹处理", font=title_font)
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 8))

        # 上部分：文件拖拽和配置区域
        top_frame = ttk.Frame(main_frame)
        top_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 8))
        top_frame.columnconfigure(1, weight=1)

        # 左侧：文件拖拽区域
        left_frame = ttk.Frame(top_frame)
        left_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        left_frame.columnconfigure(0, weight=1)

        drop_frame = ttk.LabelFrame(left_frame, text="拖拽压缩包或文件夹到此区域", padding="12")
        drop_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        drop_frame.columnconfigure(0, weight=1)

        # 拖拽提示标签
        drop_label = ttk.Label(drop_frame, text="将压缩文件或文件夹拖拽到这里",
                              justify=tk.CENTER, font=("Arial", 10))
        drop_label.grid(row=0, column=0, pady=(0, 8))

        # 文件列表（减小高度）
        list_frame = ttk.Frame(drop_frame)
        list_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        columns = ('文件名', '大小', '类型')
        self.file_tree = ttk.Treeview(list_frame, columns=columns, show='tree headings', height=4)
        self.file_tree.heading('#0', text='')
        self.file_tree.heading('文件名', text='文件名')
        self.file_tree.heading('大小', text='大小')
        self.file_tree.heading('类型', text='类型')

        self.file_tree.column('#0', width=0, stretch=False)
        self.file_tree.column('文件名', width=200)
        self.file_tree.column('大小', width=80)
        self.file_tree.column('类型', width=60)

        tree_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.file_tree.yview)
        self.file_tree.configure(yscrollcommand=tree_scroll.set)

        self.file_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # 文件操作按钮
        file_button_frame = ttk.Frame(drop_frame)
        file_button_frame.grid(row=2, column=0, pady=(8, 0))

        ttk.Button(file_button_frame, text="选择文件/文件夹", command=self.select_files).pack(side=tk.LEFT, padx=3)
        ttk.Button(file_button_frame, text="清空", command=self.clear_file_list).pack(side=tk.LEFT, padx=3)
        ttk.Button(file_button_frame, text="移除", command=self.remove_selected).pack(side=tk.LEFT, padx=3)

        # 右侧：配置区域
        right_frame = ttk.Frame(top_frame)
        right_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        right_frame.columnconfigure(1, weight=1)

        config_frame = ttk.LabelFrame(right_frame, text="配置设置", padding="8")
        config_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        config_frame.columnconfigure(1, weight=1)

        row = 0

        # 输出目录
        ttk.Label(config_frame, text="输出目录:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.output_dir_var = tk.StringVar(value=self.config.output_dir)
        output_dir_frame = ttk.Frame(config_frame)
        output_dir_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)
        output_dir_frame.columnconfigure(0, weight=1)

        ttk.Entry(output_dir_frame, textvariable=self.output_dir_var, width=35).grid(row=0, column=0, sticky=(tk.W, tk.E))
        ttk.Button(output_dir_frame, text="浏览", command=self.browse_output_dir).grid(row=0, column=1, padx=(3, 0))

        row += 1

        # 登录信息
        ttk.Label(config_frame, text="登录账号:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.login_account_var = tk.StringVar(value=self.config.login_account)
        ttk.Entry(config_frame, textvariable=self.login_account_var, width=35).grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)

        row += 1

        ttk.Label(config_frame, text="登录密码:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.login_password_var = tk.StringVar(value=self.config.login_password)
        ttk.Entry(config_frame, textvariable=self.login_password_var, show="*", width=35).grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)

        row += 1

        ttk.Label(config_frame, text="设备ID:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.device_id_var = tk.StringVar(value=self.config.device_id)
        ttk.Entry(config_frame, textvariable=self.device_id_var, width=35).grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)

        row += 1

        # 压缩配置分隔线
        ttk.Separator(config_frame, orient='horizontal').grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=8)
        row += 1

        # 压缩配置标题
        ttk.Label(config_frame, text="压缩设置:", font=("Arial", 9, "bold")).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=2)
        row += 1

        # 压缩格式
        ttk.Label(config_frame, text="压缩格式:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.zip_format_var = tk.StringVar(value=self.config.zip_format)
        zip_format_combo = ttk.Combobox(config_frame, textvariable=self.zip_format_var, width=33, state="readonly")
        zip_format_combo['values'] = ('7z', 'zip', 'zst')
        zip_format_combo.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)
        
        # 添加格式说明
        def show_format_info(event):
            selected = self.zip_format_var.get()
            if selected == 'zst':
                self.update_status("zst格式：双层压缩（内层7z+外层zstd），打开后包含一个7z压缩包")
            elif selected == '7z':
                self.update_status("7z格式：高压缩率，支持固实压缩")
            elif selected == 'zip':
                self.update_status("zip格式：通用格式，兼容性好")
        
        zip_format_combo.bind('<<ComboboxSelected>>', show_format_info)
        row += 1

        # 压缩级别
        ttk.Label(config_frame, text="压缩级别:").grid(row=row, column=0, sticky=tk.W, pady=2)
        compression_frame = ttk.Frame(config_frame)
        compression_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)
        compression_frame.columnconfigure(0, weight=1)

        self.zip_compression_level_var = tk.IntVar(value=self.config.zip_compression_level)
        compression_scale = ttk.Scale(compression_frame, from_=0, to=9, orient=tk.HORIZONTAL,
                                    variable=self.zip_compression_level_var, length=200)
        compression_scale.grid(row=0, column=0, sticky=(tk.W, tk.E))
        self.compression_level_label = ttk.Label(compression_frame, text=f"{self.config.zip_compression_level}")
        self.compression_level_label.grid(row=0, column=1, padx=(5, 0))
        compression_scale.configure(command=lambda v: self.compression_level_label.config(text=f"{int(float(v))}"))
        row += 1

        # 固实压缩模式
        self.zip_solid_mode_var = tk.BooleanVar(value=self.config.zip_solid_mode)
        solid_check = ttk.Checkbutton(config_frame, text="固实压缩模式（提高压缩率）",
                                     variable=self.zip_solid_mode_var)
        solid_check.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=2)
        row += 1

        # 字典大小
        ttk.Label(config_frame, text="字典大小:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.zip_dictionary_size_var = tk.StringVar(value=self.config.zip_dictionary_size)
        dict_combo = ttk.Combobox(config_frame, textvariable=self.zip_dictionary_size_var, width=33, state="readonly")
        dict_combo['values'] = ('1m', '2m', '4m', '8m', '16m', '32m', '64m', '128m')
        dict_combo.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)
        row += 1

        # 删除源文件选项
        self.delete_source_var = tk.BooleanVar(value=self.config.delete_source_files)
        delete_source_check = ttk.Checkbutton(config_frame, text="压缩完成后删除源文件",
                                             variable=self.delete_source_var)
        delete_source_check.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=2)

        row += 1

        # 删除压缩图片选项
        self.delete_compressed_images_var = tk.BooleanVar(value=self.config.delete_compressed_images)
        delete_compressed_check = ttk.Checkbutton(config_frame, text="删除压缩后的图片（不保留）",
                                                  variable=self.delete_compressed_images_var)
        delete_compressed_check.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=2)

        row += 1

        # 启用上传选项
        self.enable_upload_var = tk.BooleanVar(value=self.config.enable_upload)
        enable_upload_check = ttk.Checkbutton(config_frame, text="启用上传功能（取消则只打包）",
                                             variable=self.enable_upload_var)
        enable_upload_check.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=2)

        row += 1

        # 发布文章选项
        self.enable_publish_var = tk.BooleanVar(value=self.config.enable_publish)
        enable_publish_check = ttk.Checkbutton(config_frame, text="发布文章（取消则只上传不发布）",
                                               variable=self.enable_publish_var)
        enable_publish_check.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=2)

        row += 1

        # 工具配置（紧凑显示）
        tools_frame = ttk.Frame(config_frame)
        tools_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        # 7-Zip状态
        seven_zip_status = "✓已找到" if self.tools_config.seven_zip_path else "✗未找到"
        seven_zip_color = "green" if self.tools_config.seven_zip_path else "red"
        ttk.Label(tools_frame, text=f"7-Zip: {seven_zip_status}", foreground=seven_zip_color).pack(anchor=tk.W)

        # FFmpeg状态
        ffmpeg_status = "✓已找到" if self.tools_config.ffmpeg_path else "✗未找到"
        ffmpeg_color = "green" if self.tools_config.ffmpeg_path else "red"
        ttk.Label(tools_frame, text=f"FFmpeg: {ffmpeg_status}", foreground=ffmpeg_color).pack(anchor=tk.W)

        # 控制按钮
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=2, column=0, columnspan=2, pady=(0, 8))

        self.start_button = ttk.Button(control_frame, text="开始处理", command=self.start_processing)
        self.start_button.pack(side=tk.LEFT, padx=3)

        self.stop_button = ttk.Button(control_frame, text="停止", command=self.stop_processing, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=3)

        ttk.Button(control_frame, text="保存配置", command=self.save_config).pack(side=tk.LEFT, padx=3)
        ttk.Button(control_frame, text="高级配置", command=self.open_advanced_config).pack(side=tk.LEFT, padx=3)
        ttk.Button(control_frame, text="清理日志", command=self.clear_logs).pack(side=tk.LEFT, padx=3)
        ttk.Button(control_frame, text="打开输出目录", command=self.open_output_dir).pack(side=tk.LEFT, padx=3)

        # 状态显示区域
        status_frame = ttk.LabelFrame(main_frame, text="状态信息", padding="8")
        status_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 8))
        status_frame.columnconfigure(0, weight=1)
        status_frame.rowconfigure(0, weight=1)

        self.status_text = scrolledtext.ScrolledText(status_frame, height=8, state=tk.DISABLED, font=("Consolas", 9))
        self.status_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 进度条和状态栏
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E))
        bottom_frame.columnconfigure(0, weight=1)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(bottom_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 3))

        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(bottom_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=1, column=0, sticky=(tk.W, tk.E))

        # 配置主框架行列权重
        main_frame.rowconfigure(3, weight=1)
        top_frame.rowconfigure(0, weight=1)

    def on_file_drop(self, event):
        """处理拖拽的文件或文件夹"""
        files = self.root.tk.splitlist(event.data)
        self.add_files(files)

    def add_files(self, files):
        """添加文件或文件夹到列表"""
        for file_path in files:
            # 支持文件夹
            if os.path.isdir(file_path):
                if file_path not in self.dropped_files:
                    self.dropped_files.append(file_path)
                    # 更新文件列表显示
                    folder_name = os.path.basename(file_path)
                    # 计算文件夹大小
                    folder_size = self.get_folder_size(file_path)
                    self.file_tree.insert('', 'end', values=(folder_name, format_file_size(folder_size), "文件夹"))
            # 支持压缩文件
            elif os.path.isfile(file_path) and is_archive_file(file_path):
                if file_path not in self.dropped_files:
                    self.dropped_files.append(file_path)
                    # 更新文件列表显示
                    file_name = os.path.basename(file_path)
                    file_size = format_file_size(os.path.getsize(file_path))
                    file_type = os.path.splitext(file_path)[1].upper()
                    self.file_tree.insert('', 'end', values=(file_name, file_size, file_type))
            else:
                messagebox.showwarning("警告", f"不支持的文件类型: {file_path}")

    def get_folder_size(self, folder_path):
        """计算文件夹大小"""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(folder_path):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    if os.path.exists(file_path):
                        total_size += os.path.getsize(file_path)
        except Exception:
            pass
        return total_size

    def select_files(self):
        """选择文件或文件夹对话框"""
        # 先尝试选择文件夹
        folder = filedialog.askdirectory(title="选择文件夹（取消则选择文件）")
        if folder:
            self.add_files([folder])
            return
        
        # 如果没有选择文件夹，则选择文件
        files = filedialog.askopenfilenames(
            title="选择压缩文件",
            filetypes=[
                ("压缩文件", "*.7z *.zip *.rar *.tar *.gz"),
                ("所有文件", "*.*")
            ]
        )
        if files:
            self.add_files(files)

    def clear_file_list(self):
        """清空文件列表"""
        self.dropped_files.clear()
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)

    def remove_selected(self):
        """移除选中的文件或文件夹"""
        selected_items = self.file_tree.selection()
        for item in selected_items:
            # 获取名称
            values = self.file_tree.item(item)['values']
            if values:
                item_name = values[0]
                # 从列表中移除
                self.dropped_files = [f for f in self.dropped_files if os.path.basename(f) != item_name]
                # 从树形视图中删除
                self.file_tree.delete(item)

    def browse_output_dir(self):
        """浏览输出目录"""
        directory = filedialog.askdirectory(title="选择输出目录")
        if directory:
            self.output_dir_var.set(directory)

    def browse_seven_zip(self):
        """浏览7-Zip路径"""
        if sys.platform == 'win32':
            file_path = filedialog.askopenfilename(
                title="选择7-Zip可执行文件",
                filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")]
            )
        else:
            file_path = filedialog.askopenfilename(
                title="选择7-Zip可执行文件",
                filetypes=[("可执行文件", "7z"), ("所有文件", "*.*")]
            )

        if file_path:
            self.seven_zip_var.set(file_path)
            self.tools_config.set_custom_7zip_path(file_path)

    def browse_ffmpeg(self):
        """浏览FFmpeg路径"""
        if sys.platform == 'win32':
            file_path = filedialog.askopenfilename(
                title="选择FFmpeg可执行文件",
                filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")]
            )
        else:
            file_path = filedialog.askopenfilename(
                title="选择FFmpeg可执行文件",
                filetypes=[("可执行文件", "ffmpeg"), ("所有文件", "*.*")]
            )

        if file_path:
            self.ffmpeg_var.set(file_path)
            self.tools_config.set_custom_ffmpeg_path(file_path)

    def save_config(self):
        """保存配置"""
        # 更新配置
        self.config.output_dir = self.output_dir_var.get()
        self.config.login_account = self.login_account_var.get()
        self.config.login_password = self.login_password_var.get()
        self.config.device_id = self.device_id_var.get()
        self.config.delete_source_files = self.delete_source_var.get()
        self.config.delete_compressed_images = self.delete_compressed_images_var.get()
        self.config.enable_upload = self.enable_upload_var.get()
        self.config.enable_publish = self.enable_publish_var.get()

        # 压缩配置
        self.config.zip_format = self.zip_format_var.get()
        self.config.zip_compression_level = self.zip_compression_level_var.get()
        self.config.zip_solid_mode = self.zip_solid_mode_var.get()
        self.config.zip_dictionary_size = self.zip_dictionary_size_var.get()

        # 创建默认目录
        self.config_manager.config = self.config
        self.config_manager.create_default_directories()

        # 保存到文件（静默保存，不显示弹窗）
        if self.config_manager.save_config():
            self.update_status("配置已保存")
        else:
            self.update_status("保存配置失败")

    
    def start_processing(self):
        """开始处理"""
        # 检查是否有文件或文件夹
        if not self.dropped_files:
            self.update_status("错误：请先添加要处理的压缩文件或文件夹")
            return

        # 保存配置
        self.save_config()

        # 验证配置
        if not self.config.output_dir:
            self.update_status("错误：请先设置输出目录")
            return

        if not self.config.login_account or not self.config.login_password:
            self.update_status("错误：请先设置登录账号和密码")
            return

        # 创建文件处理器
        try:
            self.file_processor = FileProcessor(self.config, self.logger, self.update_status)
        except Exception as e:
            self.update_status(f"初始化失败: {e}")
            return

        # 更新UI状态
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status_var.set("正在处理...")

        # 清空状态文本
        self.status_text.config(state=tk.NORMAL)
        self.status_text.delete(1.0, tk.END)
        self.status_text.config(state=tk.DISABLED)

        # 启动处理线程
        self.processing_thread = threading.Thread(target=self.process_files)
        self.processing_thread.daemon = True
        self.processing_thread.start()

    def stop_processing(self):
        """停止处理"""
        if self.processing_thread and self.processing_thread.is_alive():
            # 这里可以设置停止标志，但为了简化，我们只是禁用按钮
            self.status_var.set("正在停止...")

    def process_files(self):
        """处理文件线程"""
        try:
            # 确保已登录（优先使用已有token）
            self.update_status("正在检查登录状态...")
            if not self.file_processor.api_handler.ensure_login():
                self.update_status("登录失败，请检查账号密码")
                return

            # 处理文件
            total_files = len(self.dropped_files)
            success_count = 0
            failure_count = 0

            for i, file_path in enumerate(self.dropped_files):
                if not os.path.exists(file_path):
                    continue

                self.update_status(f"正在处理文件 ({i+1}/{total_files}): {os.path.basename(file_path)}")
                self.progress_var.set((i / total_files) * 100)

                try:
                    if self.file_processor.process_file(file_path):
                        success_count += 1
                        # 从列表中移除已处理的文件
                        self.root.after(0, lambda: self.remove_processed_file(file_path))
                    else:
                        failure_count += 1
                except Exception as e:
                    self.logger.error(f"处理文件出错: {e}")
                    failure_count += 1

            # 完成
            self.update_status(f"处理完成！成功: {success_count}, 失败: {failure_count}")
            self.progress_var.set(100)

        except Exception as e:
            self.update_status(f"处理过程中出错: {e}")
            self.logger.error(f"处理过程中出错: {e}")
        finally:
            # 恢复UI状态
            self.root.after(0, self.reset_ui)

    def remove_processed_file(self, file_path):
        """从列表中移除已处理的文件或文件夹"""
        item_name = os.path.basename(file_path)
        for item in self.file_tree.get_children():
            values = self.file_tree.item(item)['values']
            if values and values[0] == item_name:
                self.file_tree.delete(item)
                break

    def update_status(self, message: str):
        """更新状态信息"""
        def update():
            self.status_text.config(state=tk.NORMAL)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.status_text.insert(tk.END, f"[{timestamp}] {message}\n")
            self.status_text.see(tk.END)
            self.status_text.config(state=tk.DISABLED)
            self.status_var.set(message)

        if threading.current_thread() == threading.main_thread():
            update()
        else:
            self.root.after(0, update)

    def reset_ui(self):
        """重置UI状态"""
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.progress_var.set(0)
        self.status_var.set("就绪")

    def clear_logs(self):
        """清理日志"""
        try:
            self.status_text.config(state=tk.NORMAL)
            self.status_text.delete(1.0, tk.END)
            self.status_text.config(state=tk.DISABLED)
            messagebox.showinfo("成功", "日志已清理")
        except Exception as e:
            messagebox.showerror("错误", f"清理日志失败: {e}")

    def open_output_dir(self):
        """打开输出目录"""
        try:
            output_dir = self.output_dir_var.get()
            if not output_dir:
                messagebox.showwarning("警告", "请先设置输出目录")
                return

            if not os.path.exists(output_dir):
                messagebox.showwarning("警告", f"输出目录不存在: {output_dir}")
                return

            # Windows系统使用explorer打开目录
            if os.name == 'nt':
                os.startfile(output_dir)
            else:
                # Linux/Mac系统
                import subprocess
                subprocess.run(['xdg-open', output_dir])

            self.logger.info(f"已打开输出目录: {output_dir}")

        except Exception as e:
            messagebox.showerror("错误", f"打开输出目录失败: {e}")

    def open_advanced_config(self):
        """打开高级配置窗口"""
        config_window = tk.Toplevel(self.root)
        config_window.title("高级配置")
        config_window.geometry("700x650")
        config_window.transient(self.root)
        config_window.grab_set()

        # 创建笔记本（标签页）
        notebook = ttk.Notebook(config_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # ===== 标签页1: 文件处理配置 =====
        file_frame = ttk.Frame(notebook, padding="10")
        notebook.add(file_frame, text="文件处理")
        
        row = 0
        
        # 图片前缀
        ttk.Label(file_frame, text="图片文件前缀:").grid(row=row, column=0, sticky=tk.W, pady=5)
        image_prefix_var = tk.StringVar(value=self.config.image_prefix)
        ttk.Entry(file_frame, textvariable=image_prefix_var, width=40).grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1

        # 视频前缀
        ttk.Label(file_frame, text="视频文件前缀:").grid(row=row, column=0, sticky=tk.W, pady=5)
        video_prefix_var = tk.StringVar(value=self.config.video_prefix)
        ttk.Entry(file_frame, textvariable=video_prefix_var, width=40).grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1

        # 压缩包密码
        ttk.Label(file_frame, text="压缩包密码:").grid(row=row, column=0, sticky=tk.W, pady=5)
        zip_password_var = tk.StringVar(value=self.config.zip_password)
        ttk.Entry(file_frame, textvariable=zip_password_var, width=40).grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1

        # 解压密码列表
        ttk.Label(file_frame, text="解压密码列表:").grid(row=row, column=0, sticky=tk.W, pady=5)
        ttk.Label(file_frame, text="(每行一个密码)", font=("Arial", 8)).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1
        
        passwords_text = scrolledtext.ScrolledText(file_frame, height=8, width=40)
        passwords_text.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        passwords_text.insert(1.0, '\n'.join(self.config.passwords))
        row += 1

        file_frame.columnconfigure(1, weight=1)

        # ===== 标签页2: 图片压缩配置 =====
        image_frame = ttk.Frame(notebook, padding="10")
        notebook.add(image_frame, text="图片压缩")
        
        row = 0

        # 最大高度
        ttk.Label(image_frame, text="最大高度 (像素):").grid(row=row, column=0, sticky=tk.W, pady=5)
        max_height_var = tk.IntVar(value=self.config.max_height)
        ttk.Spinbox(image_frame, from_=480, to=4320, textvariable=max_height_var, width=38).grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1

        # 最大宽度
        ttk.Label(image_frame, text="最大宽度 (像素):").grid(row=row, column=0, sticky=tk.W, pady=5)
        max_width_var = tk.IntVar(value=self.config.max_width)
        ttk.Spinbox(image_frame, from_=480, to=4320, textvariable=max_width_var, width=38).grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1

        # 图片质量
        ttk.Label(image_frame, text="图片质量 (1-100):").grid(row=row, column=0, sticky=tk.W, pady=5)
        quality_frame = ttk.Frame(image_frame)
        quality_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        quality_frame.columnconfigure(0, weight=1)
        
        quality_var = tk.IntVar(value=self.config.quality)
        quality_scale = ttk.Scale(quality_frame, from_=1, to=100, orient=tk.HORIZONTAL, variable=quality_var)
        quality_scale.grid(row=0, column=0, sticky=(tk.W, tk.E))
        quality_label = ttk.Label(quality_frame, text=f"{self.config.quality}")
        quality_label.grid(row=0, column=1, padx=(5, 0))
        quality_scale.configure(command=lambda v: quality_label.config(text=f"{int(float(v))}"))
        row += 1

        ttk.Label(image_frame, text="说明: 压缩后的图片用于上传，原图保留在压缩包中", 
                 font=("Arial", 8), foreground="gray").grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=10)
        row += 1

        image_frame.columnconfigure(1, weight=1)

        # ===== 标签页3: API配置 =====
        api_frame = ttk.Frame(notebook, padding="10")
        notebook.add(api_frame, text="API配置")
        
        row = 0

        # 上传API
        ttk.Label(api_frame, text="上传API:").grid(row=row, column=0, sticky=tk.W, pady=5)
        upload_api_var = tk.StringVar(value=self.config.upload_api)
        ttk.Entry(api_frame, textvariable=upload_api_var, width=40).grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1

        # 文章API
        ttk.Label(api_frame, text="文章API:").grid(row=row, column=0, sticky=tk.W, pady=5)
        article_api_var = tk.StringVar(value=self.config.article_api)
        ttk.Entry(api_frame, textvariable=article_api_var, width=40).grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1

        # 登录API
        ttk.Label(api_frame, text="登录API:").grid(row=row, column=0, sticky=tk.W, pady=5)
        login_api_var = tk.StringVar(value=self.config.login_api)
        ttk.Entry(api_frame, textvariable=login_api_var, width=40).grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1

        # 分类API
        ttk.Label(api_frame, text="分类API:").grid(row=row, column=0, sticky=tk.W, pady=5)
        category_api_var = tk.StringVar(value=self.config.category_api)
        ttk.Entry(api_frame, textvariable=category_api_var, width=40).grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1

        # 上传批次大小
        ttk.Label(api_frame, text="上传批次大小:").grid(row=row, column=0, sticky=tk.W, pady=5)
        upload_batch_var = tk.IntVar(value=self.config.upload_batch_size)
        ttk.Spinbox(api_frame, from_=1, to=100, textvariable=upload_batch_var, width=38).grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1

        # API超时
        ttk.Label(api_frame, text="API超时 (秒):").grid(row=row, column=0, sticky=tk.W, pady=5)
        api_timeout_var = tk.IntVar(value=self.config.api_timeout)
        ttk.Spinbox(api_frame, from_=30, to=600, textvariable=api_timeout_var, width=38).grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1

        api_frame.columnconfigure(1, weight=1)

        # ===== 标签页4: 系统配置 =====
        system_frame = ttk.Frame(notebook, padding="10")
        notebook.add(system_frame, text="系统配置")
        
        row = 0

        # 最大重试次数
        ttk.Label(system_frame, text="最大重试次数:").grid(row=row, column=0, sticky=tk.W, pady=5)
        max_retries_var = tk.IntVar(value=self.config.max_retries)
        ttk.Spinbox(system_frame, from_=1, to=10, textvariable=max_retries_var, width=38).grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1

        # 解压超时
        ttk.Label(system_frame, text="解压超时 (秒):").grid(row=row, column=0, sticky=tk.W, pady=5)
        extraction_timeout_var = tk.IntVar(value=self.config.extraction_timeout)
        ttk.Spinbox(system_frame, from_=30, to=600, textvariable=extraction_timeout_var, width=38).grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1

        # 清理保留天数
        ttk.Label(system_frame, text="日志保留天数:").grid(row=row, column=0, sticky=tk.W, pady=5)
        cleanup_days_var = tk.IntVar(value=self.config.cleanup_retention_days)
        ttk.Spinbox(system_frame, from_=1, to=90, textvariable=cleanup_days_var, width=38).grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1

        # 删除压缩图片选项
        delete_compressed_images_var = tk.BooleanVar(value=self.config.delete_compressed_images)
        ttk.Checkbutton(system_frame, text="删除压缩后的图片（不保留压缩图片）",
                       variable=delete_compressed_images_var).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5)
        row += 1

        # 启用上传选项
        enable_upload_var = tk.BooleanVar(value=self.config.enable_upload)
        ttk.Checkbutton(system_frame, text="启用上传功能（取消则只打包不上传）",
                       variable=enable_upload_var).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5)
        row += 1

        # 发布文章选项
        enable_publish_var = tk.BooleanVar(value=self.config.enable_publish)
        ttk.Checkbutton(system_frame, text="发布文章（取消则只上传不发布）",
                       variable=enable_publish_var).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5)
        row += 1

        ttk.Label(system_frame, text="说明: 不删除压缩图片时，会保存到输出目录的_compressed文件夹", 
                 font=("Arial", 8), foreground="gray").grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5)
        row += 1

        system_frame.columnconfigure(1, weight=1)

        # 底部按钮
        button_frame = ttk.Frame(config_window)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        def save_advanced_config():
            """保存高级配置"""
            try:
                # 文件处理配置
                self.config.image_prefix = image_prefix_var.get()
                self.config.video_prefix = video_prefix_var.get()
                self.config.zip_password = zip_password_var.get()
                
                # 解压密码列表
                passwords_content = passwords_text.get(1.0, tk.END).strip()
                self.config.passwords = [p.strip() for p in passwords_content.split('\n') if p.strip()]

                # 图片压缩配置
                self.config.max_height = max_height_var.get()
                self.config.max_width = max_width_var.get()
                self.config.quality = quality_var.get()

                # API配置
                self.config.upload_api = upload_api_var.get()
                self.config.article_api = article_api_var.get()
                self.config.login_api = login_api_var.get()
                self.config.category_api = category_api_var.get()
                self.config.upload_batch_size = upload_batch_var.get()
                self.config.api_timeout = api_timeout_var.get()

                # 系统配置
                self.config.max_retries = max_retries_var.get()
                self.config.extraction_timeout = extraction_timeout_var.get()
                self.config.cleanup_retention_days = cleanup_days_var.get()
                self.config.delete_compressed_images = delete_compressed_images_var.get()
                self.config.enable_upload = enable_upload_var.get()
                self.config.enable_publish = enable_publish_var.get()

                # 保存配置
                self.config_manager.config = self.config
                if self.config_manager.save_config():
                    messagebox.showinfo("成功", "高级配置已保存")
                    config_window.destroy()
                else:
                    messagebox.showerror("错误", "保存配置失败")
            except Exception as e:
                messagebox.showerror("错误", f"保存配置失败: {e}")

        def reset_to_default():
            """重置为默认值"""
            if messagebox.askyesno("确认", "确定要重置为默认配置吗？"):
                default_config = Config()
                
                # 文件处理配置
                image_prefix_var.set(default_config.image_prefix)
                video_prefix_var.set(default_config.video_prefix)
                zip_password_var.set(default_config.zip_password)
                passwords_text.delete(1.0, tk.END)
                passwords_text.insert(1.0, '\n'.join(default_config.passwords))

                # 图片压缩配置
                max_height_var.set(default_config.max_height)
                max_width_var.set(default_config.max_width)
                quality_var.set(default_config.quality)

                # API配置
                upload_api_var.set(default_config.upload_api)
                article_api_var.set(default_config.article_api)
                login_api_var.set(default_config.login_api)
                category_api_var.set(default_config.category_api)
                upload_batch_var.set(default_config.upload_batch_size)
                api_timeout_var.set(default_config.api_timeout)

                # 系统配置
                max_retries_var.set(default_config.max_retries)
                extraction_timeout_var.set(default_config.extraction_timeout)
                cleanup_days_var.set(default_config.cleanup_retention_days)
                delete_compressed_images_var.set(default_config.delete_compressed_images)
                enable_upload_var.set(default_config.enable_upload)
                enable_publish_var.set(default_config.enable_publish)

        ttk.Button(button_frame, text="保存", command=save_advanced_config).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="取消", command=config_window.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="重置为默认", command=reset_to_default).pack(side=tk.LEFT, padx=5)

    def on_closing(self):
        """窗口关闭事件"""
        if self.processing_thread and self.processing_thread.is_alive():
            if messagebox.askokcancel("退出", "正在处理文件，确定要退出吗？"):
                self.root.quit()
        else:
            self.root.quit()

    def run(self):
        """运行GUI"""
        self.root.mainloop()