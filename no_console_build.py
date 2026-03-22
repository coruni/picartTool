#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重新打包为无控制台窗口的exe
"""

import subprocess
import sys
import os

def build_no_console():
    """构建无控制台窗口的exe"""
    print("=== 重新打包为无控制台窗口 ===")

    # 创建自定义spec文件
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('config.json', '.'), ('tools', 'tools')],
    hiddenimports=['tkinterdnd2', 'PIL._tkinter_finder'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='文件处理工具',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # 确保这是False
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if os.path.exists('icon.ico') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    console=False,  # 确保这是False
    upx_exclude=[],
    name='文件处理工具',
    icon='icon.ico' if os.path.exists('icon.ico') else None,
)
'''

    # 写入spec文件
    with open('no_console.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)

    print("✓ 创建自定义spec文件")

    # 使用spec文件构建
    cmd = [
        'pyinstaller',
        '--clean',
        '--noconfirm',
        'no_console.spec'
    ]

    print("执行命令:", ' '.join(cmd))

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✓ 打包成功！")

        # 检查输出
        dist_dir = 'dist'
        if os.path.exists(dist_dir):
            print(f"输出目录: {dist_dir}")
            for file in os.listdir(dist_dir):
                if file.endswith('.exe'):
                    print(f"exe文件: {file}")

        return True

    except subprocess.CalledProcessError as e:
        print(f"✗ 打包失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False

if __name__ == '__main__':
    build_no_console()