# 文件处理工具

Windows兼容的GUI文件处理应用，支持拖拽压缩包进行处理。

## 功能特性

- 🖱️ **拖拽操作**: 支持直接拖拽压缩文件到界面
- 📦 **多格式支持**: 支持 .7z, .zip, .rar 等压缩格式
- 🔐 **自动解密**: 自动尝试多种密码解压
- 🖼️ **图片压缩**: 自动压缩图片为WebP格式
- 📤 **自动上传**: 上传到远程服务器并提交文章
- ⚙️ **配置管理**: 可视化配置管理
- 📊 **状态监控**: 实时显示处理进度和状态

## 系统要求

- Windows 10/11
- Python 3.7+
- 7-Zip (用于压缩/解压)
- FFmpeg (用于图片处理)

## 🎯 工具配置 - 支持项目本地放置

本程序支持多种工具配置方式，**优先使用项目目录中的工具**：

### 方式1: 放在项目目录 (推荐)
1. 将 `7z.exe` 复制到项目根目录或 `tools` 目录
2. 将 `ffmpeg.exe` 复制到项目根目录或 `tools` 目录
3. 无需安装到系统，绿色便携

### 方式2: 手动配置路径
1. 在程序界面的工具配置区域手动指定工具路径
2. 支持浏览选择工具文件位置

### 方式3: 系统安装
1. 安装7-Zip到系统: https://www.7-zip.org/
2. 安装FFmpeg到系统: https://ffmpeg.org/download.html

### 快速下载链接
- **7-Zip便携版**: https://www.7-zip.org/a/7z2301-x64.exe
- **FFmpeg便携版**: https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip

下载后将7z.exe和ffmpeg.exe复制到tools目录即可。

## 安装步骤

1. **下载并安装Python**
   - 访问 https://www.python.org/downloads/
   - 下载并安装Python 3.7或更高版本

2. **安装7-Zip**
   - 访问 https://www.7-zip.org/
   - 下载并安装7-Zip

3. **安装FFmpeg**
   - 访问 https://ffmpeg.org/download.html
   - 下载Windows版本并解压
   - 将FFmpeg的bin目录添加到系统PATH

4. **安装应用依赖**
   ```bash
   # 方法1: 使用安装脚本
   double-click install.bat

   # 方法2: 手动安装
   pip install -r requirements.txt
   ```

## 使用方法

1. **启动应用**
   ```bash
   python main.py
   ```

2. **配置设置**
   - 设置输出目录
   - 配置登录账号和密码

3. **添加文件**
   - 拖拽压缩文件到界面
   - 或点击"选择文件"按钮

4. **开始处理**
   - 点击"开始处理"按钮
   - 等待处理完成

## 配置说明

### 目录配置
- **输出目录**: 处理后的文件保存位置
- **临时目录**: 处理过程中的临时文件
- **日志目录**: 日志文件保存位置

### API配置
- **登录账号**: API登录账号
- **登录密码**: API登录密码
- **上传API**: 文件上传接口地址
- **文章API**: 文章提交接口地址

### 压缩配置
- **最大宽度**: 图片压缩后的最大宽度
- **最大高度**: 图片压缩后的最大高度
- **压缩质量**: 图片压缩质量 (0-100)

## 文件结构

```
file_processor/
├── main.py              # 主程序入口
├── config.py            # 配置管理
├── logger.py            # 日志管理
├── utils.py             # 工具函数
├── compression.py       # 压缩/解压处理
├── image_processor.py   # 图片处理
├── api_handler.py       # API处理
├── file_processor.py    # 文件处理核心
├── gui.py               # GUI界面
├── requirements.txt     # 依赖列表
├── install.bat          # 安装脚本
└── README.md           # 说明文档
```

## 常见问题

### Q: 提示"7-Zip未安装"
A: 请从 https://www.7-zip.org/ 下载并安装7-Zip，或将7z.exe复制到系统PATH中。

### Q: 提示"FFmpeg未安装"
A: 请从 https://ffmpeg.org/download.html 下载FFmpeg，并将bin目录添加到系统PATH。

### Q: 拖拽文件没有反应
A: 请确保安装了tkinterdnd2包：`pip install tkinterdnd2`

### Q: 处理失败
A: 检查日志文件了解详细错误信息，确保网络连接正常且API配置正确。

## 开发说明

### 模块说明
- **config.py**: 配置管理，包括加载、保存和验证配置
- **logger.py**: 日志管理，支持文件和控制台输出
- **utils.py**: 工具函数，包括文件名清理、格式检查等
- **compression.py**: 压缩/解压处理，基于7-Zip
- **image_processor.py**: 图片处理，基于FFmpeg
- **api_handler.py**: API处理，包括登录、上传和提交
- **file_processor.py**: 文件处理核心，整合各个模块
- **gui.py**: GUI界面，基于tkinter和tkinterdnd2

### 扩展开发
1. 添加新的压缩格式支持：修改compression.py
2. 添加新的图片处理功能：修改image_processor.py
3. 修改API接口：修改api_handler.py
4. 添加新的GUI功能：修改gui.py

## 许可证

本项目采用MIT许可证。

## 贡献

欢迎提交Issue和Pull Request！