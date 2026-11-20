# NK-AIGC-Comfyui/nodes/text_prompt_node.py

import os
import json
import time
from pathlib import Path

import folder_paths


CATEGORY = "南光AIGC/文本"

# ── 反推规则库 ──────────────────────────────────────────────
BASE_NEGATIVE = [
    "low quality", "worst quality", "blurry", "pixelated",
    "jpeg artifacts", "noise", "grainy",
]

STYLE_RULES = [
    {
        "triggers": ["anime", "动漫", "二次元", "manga", "漫画"],
        "negative": [
            "photorealistic", "realistic", "3d render",
            "bad anatomy", "extra fingers", "missing fingers",
            "bad hands", "mutated hands", "poorly drawn face",
        ],
    },
    {
        "triggers": ["photo", "photograph", "摄影", "写实", "realistic"],
        "negative": [
            "cartoon", "anime", "illustration", "painting",
            "oversaturated", "oversharpened",
        ],
    },
    {
        "triggers": ["portrait", "人像", "人物", "girl", "woman", "man", "boy"],
        "negative": [
            "bad anatomy", "bad proportions", "deformed face",
            "asymmetrical eyes", "extra limbs", "missing limbs",
            "mutated hands", "fused fingers",
        ],
    },
    {
        "triggers": ["landscape", "风景", "scenery", "architecture", "建筑"],
        "negative": [
            "distorted perspective", "warped lines", "tilted horizon",
            "cluttered composition",
        ],
    },
    {
        "triggers": ["text", "文字", "logo", "标志"],
        "negative": [
            "blurry text", "garbled text", "illegible", "misspelled",
        ],
    },
]


def _auto_negative_from_positive(positive: str) -> str:
    """根据正向提示词反推负向提示词（基础负面词 + 命中规则追加）。"""
    pos_lower = positive.lower()
    result = list(BASE_NEGATIVE)

    for rule in STYLE_RULES:
        if any(trigger in pos_lower for trigger in rule["triggers"]):
            result.extend(rule["negative"])

    seen = set()
    unique = []
    for word in result:
        w = word.strip()
        if w and w.lower() not in seen:
            seen.add(w.lower())
            unique.append(w)

    return ", ".join(unique)


class NKAIGC_PositiveNegativePrompt:
    """
    南光AIGC-正反向提示词
    - 上方正向提示词输入框
    - 下方负向提示词输入框（可为空，为空时自动反推）
    - 输出：正向提示词、负向提示词、保存提示词（格式化文本）
    """

    CATEGORY = CATEGORY
    FUNCTION = "run"
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("正向提示词", "负向提示词", "保存提示词")
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "positive_prompt": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "tooltip": "输入正向提示词",
                    },
                ),
                "negative_prompt": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "tooltip": "输入负向提示词；留空时将根据正向提示词自动反推",
                    },
                ),
            },
            "optional": {
                "auto_save": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": "是否将本次正反向提示词保存到 input/NK-AIGC-Prompts 文件夹",
                    },
                ),
            },
        }

    @classmethod
    def IS_CHANGED(cls, positive_prompt, negative_prompt, auto_save=True):
        # 每次执行都重新运行，确保保存文件始终反映最新输入
        return float("NaN")

    def run(self, positive_prompt, negative_prompt, auto_save=True):
        positive_prompt = positive_prompt.strip()
        negative_prompt = negative_prompt.strip()

        # ── 反推逻辑：负向为空时根据正向生成 ─────────────
        if not negative_prompt:
            negative_prompt = _auto_negative_from_positive(positive_prompt)

        # ── 保存提示词到 input 目录 (JSON 和 txt) ────────
        save_path = ""
        if auto_save:
            save_path = self._save_prompts(positive_prompt, negative_prompt)

        # ── 构建方便直接保存为 txt 的格式化文本 ──────────
        # 这样外接 Save Text 节点时，写入的是提示词内容，而不是文件路径
        formatted_text = f"[正向提示词]\n{positive_prompt}\n\n[负向提示词]\n{negative_prompt}"
        if save_path:
            formatted_text += f"\n\n[自动保存路径]\n{save_path}"

        # 输出：正向、负向、格式化文本
        return (positive_prompt, negative_prompt, formatted_text)

    @staticmethod
    def _save_prompts(positive: str, negative: str) -> str:
        input_dir = folder_paths.get_input_directory()
        save_dir = Path(input_dir) / "NK-AIGC-Prompts"
        save_dir.mkdir(parents=True, exist_ok=True)

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        base_name = f"prompt_{timestamp}"
        file_path = save_dir / f"{base_name}.json"
        counter = 1
        while file_path.exists():
            file_path = save_dir / f"{base_name}_{counter}.json"
            counter += 1

        payload = {
            "positive": positive,
            "negative": negative,
            "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        latest_txt = save_dir / "latest_prompts.txt"
        with open(latest_txt, "w", encoding="utf-8") as f:
            f.write(f"[正向]\n{positive}\n\n[负向]\n{negative}\n")

        return str(file_path)


# ── 本文件的节点注册映射 ───────────────────────────────────
NODE_CLASS_MAPPINGS = {
    "NKAIGC_PositiveNegativePrompt": NKAIGC_PositiveNegativePrompt,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "NKAIGC_PositiveNegativePrompt": "南光AIGC-正反向提示词",
}

__all__ = [
    "NKAIGC_PositiveNegativePrompt",
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
    "CATEGORY",
]