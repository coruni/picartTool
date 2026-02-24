# 修复验证

## 修复1: zst格式文件名

### 问题
- 之前：`香草奶喵 - 圣诞礼物 [135P+25V - 1073MB].zst`
- 现在：`香草奶喵 - 圣诞礼物 [135P+25V - 1073MB].7z.zst`

### 修复位置
- `file_processor.py` 的 `process_folder` 和 `process_archive` 方法
- 添加了格式判断逻辑：
  ```python
  if self.config.zip_format.lower() == 'zst':
      zip_extension = ".7z.zst"  # zst格式使用双扩展名
  else:
      zip_extension = f".{self.config.zip_format}"
  ```

### 验证方法
1. 设置压缩格式为 zst
2. 处理一个文件或文件夹
3. 检查输出文件名是否为 `.7z.zst` 结尾

## 修复2: 保留压缩图片支持AVIF格式

### 问题
- 之前：只保存 `.webp` 格式的压缩图片
- 现在：同时支持 `.webp` 和 `.avif` 格式

### 修复位置
- `file_processor.py` 的 `_save_compressed_images` 方法
- 更新了图片扩展名列表：
  ```python
  image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.avif'}
  ```
- 添加了调试日志和警告信息

### 验证方法
1. 设置图片格式为 avif
2. 取消勾选"删除压缩后的图片"
3. 处理文件
4. 检查输出目录的 `_compressed` 文件夹中是否有 `.avif` 文件

## 测试场景

### 场景1: zst格式 + 保留压缩图片（WebP）
- 压缩格式：zst
- 图片格式：webp
- 删除压缩图片：✗
- 预期结果：
  - 压缩包：`文件名.7z.zst`
  - 压缩图片文件夹：`文件名_compressed/` 包含 `.webp` 文件

### 场景2: zst格式 + 保留压缩图片（AVIF）
- 压缩格式：zst
- 图片格式：avif
- 删除压缩图片：✗
- 预期结果：
  - 压缩包：`文件名.7z.zst`
  - 压缩图片文件夹：`文件名_compressed/` 包含 `.avif` 文件

### 场景3: 7z格式 + 保留压缩图片
- 压缩格式：7z
- 图片格式：webp
- 删除压缩图片：✗
- 预期结果：
  - 压缩包：`文件名.7z`
  - 压缩图片文件夹：`文件名_compressed/` 包含 `.webp` 文件

### 场景4: 多个文件处理
- 处理多个文件
- 取消勾选"删除压缩后的图片"
- 预期结果：每个文件都应该有对应的 `_compressed` 文件夹
