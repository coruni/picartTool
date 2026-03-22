#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设置视图 - 配置管理界面
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import TYPE_CHECKING, Callable, Optional, Dict, Any

if TYPE_CHECKING:
    from infrastructure.config import Config


class SettingsView:
    """
    设置视图

    提供完整的配置管理界面
    """

    def __init__(self, parent: tk.Tk, config: 'Config'):
        self.parent = parent
        self.config = config

        # 创建设置窗口
        self.window = tk.Toplevel(parent)
        self.window.title("设置")
        self.window.geometry("700x700")
        self.window.transient(parent)
        self.window.grab_set()

        # 回调
        self.on_save: Optional[Callable[['Config'], None]] = None

        # 变量字典
        self.vars: Dict[str, tk.Variable] = {}

        # 创建UI
        self._create_widgets()

    def _create_widgets(self):
        """创建UI组件"""
        # 底部按钮（先pack，固定在底部）
        btn_frame = ttk.Frame(self.window, padding=10)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self._create_buttons_content(btn_frame)

        # 主框架
        main_frame = ttk.Frame(self.window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 创建Notebook（分页）
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # 创建各个设置页
        self._create_basic_tab()
        self._create_archive_tab()
        self._create_image_tab()
        self._create_api_tab()
        self._create_ai_tab()
        self._create_image_host_tab()
        self._create_processing_tab()

    # ============ 基本设置 ============

    def _create_basic_tab(self):
        """创建基本设置页"""
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="基本设置")

        # 目录设置
        dir_frame = ttk.LabelFrame(frame, text="目录设置", padding=10)
        dir_frame.pack(fill=tk.X, pady=5)

        self._add_directory_field(dir_frame, "output_dir", "输出目录:", 0)
        self._add_directory_field(dir_frame, "temp_dir", "临时目录:", 1)
        self._add_directory_field(dir_frame, "log_dir", "日志目录:", 2)

        # 解压设置
        extract_frame = ttk.LabelFrame(frame, text="解压设置", padding=10)
        extract_frame.pack(fill=tk.X, pady=5)

        ttk.Label(extract_frame, text="解压密码列表:").grid(row=0, column=0, sticky=tk.W)
        passwords_text = tk.Text(extract_frame, height=5, width=50)
        passwords_text.grid(row=1, column=0, columnspan=2, sticky=tk.EW, pady=5)
        self.vars['passwords_text'] = passwords_text
        passwords_text.insert('1.0', '\n'.join(self.config.passwords or []))

        ttk.Label(extract_frame, text="（每行一个密码）").grid(row=2, column=0, sticky=tk.W)

        # 重命名设置
        rename_frame = ttk.LabelFrame(frame, text="重命名设置", padding=10)
        rename_frame.pack(fill=tk.X, pady=5)

        self._add_entry_field(rename_frame, "image_prefix", "图片前缀:", 0)
        self._add_entry_field(rename_frame, "video_prefix", "视频前缀:", 1)

    # ============ 打包设置 ============

    def _create_archive_tab(self):
        """创建打包设置页"""
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="打包设置")

        # 基本打包设置
        basic_frame = ttk.LabelFrame(frame, text="基本设置", padding=10)
        basic_frame.pack(fill=tk.X, pady=5)

        self._add_entry_field(basic_frame, "zip_password", "压缩密码:", 0, show="*")
        self._add_combobox_field(basic_frame, "zip_format", "压缩格式:", 1,
                                  ["7z", "zip", "zst"])
        self._add_spinbox_field(basic_frame, "zip_compression_level", "压缩级别:", 2,
                                 0, 9, 1)
        self._add_entry_field(basic_frame, "zip_dictionary_size", "字典大小:", 3)

        # 固实模式
        self._add_checkbox_field(basic_frame, "zip_solid_mode", "启用固实压缩", 4)

        # ZSTD设置
        zstd_frame = ttk.LabelFrame(frame, text="ZSTD高级设置", padding=10)
        zstd_frame.pack(fill=tk.X, pady=5)

        self._add_spinbox_field(zstd_frame, "zstd_compression_level", "压缩级别:", 0, 1, 22, 1)
        self._add_checkbox_field(zstd_frame, "zstd_long_distance_mode", "长距离匹配模式", 1)
        self._add_spinbox_field(zstd_frame, "zstd_ldm_distance", "LDM距离:", 2, 20, 30, 1)
        self._add_combobox_field(zstd_frame, "zstd_strategy", "压缩策略:", 3,
                                  ["default", "fast", "dfast", "greedy", "lazy"])
        self._add_spinbox_field(zstd_frame, "zstd_window_log", "窗口大小:", 4, 20, 30, 1)

    # ============ 图片设置 ============

    def _create_image_tab(self):
        """创建图片设置页"""
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="图片设置")

        # 尺寸设置
        size_frame = ttk.LabelFrame(frame, text="尺寸限制", padding=10)
        size_frame.pack(fill=tk.X, pady=5)

        self._add_spinbox_field(size_frame, "max_width", "最大宽度:", 0, 100, 10000, 100)
        self._add_spinbox_field(size_frame, "max_height", "最大高度:", 1, 100, 10000, 100)

        # 质量设置
        quality_frame = ttk.LabelFrame(frame, text="压缩设置", padding=10)
        quality_frame.pack(fill=tk.X, pady=5)

        self._add_checkbox_field(quality_frame, "enable_compression", "启用图片压缩", 0)
        self._add_spinbox_field(quality_frame, "quality", "质量:", 1, 1, 100, 1)
        self._add_combobox_field(quality_frame, "image_format", "输出格式:", 2,
                                  ["webp", "avif", "jpg", "png"])
        self._add_checkbox_field(quality_frame, "lossless_compression", "无损压缩", 3)
        self._add_spinbox_field(quality_frame, "max_upload_size_mb", "最大上传大小(MB):", 4, 1, 50, 1)

        # 上传方式设置
        upload_method_frame = ttk.LabelFrame(frame, text="上传方式", padding=10)
        upload_method_frame.pack(fill=tk.X, pady=5)

        self._add_combobox_field(upload_method_frame, "upload_method", "上传方式:", 0,
                                  ["api", "image_host", "imgur"])

    # ============ API设置 ============

    def _create_api_tab(self):
        """创建API设置页"""
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="API设置")

        # 登录设置
        login_frame = ttk.LabelFrame(frame, text="登录设置", padding=10)
        login_frame.pack(fill=tk.X, pady=5)

        self._add_entry_field(login_frame, "login_account", "账号:", 0)
        self._add_entry_field(login_frame, "login_password", "密码:", 1, show="*")
        self._add_entry_field(login_frame, "device_id", "设备ID:", 2)
        self._add_checkbox_field(login_frame, "skip_login", "跳过登录", 3)

        # API端点
        api_frame = ttk.LabelFrame(frame, text="API端点", padding=10)
        api_frame.pack(fill=tk.X, pady=5)

        self._add_entry_field(api_frame, "upload_api", "上传API:", 0, width=50)
        self._add_entry_field(api_frame, "article_api", "文章API:", 1, width=50)
        self._add_entry_field(api_frame, "login_api", "登录API:", 2, width=50)
        self._add_entry_field(api_frame, "category_api", "分类API:", 3, width=50)

        # 其他设置
        other_frame = ttk.LabelFrame(frame, text="其他设置", padding=10)
        other_frame.pack(fill=tk.X, pady=5)

        self._add_spinbox_field(other_frame, "upload_batch_size", "上传批次大小:", 0, 1, 100, 1)
        self._add_spinbox_field(other_frame, "api_timeout", "API超时(秒):", 1, 10, 300, 10)
        self._add_spinbox_field(other_frame, "extraction_timeout", "解压超时(秒):", 2, 30, 600, 30)
        self._add_spinbox_field(other_frame, "max_retries", "最大重试次数:", 3, 1, 10, 1)

        # Token显示
        token_frame = ttk.LabelFrame(frame, text="Token", padding=10)
        token_frame.pack(fill=tk.X, pady=5)

        self._add_entry_field(token_frame, "access_token", "Access Token:", 0, width=50)

    # ============ AI设置 ============

    def _create_ai_tab(self):
        """创建AI设置页"""
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="AI设置")

        # 基本设置
        basic_frame = ttk.LabelFrame(frame, text="AI配置", padding=10)
        basic_frame.pack(fill=tk.X, pady=5)

        self._add_checkbox_field(basic_frame, "ai_enabled", "启用AI功能", 0)
        self._add_entry_field(basic_frame, "ai_api_endpoint", "API端点:", 1, width=50)
        self._add_entry_field(basic_frame, "ai_api_key", "API Key:", 2, show="*", width=50)
        self._add_entry_field(basic_frame, "ai_model", "模型名称:", 3, width=30)

        # 参数设置
        param_frame = ttk.LabelFrame(frame, text="参数设置", padding=10)
        param_frame.pack(fill=tk.X, pady=5)

        self._add_spinbox_field(param_frame, "ai_temperature", "Temperature:", 0, 0.0, 2.0, 0.1)
        self._add_spinbox_field(param_frame, "ai_max_tokens", "Max Tokens:", 1, 100, 32000, 100)

        # 测试按钮
        ttk.Button(param_frame, text="测试连接", command=self._test_ai).grid(
            row=2, column=0, columnspan=2, pady=10)

    # ============ 图床设置 ============

    def _create_image_host_tab(self):
        """创建图床设置页"""
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="图床设置")

        # 图床基本设置
        basic_frame = ttk.LabelFrame(frame, text="图床配置", padding=10)
        basic_frame.pack(fill=tk.X, pady=5)

        self._add_checkbox_field(basic_frame, "image_host_enabled", "启用图床上传", 0)
        self._add_entry_field(basic_frame, "image_host_api", "API地址:", 1, width=50)
        self._add_entry_field(basic_frame, "image_host_key", "API Key:", 2, show="*", width=50)

        # 图床测试按钮
        btn_frame = ttk.Frame(basic_frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=5)
        ttk.Button(btn_frame, text="测试图床连接", command=self._test_image_host).pack(side=tk.LEFT)

        # Imgur配置
        imgur_frame = ttk.LabelFrame(frame, text="Imgur配置", padding=10)
        imgur_frame.pack(fill=tk.X, pady=5)

        self._add_entry_field(imgur_frame, "imgur_client_id", "Client ID:", 0, width=50)

        # 测试按钮
        btn_frame = ttk.Frame(imgur_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="测试 Imgur 连接", command=self._test_imgur).pack(side=tk.LEFT)

        # 说明
        help_frame = ttk.LabelFrame(frame, text="使用说明", padding=10)
        help_frame.pack(fill=tk.X, pady=5)

        help_text = """上传方式说明：
- api: 使用原有API上传（需配置API设置）
- image_host: 使用自定义图床上传
- imgur: 使用Imgur图床上传（需配置Client ID）

图床API说明：
1. API地址格式：http://yoursite.com/api/1/upload
2. 上传时会自动使用 format=txt 参数，直接返回URL

Imgur说明：
1. 注册 Imgur 应用获取 Client ID
2. 免费API限制：约1250次上传/天
3. 使用 Imgur 时，图片会强制转换为 jpg 格式"""

        ttk.Label(help_frame, text=help_text, justify=tk.LEFT).pack(anchor=tk.W)

    # ============ 处理设置 ============

    def _create_processing_tab(self):
        """创建处理设置页"""
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="处理设置")

        # 上传发布设置
        upload_frame = ttk.LabelFrame(frame, text="上传发布", padding=10)
        upload_frame.pack(fill=tk.X, pady=5)

        self._add_checkbox_field(upload_frame, "enable_upload", "启用上传", 0)
        self._add_checkbox_field(upload_frame, "enable_publish", "启用发布", 1)

        # 文件清理设置
        clean_frame = ttk.LabelFrame(frame, text="文件清理", padding=10)
        clean_frame.pack(fill=tk.X, pady=5)

        self._add_checkbox_field(clean_frame, "delete_source_files", "删除源文件", 0)
        self._add_checkbox_field(clean_frame, "delete_compressed_images", "删除压缩后图片", 1)

        # 网络设置
        network_frame = ttk.LabelFrame(frame, text="网络设置", padding=10)
        network_frame.pack(fill=tk.X, pady=5)

    # ============ 辅助方法 ============

    def _add_entry_field(self, parent, key: str, label: str, row: int,
                          show: str = None, width: int = 30):
        """添加输入框"""
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=2)

        var = tk.StringVar(value=getattr(self.config, key, ""))
        entry = ttk.Entry(parent, textvariable=var, width=width, show=show)
        entry.grid(row=row, column=1, sticky=tk.EW, pady=2)

        self.vars[key] = var
        parent.columnconfigure(1, weight=1)

    def _add_directory_field(self, parent, key: str, label: str, row: int):
        """添加目录选择框"""
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=2)

        var = tk.StringVar(value=getattr(self.config, key, ""))
        entry = ttk.Entry(parent, textvariable=var, width=40)
        entry.grid(row=row, column=1, sticky=tk.EW, pady=2)

        btn = ttk.Button(parent, text="浏览...", width=8,
                         command=lambda: self._browse_directory(var))
        btn.grid(row=row, column=2, padx=5, pady=2)

        self.vars[key] = var
        parent.columnconfigure(1, weight=1)

    def _add_combobox_field(self, parent, key: str, label: str, row: int, values: list):
        """添加下拉框"""
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=2)

        var = tk.StringVar(value=getattr(self.config, key, ""))
        combo = ttk.Combobox(parent, textvariable=var, values=values, width=28, state='readonly')
        combo.grid(row=row, column=1, sticky=tk.W, pady=2)

        self.vars[key] = var

    def _add_spinbox_field(self, parent, key: str, label: str, row: int,
                            from_: float, to: float, increment: float):
        """添加数值输入框"""
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=2)

        value = getattr(self.config, key, from_)
        var = tk.StringVar(value=str(value))

        spinbox = ttk.Spinbox(parent, from_=from_, to=to, increment=increment,
                               textvariable=var, width=15)
        spinbox.grid(row=row, column=1, sticky=tk.W, pady=2)

        self.vars[key] = var

    def _add_checkbox_field(self, parent, key: str, label: str, row: int):
        """添加复选框"""
        var = tk.BooleanVar(value=getattr(self.config, key, False))
        cb = ttk.Checkbutton(parent, text=label, variable=var)
        cb.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=2)

        self.vars[key] = var

    def _browse_directory(self, var: tk.StringVar):
        """浏览目录"""
        directory = filedialog.askdirectory(initialdir=var.get())
        if directory:
            var.set(directory)

    def _test_ai(self):
        """测试AI连接"""
        try:
            from services.ai_service import AIService

            # 临时创建配置对象
            class TempConfig:
                pass

            temp_config = TempConfig()
            temp_config.ai_enabled = True
            temp_config.ai_api_endpoint = self.vars.get('ai_api_endpoint', tk.StringVar()).get()
            temp_config.ai_api_key = self.vars.get('ai_api_key', tk.StringVar()).get()
            temp_config.ai_model = self.vars.get('ai_model', tk.StringVar()).get()
            temp_config.ai_max_tokens = int(self.vars.get('ai_max_tokens', tk.StringVar(value="4096")).get())
            temp_config.ai_temperature = float(self.vars.get('ai_temperature', tk.StringVar(value="0.7")).get())

            service = AIService(temp_config)

            # 简单测试
            result = service.generate_title("test.zip", 10, 0, 50)
            if result:
                messagebox.showinfo("成功", f"AI连接测试成功！\n返回: {result}")
            else:
                messagebox.showwarning("提示", "AI连接成功，但未返回结果")
        except Exception as e:
            messagebox.showerror("错误", f"测试失败: {e}")

    def _test_image_host(self):
        """测试图床连接"""
        try:
            from services.image_host_service import ImageHostService

            # 临时创建配置对象
            class TempConfig:
                pass

            temp_config = TempConfig()
            temp_config.image_host_api = self.vars.get('image_host_api', tk.StringVar()).get()
            temp_config.image_host_key = self.vars.get('image_host_key', tk.StringVar()).get()
            temp_config.max_retries = 1

            service = ImageHostService(temp_config)
            success, message = service.test_connection()

            if success:
                messagebox.showinfo("成功", message)
            else:
                messagebox.showerror("失败", message)

        except Exception as e:
            messagebox.showerror("错误", f"测试失败: {e}")

    def _test_imgur(self):
        """测试 Imgur 连接"""
        try:
            from services.imgur_service import ImgurService

            # 临时创建配置对象
            class TempConfig:
                pass

            temp_config = TempConfig()
            temp_config.imgur_client_id = self.vars.get('imgur_client_id', tk.StringVar()).get()
            temp_config.max_retries = 1

            service = ImgurService(temp_config)
            success, message = service.test_connection()

            if success:
                messagebox.showinfo("成功", message)
            else:
                messagebox.showerror("失败", message)

        except Exception as e:
            messagebox.showerror("错误", f"测试失败: {e}")

    # ============ 底部按钮 ============

    def _create_buttons_content(self, parent):
        """创建底部按钮内容"""
        ttk.Button(parent, text="保存", command=self._on_save_click).pack(side=tk.RIGHT, padx=5)
        ttk.Button(parent, text="取消", command=self.window.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(parent, text="恢复默认", command=self._on_reset).pack(side=tk.LEFT, padx=5)

    def _on_save_click(self):
        """保存按钮点击"""
        # 更新配置
        for key, var in self.vars.items():
            if key == 'passwords_text':
                continue  # 单独处理

            value = var.get()

            # 类型转换
            attr = getattr(self.config.__class__, key, None)
            if attr is not None:
                import dataclasses
                if dataclasses.is_dataclass(self.config.__class__):
                    field_type = None
                    for f in dataclasses.fields(self.config.__class__):
                        if f.name == key:
                            field_type = f.type
                            break

                    if field_type == int:
                        value = int(float(value))
                    elif field_type == float:
                        value = float(value)
                    elif field_type == bool:
                        if isinstance(value, bool):
                            value = value
                        elif isinstance(value, str):
                            value = value.lower() == 'true'
                        else:
                            value = bool(value)

            setattr(self.config, key, value)

        # 处理密码列表
        passwords_text = self.vars.get('passwords_text')
        if passwords_text:
            self.config.passwords = [p.strip() for p in passwords_text.get('1.0', tk.END).split('\n') if p.strip()]

        # 调用回调
        if self.on_save:
            self.on_save(self.config)

        messagebox.showinfo("成功", "设置已保存")
        self.window.destroy()

    def _on_reset(self):
        """恢复默认设置"""
        if messagebox.askyesno("确认", "确定要恢复默认设置吗？"):
            # 恢复默认值
            from infrastructure.config import Config
            default = Config()

            for key in self.vars:
                if key == 'passwords_text':
                    continue
                if hasattr(default, key):
                    self.vars[key].set(getattr(default, key))

            # 更新密码列表
            if 'passwords_text' in self.vars:
                self.vars['passwords_text'].delete('1.0', tk.END)
                self.vars['passwords_text'].insert('1.0', '\n'.join(default.passwords or []))

    def show(self):
        """显示设置窗口"""
        self.window.wait_window()