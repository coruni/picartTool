#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI服务 - 调用AI API生成标题和标签
"""

import json
from typing import Optional, Dict, Any, List

import requests


class AIService:
    """
    AI服务

    负责调用AI API生成标题、标签等
    """

    def __init__(self, config, logger=None):
        self.config = config
        self.logger = logger

    def is_enabled(self) -> bool:
        """检查AI功能是否启用"""
        return (
            self.config.ai_enabled and
            bool(self.config.ai_api_key) and
            bool(self.config.ai_api_endpoint)
        )

    def generate_title(self, original_filename: str, image_count: int,
                       video_count: int, total_mb: int) -> Optional[Dict[str, Any]]:
        """
        使用AI生成标题

        Args:
            original_filename: 原始文件名
            image_count: 图片数量
            video_count: 视频数量
            total_mb: 文件大小(MB)

        Returns:
            包含 coser_name 和 work_name 的字典，失败返回 None
        """
        if not self.is_enabled():
            return None

        prompt = self._build_title_prompt(original_filename)

        try:
            result = self._call_api(prompt)

            if result:
                parsed = self._parse_json_response(result)
                if parsed and 'coser_name' in parsed and 'work_name' in parsed:
                    self._log(f"AI生成标题成功: {parsed}")
                    return parsed

            self._log("AI返回格式不正确", level="warning")
            return None

        except Exception as e:
            self._log(f"AI生成标题失败: {e}", level="warning")
            return None

    def generate_tags(self, coser_name: str, work_name: str,
                      original_filename: str = "") -> List[str]:
        """
        使用AI生成标签

        Args:
            coser_name: 作者名称
            work_name: 作品信息
            original_filename: 原始文件名

        Returns:
            标签列表
        """
        if not self.is_enabled():
            return []

        prompt = self._build_tags_prompt(coser_name, work_name, original_filename)

        try:
            result = self._call_api(prompt, max_tokens=500, temperature=0.3)

            if result:
                parsed = self._parse_json_response(result)
                if parsed:
                    tags = parsed.get('tagNames', [])
                    # 过滤和清理标签
                    valid_tags = []
                    for tag in tags:
                        if isinstance(tag, str) and tag.strip():
                            clean_tag = tag.strip()[:20]
                            if clean_tag:
                                valid_tags.append(clean_tag)
                    return valid_tags[:3]

        except Exception as e:
            self._log(f"AI生成标签失败: {e}", level="warning")

        return []

    def format_ai_title(self, coser_name: str, work_name: str,
                        image_count: int, video_count: int, total_mb: int) -> str:
        """
        格式化AI生成的标题

        Args:
            coser_name: 作者名称
            work_name: 作品信息
            image_count: 图片数量
            video_count: 视频数量
            total_mb: 文件大小(MB)

        Returns:
            格式化后的标题
        """
        if video_count > 0:
            stats = f"[{image_count}P+{video_count}V - {total_mb}MB]"
        else:
            stats = f"[{image_count}P - {total_mb}MB]"

        return f"[{coser_name}] {stats} {work_name}"

    def _build_title_prompt(self, filename: str) -> str:
        """构建标题生成提示词"""
        return f"""请分析以下文件名，提取作者名称、作品来源、角色名等信息。

文件名: {filename}

返回JSON格式，包含以下字段:
- coser_name: 作者/Coser/模特名称
- work_name: 作品信息

work_name 格式规则（严格遵守）:
1. 有来源作品时：格式为 "来源作品 - 角色名"
   示例：碧蓝幻想 - 娜露梅亚、赛马娘 - 大和赤骥、刀剑神域 - 亚丝娜
2. 无来源作品时：直接写主题/角色名
   示例：兔女郎、圣诞主题、浴衣
3. 有角色+服装主题时：格式为 "来源作品 - 角色名 - 服装/主题"
   示例：碧蓝幻想 - 娜露梅亚 - 女仆、刀剑神域 - 亚丝娜 - 礼服

最终文件名格式示例：
[洛璃LoLiSAMA] [37P - 504MB] 碧蓝幻想 - 娜露梅亚 - 女仆
[阿半] [35P - 307MB] 赛马娘 - 大和赤骥
[切切celia] [28P - 232MB] 刀剑神域 - 亚丝娜 - 礼服

只返回JSON，不要其他内容。"""

    def _build_tags_prompt(self, coser_name: str, work_name: str,
                           original_filename: str) -> str:
        """构建标签生成提示词"""
        return f"""请根据以下信息生成2-3个高度相关的标签。

作者/Coser: {coser_name}
作品信息: {work_name}
原始文件名: {original_filename}

标签生成规则:
1. 标签必须与内容高度相关
2. 不要把作者名称作为标签
3. 优先从以下维度提取: 来源作品名、角色名、主题/风格
4. 返回JSON格式: {{"tagNames": ["标签1", "标签2"]}}

只返回JSON，不要其他内容。"""

    def _call_api(self, prompt: str, max_tokens: int = None,
                  temperature: float = None) -> Optional[str]:
        """调用AI API"""
        max_tokens = max_tokens or self.config.ai_max_tokens
        temperature = temperature or self.config.ai_temperature

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.ai_api_key}",
            "Connection": "close"  # 禁用 keep-alive
        }

        # 检查是否是Anthropic API
        is_anthropic = "anthropic.com" in self.config.ai_api_endpoint

        if is_anthropic:
            headers["x-api-key"] = self.config.ai_api_key
            headers["anthropic-version"] = "2023-06-01"
            if "Authorization" in headers:
                del headers["Authorization"]

            payload = {
                "model": self.config.ai_model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}]
            }

            endpoint = self.config.ai_api_endpoint.rstrip('/') + "/messages"
        else:
            payload = {
                "model": self.config.ai_model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"}
            }

            endpoint = self.config.ai_api_endpoint.rstrip('/') + "/chat/completions"

        response = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()

            if is_anthropic:
                return result.get("content", [{}])[0].get("text", "")
            else:
                return result.get("choices", [{}])[0].get("message", {}).get("content", "")

        self._log(f"AI API调用失败: HTTP {response.status_code}", level="warning")
        return None

    def _parse_json_response(self, content: str) -> Optional[dict]:
        """解析JSON响应"""
        try:
            content = content.strip()

            # 移除代码块标记
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

            return json.loads(content)

        except json.JSONDecodeError:
            return None

    def _log(self, message: str, level: str = "info"):
        """记录日志"""
        if self.logger:
            if level == "error":
                self.logger.error(message)
            elif level == "warning":
                self.logger.warning(message)
            else:
                self.logger.info(message)