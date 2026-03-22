#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主视图 - 负责UI渲染和用户交互
"""

import os
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from typing import TYPE_CHECKING, Callable, Optional, List

# 拖拽支持
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False

if TYPE_CHECKING:
    from .main_controller import MainController
    from infrastructure.config import Config


class MainView:
    """
    主视图

    负责UI渲染和用户交互，不包含业务逻辑
    """

    def __init__(self, parent: tk.Tk, config: 'Config'):
        self.parent = parent
        self.config = config
        self.controller: Optional['MainController'] = None

        # 创建主框架
        self.main_frame = ttk.Frame(parent)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 创建UI组件
        self._create_widgets()

        # 设置拖拽
        self._setup_drag_drop()

    def set_controller(self, controller: 'MainController'):
        """设置控制器"""
        self.controller = controller

    def _create_widgets(self):
        """创建UI组件"""
        # 顶部：文件列表
        self._create_file_list_section()

        # 中间：操作按钮
        self._create_action_buttons()

        # 底部：日志区域
        self._create_log_section()

        # 状态栏
        self._create_status_bar()

    def _create_file_list_section(self):
        """创建文件列表区域"""
        list_frame = ttk.LabelFrame(self.main_frame, text="待处理文件", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # 文件列表（显示完整路径）
        self.file_listbox = tk.Listbox(list_frame, height=8, selectmode=tk.EXTENDED)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.file_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.config(yscrollcommand=scrollbar.set)

        # 文件操作按钮
        btn_frame = ttk.Frame(list_frame)
        btn_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Button(btn_frame, text="添加文件", command=self._on_add_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="添加文件夹", command=self._on_add_folder).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="清空列表", command=self._on_clear_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="移除选中", command=self._on_remove_selected).pack(side=tk.LEFT, padx=5)

        # 提示标签
        hint_text = "拖拽文件或文件夹到此处添加" if HAS_DND else "点击按钮添加文件"
        self.hint_label = ttk.Label(list_frame, text=hint_text, foreground='gray')
        self.hint_label.pack(pady=5)

        # 文件计数标签
        self.file_count_label = ttk.Label(list_frame, text="共 0 个文件", foreground='blue')
        self.file_count_label.pack(pady=2)

    def _create_action_buttons(self):
        """创建操作按钮区域"""
        btn_frame = ttk.Frame(self.main_frame)
        btn_frame.pack(fill=tk.X, pady=10)

        # 主要操作
        ttk.Button(btn_frame, text="开始处理", command=self._on_start_processing).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="停止处理", command=self._on_stop_processing).pack(side=tk.LEFT, padx=5)

        ttk.Separator(btn_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        # 设置按钮
        ttk.Button(btn_frame, text="设置", command=self._on_open_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="打开输出目录", command=self._on_open_output_dir).pack(side=tk.LEFT, padx=5)

    def _create_log_section(self):
        """创建日志区域"""
        log_frame = ttk.LabelFrame(self.main_frame, text="处理日志", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _create_status_bar(self):
        """创建状态栏"""
        status_frame = ttk.Frame(self.main_frame)
        status_frame.pack(fill=tk.X)

        self.status_label = ttk.Label(status_frame, text="就绪", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(fill=tk.X)

    def _setup_drag_drop(self):
        """设置拖拽功能"""
        if HAS_DND:
            # 注册窗口为拖拽目标
            self.parent.drop_target_register(DND_FILES)
            self.parent.dnd_bind('<<Drop>>', self._on_drop)

            # 注册主框架为拖拽目标
            self.main_frame.drop_target_register(DND_FILES)
            self.main_frame.dnd_bind('<<Drop>>', self._on_drop)

            # 注册文件列表区域为拖拽目标
            self.file_listbox.drop_target_register(DND_FILES)
            self.file_listbox.dnd_bind('<<Drop>>', self._on_drop)

    # ============ 事件处理 ============

    def _on_add_files(self):
        """添加文件事件"""
        files = filedialog.askopenfilenames(
            title="选择文件",
            filetypes=[
                ("压缩文件", "*.7z *.zip *.rar *.tar *.gz"),
                ("所有文件", "*.*")
            ]
        )
        if files and self.controller:
            self.controller.add_files(list(files))

    def _on_add_folder(self):
        """添加文件夹事件"""
        folder = filedialog.askdirectory(title="选择文件夹")
        if folder and self.controller:
            self.controller.add_files([folder])

    def _on_clear_files(self):
        """清空文件列表事件"""
        if self.controller:
            self.controller.clear_files()

    def _on_remove_selected(self):
        """移除选中文件事件"""
        selection = self.file_listbox.curselection()
        if selection and self.controller:
            self.controller.remove_files(selection)

    def _on_drop(self, event):
        """拖拽事件"""
        if self.controller:
            # 解析拖拽的文件
            files = self._parse_dropped_files(event.data)
            self.controller.add_files(files)

    def _parse_dropped_files(self, data: str) -> List[str]:
        """解析拖拽的文件"""
        files = []

        # tkinterdnd2 返回的数据格式
        # Windows: {C:/path/to/file1.txt} {C:/path/to/file2.txt}
        # 或者: C:/path/to/file1.txt C:/path/to/file2.txt

        if not data:
            return files

        # 处理花括号包裹的路径
        # 匹配 {path} 或普通路径
        pattern = r'\{([^}]+)\}|(\S+)'
        matches = re.findall(pattern, data)

        for match in matches:
            # match 是一个元组，取非空的那个
            path = match[0] if match[0] else match[1]
            path = path.strip()

            if path and os.path.exists(path):
                files.append(path)

        return files

    def _on_start_processing(self):
        """开始处理事件"""
        if self.controller:
            self.controller.start_processing()

    def _on_stop_processing(self):
        """停止处理事件"""
        if self.controller:
            self.controller.stop_processing()

    def _on_open_settings(self):
        """打开设置事件"""
        if self.controller:
            self.controller.open_settings()

    def _on_open_output_dir(self):
        """打开输出目录事件"""
        if self.controller:
            self.controller.open_output_dir()

    # ============ 视图更新方法 ============

    def update_file_list(self, files: List[str]):
        """更新文件列表"""
        self.file_listbox.delete(0, tk.END)
        total_size = 0

        for file in files:
            # 显示文件名和大小
            try:
                if os.path.isfile(file):
                    size = os.path.getsize(file)
                    total_size += size
                    size_str = self._format_size(size)
                    display = f"{os.path.basename(file)} ({size_str})"
                elif os.path.isdir(file):
                    display = f"[文件夹] {os.path.basename(file)}"
                else:
                    display = os.path.basename(file)
            except:
                display = os.path.basename(file)

            self.file_listbox.insert(tk.END, display)

        # 更新文件计数
        count_text = f"共 {len(files)} 个项目"
        if total_size > 0:
            count_text += f" | 总大小: {self._format_size(total_size)}"
        self.file_count_label.config(text=count_text)

    def _format_size(self, size: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def append_log(self, message: str):
        """追加日志"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def clear_log(self):
        """清空日志"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)

    def update_status(self, message: str):
        """更新状态栏"""
        self.status_label.config(text=message)

    def set_processing(self, is_processing: bool):
        """设置处理状态"""
        if is_processing:
            self.status_label.config(text="处理中...")
        else:
            self.status_label.config(text="就绪")

    def show_message(self, title: str, message: str, msg_type: str = "info"):
        """显示消息框"""
        if msg_type == "error":
            messagebox.showerror(title, message)
        elif msg_type == "warning":
            messagebox.showwarning(title, message)
        else:
            messagebox.showinfo(title, message)

    def ask_yes_no(self, title: str, message: str) -> bool:
        """询问是否"""
        return messagebox.askyesno(title, message)