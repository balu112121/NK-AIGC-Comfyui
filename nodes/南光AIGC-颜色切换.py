# NK-AIGC-Comfyui/nodes/color_switch_node.py
# -*- coding: utf-8 -*-
"""
南光AIGC-颜色切换（子节点）
- 输入：颜色1 / 颜色2 / 颜色3 / 颜色4（字符串，十六进制或颜色名均可）
- 下拉框：颜色选择（1 / 2 / 3 / 4，默认 1）
- 输出：颜色（STRING，等于所选编号对应的输入颜色）
"""

from __future__ import annotations


class NKColorSwitch:
    """根据数字选择输出对应颜色。"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "颜色1": ("STRING", {"default": "#FF0000", "multiline": False}),
                "颜色2": ("STRING", {"default": "#00FF00", "multiline": False}),
                "颜色3": ("STRING", {"default": "#0000FF", "multiline": False}),
                "颜色4": ("STRING", {"default": "#FFFFFF", "multiline": False}),
                "颜色选择": (["1", "2", "3", "4"], {"default": "1"}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("颜色",)
    FUNCTION = "switch_color"
    CATEGORY = "南光AIGC/证件照"

    def switch_color(self, 颜色1, 颜色2, 颜色3, 颜色4, 颜色选择):
        color_map = {
            "1": 颜色1,
            "2": 颜色2,
            "3": 颜色3,
            "4": 颜色4,
        }
        # 兼容数字类型与异常值，异常时回退到颜色1
        selected = color_map.get(str(颜色选择).strip(), 颜色1)
        return (selected,)


NODE_CLASS_MAPPINGS = {
    "NKColorSwitch": NKColorSwitch,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "NKColorSwitch": "南光AIGC-颜色切换",
}