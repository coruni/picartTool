#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
处理器层 - 独立可插拔的处理单元
"""

from .extraction import ExtractionProcessor
from .cleaning import CleaningProcessor
from .renaming import RenamingProcessor
from .compression import ImageCompressionProcessor
from .archiving import ArchivingProcessor
from .uploading import UploadingProcessor
from .publishing import PublishingProcessor
from .title_formatting import TitleFormattingProcessor
from .cleanup import CleanupProcessor

__all__ = [
    'ExtractionProcessor',
    'CleaningProcessor',
    'RenamingProcessor',
    'ImageCompressionProcessor',
    'ArchivingProcessor',
    'UploadingProcessor',
    'PublishingProcessor',
    'TitleFormattingProcessor',
    'CleanupProcessor'
]