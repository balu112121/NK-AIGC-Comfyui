# NK-AIGC-Comfyui/nodes/qwen_image_prompt_optimizer.py

import base64
import io
import json
import os
import re
from pathlib import Path
from typing import Any, Optional

import numpy as np
import torch

# ── 延迟导入 llama_cpp，避免未安装时整个插件加载失败 ──────────
_llama_cpp = None
_MTMDChatHandler = None

def _ensure_llama_cpp():
    global _llama_cpp, _MTMDChatHandler
    if _llama_cpp is not None:
        return
    from llama_cpp import Llama
    from llama_cpp.llama_chat_format import MTMDChatHandler
    _llama_cpp = Llama
    _MTMDChatHandler = MTMDChatHandler


# ══════════════════════════════════════════════════════════════
# ── 模型目录与文件常量 ────────────────────────────────────────
# ══════════════════════════════════════════════════════════════

_NODE_DIR = Path(__file__).parent.parent
_MODEL_DIR = Path(
    os.environ.get(
        "QWEN_PE_MODEL_DIR",
        str(_NODE_DIR / "models" / "llm" / "qwenimage-pe"),
    )
)

T2I_MODEL_FILE = "Qwen-Image-2.1-PE-T2I.Q5_K_M.gguf"
I2I_MODEL_FILE = "Qwen-Image-2.1-PE-I2I.Q5_K_M.gguf"
VISION_MODEL_FILE = "Qwen-Image-2.1-PE-I2I.mmproj-bf16.gguf"
SYSTEM_PROMPT_FILE = "system_prompt.txt"


def _model_path(filename: str) -> Path:
    return _MODEL_DIR / filename


def _read_system_prompt() -> str:
    path = _model_path(SYSTEM_PROMPT_FILE)
    if path.exists():
        return path.read_text(encoding="utf-8")
    # 兜底：模型未放置 system_prompt.txt 时使用简化版约束
    return (
        "You are a prompt rewriter for Qwen-Image-2.1. "
        "Input may be text and/or one or more images. "
        "Output ONE JSON object only, no markdown, with keys: "
        "\"rewritten_prompt\" (detailed English image prompt) and "
        "\"wh_ratio\" (e.g. \"1:1\", \"16:9\", \"9:16\")."
    )


# ══════════════════════════════════════════════════════════════
# ── 图像张量 → base64 data URI ────────────────────────────────
# ══════════════════════════════════════════════════════════════

def _comfy_image_to_data_uri(image: torch.Tensor) -> Optional[str]:
    """将 ComfyUI IMAGE 张量 (B,H,W,C) 转为 data URI；仅取第一张。"""
    if image is None:
        return None
    try:
        from PIL import Image

        arr = image.cpu().numpy()
        if arr.ndim == 4:
            arr = arr[0]
        if arr.ndim != 3:
            return None
        arr = np.clip(arr * 255.0, 0, 255).astype(np.uint8)
        pil = Image.fromarray(arr)
        buffer = io.BytesIO()
        pil.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return f"data:image/png;base64,{encoded}"
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════
# ── 模型加载（带简单缓存与卸载） ──────────────────────────────
# ══════════════════════════════════════════════════════════════

_model_cache: dict[str, Any] = {}


def _load_model(model_path: Path, mmproj_path: Optional[Path] = None, n_ctx: int = 16384):
    _ensure_llama_cpp()

    key = f"{model_path}|{mmproj_path}"
    if key in _model_cache:
        return _model_cache[key]

    if not model_path.exists():
        raise FileNotFoundError(
            f"未找到模型文件：{model_path}\n"
            f"请将 {model_path.name} 放入 {_MODEL_DIR}，"
            f"或设置环境变量 QWEN_PE_MODEL_DIR 指向模型目录。"
        )

    kwargs: dict[str, Any] = {
        "model_path": str(model_path),
        "n_ctx": n_ctx,
        "n_gpu_layers": -1,
        "verbose": False,
        "n_threads": max(1, (os.cpu_count() or 4) // 2),
    }

    if mmproj_path is not None:
        if not mmproj_path.exists():
            raise FileNotFoundError(
                f"未找到视觉模型文件：{mmproj_path}\n"
                f"图生图任务需要 {VISION_MODEL_FILE} 与 I2I 模型配合使用。"
            )
        kwargs["chat_handler"] = _MTMDChatHandler(
            clip_model_path=str(mmproj_path),
            verbose=False,
        )

    llm = _llama_cpp(**kwargs)
    _model_cache[key] = llm
    return llm


def _unload_all_models():
    for llm in _model_cache.values():
        try:
            llm.close()
        except Exception:
            pass
    _model_cache.clear()


# ══════════════════════════════════════════════════════════════
# ── 推理与结果解析 ────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════

def _build_messages(user_prompt: str, image_data_uri: Optional[str], skill_text: str) -> list:
    system_prompt = _read_system_prompt()
    if skill_text.strip():
        system_prompt += f"\n\nAdditional user skill / style instructions:\n{skill_text.strip()}"

    user_content: list[dict[str, Any]] = []
    if image_data_uri:
        user_content.append({
            "type": "image_url",
            "image_url": {"url": image_data_uri},
        })
    user_content.append({"type": "text", "text": user_prompt or "请优化提示词。"})

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content if image_data_uri else (user_prompt or "请优化提示词。")},
    ]


def _parse_model_output(raw: str) -> tuple[str, dict]:
    text = (raw or "").strip()
    # 去掉可能的 markdown 代码围栏
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    try:
        payload = json.loads(text)
    except Exception:
        # 兜底：尝试从文本中提取第一个 JSON 对象
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                payload = json.loads(match.group(0))
            except Exception:
                payload = {}
        else:
            payload = {}

    if not isinstance(payload, dict):
        payload = {}

    prompt = str(payload.get("rewritten_prompt") or payload.get("prompt") or text).strip()
    if not prompt:
        prompt = text or "未生成有效提示词。"

    return prompt, payload


# ══════════════════════════════════════════════════════════════
# ── ComfyUI 节点类 ────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════

class NKQwenImagePromptOptimizer:
    """
    南光AIGC-Qwen-Image-2.1(提示词优化)
    子节点：输入图像 + skill，输出优化后的 prompt 与 json。
    """

    CATEGORY = "南光AIGC/千问"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "文本提示词": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "placeholder": "输入需要优化的提示词，或结合图像让模型反推…",
                    },
                ),
                "文生图模型": (
                    [T2I_MODEL_FILE],
                    {"default": T2I_MODEL_FILE},
                ),
                "图生图模型": (
                    [I2I_MODEL_FILE],
                    {"default": I2I_MODEL_FILE},
                ),
                "视觉模型": (
                    [VISION_MODEL_FILE],
                    {"default": VISION_MODEL_FILE},
                ),
                "输出语言": (
                    ["中文", "English", "自动"],
                    {"default": "中文"},
                ),
                "透明背景": (
                    ["否", "是"],
                    {"default": "否"},
                ),
                "种子值": (
                    "INT",
                    {"default": 42, "min": 0, "max": 0xFFFFFFFFFFFFFFFF},
                ),
                "种子模式": (
                    ["固定", "随机"],
                    {"default": "固定"},
                ),
                "卸载模型": (
                    ["自动", "保持加载", "运行后自动卸载", "运行前后自动卸载"],
                    {"default": "自动"},
                ),
            },
            "optional": {
                "图像": ("IMAGE",),
                "skill": ("STRING", {"forceInput": True}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("prompt", "json")
    FUNCTION = "optimize"
    OUTPUT_NODE = False

    def optimize(
        self,
        文本提示词: str,
        文生图模型: str,
        图生图模型: str,
        视觉模型: str,
        输出语言: str,
        透明背景: str,
        种子值: int,
        种子模式: str,
        卸载模型: str,
        图像: Optional[torch.Tensor] = None,
        skill: Optional[str] = None,
    ):
        # ── 种子处理 ──
        if 种子模式 == "随机":
            import random
            seed = random.randint(0, 0xFFFFFFFFFFFFFFFF)
        else:
            seed = int(种子值)

        # ── 空值保护 ──
        skill_text = skill or ""

        # ── 判断任务类型：有图像 → 图生图；无图像 → 文生图 ──
        has_image = 图像 is not None
        if has_image:
            main_model_path = _model_path(图生图模型)
            mmproj_path = _model_path(视觉模型)
        else:
            main_model_path = _model_path(文生图模型)
            mmproj_path = None  # 纯文生图不需要视觉投影器

        # ── 卸载策略：运行前判断 ──
        if 卸载模型 == "运行前后自动卸载":
            _unload_all_models()
        elif 卸载模型 == "自动":
            # “自动”模式下，检查当前要用的模型是否已在缓存，如果有且不一致则清空
            target_key = f"{main_model_path}|{mmproj_path}"
            if target_key not in _model_cache and len(_model_cache) > 0:
                _unload_all_models()

        # ── 加载模型 ──
        llm = _load_model(main_model_path, mmproj_path=mmproj_path)

        # ── 构造用户提示词（注入语言 / 透明背景约束） ──
        user_prompt_parts = [文本提示词.strip() or "请优化提示词。"]
        if 输出语言 == "中文":
            user_prompt_parts.append("Output the rewritten_prompt in Chinese.")
        elif 输出语言 == "English":
            user_prompt_parts.append("Output the rewritten_prompt in English.")
        # “自动”不追加语言约束，由模型自行判断

        if 透明背景 == "是":
            user_prompt_parts.append(
                "The final prompt must explicitly request a transparent background "
                "(RGBA, alpha channel, no background)."
            )

        user_prompt = "\n".join(user_prompt_parts)

        # ── 图像 → data URI ──
        image_data_uri = _comfy_image_to_data_uri(图像) if has_image else None

        # ── 构造 messages ──
        messages = _build_messages(user_prompt, image_data_uri, skill_text)

        # ── 调用模型 ──
        try:
            response = llm.create_chat_completion(
                messages=messages,
                temperature=0.7,
                top_p=0.95,
                top_k=20,
                min_p=0.0,
                repeat_penalty=1.0,
                max_tokens=4096,
                seed=seed,
            )
            raw_output = response["choices"][0]["message"]["content"]
        except Exception as error:
            raise RuntimeError(f"Qwen-Image-2.1 提示词优化推理失败：{error}") from error

        # ── 解析输出 ──
        prompt, json_payload = _parse_model_output(raw_output)

        # 将原始元信息合并进 JSON，便于下游节点使用
        json_payload.setdefault("seed", seed)
        json_payload.setdefault("task", "i2i" if has_image else "t2i")
        json_payload.setdefault("output_language", 输出语言)
        json_payload.setdefault("transparent_background", 透明背景 == "是")
        json_payload.setdefault("model", main_model_path.name)
        if mmproj_path:
            json_payload.setdefault("vision_model", mmproj_path.name)

        json_text = json.dumps(json_payload, ensure_ascii=False, indent=2)

        # ── 卸载策略：运行后判断 ──
        if 卸载模型 in ("运行后自动卸载", "运行前后自动卸载"):
            _unload_all_models()

        return (prompt, json_text)


# ══════════════════════════════════════════════════════════════
# ── 注册映射 ─────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════

NODE_CLASS_MAPPINGS = {
    "NKQwenImagePromptOptimizer": NKQwenImagePromptOptimizer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "NKQwenImagePromptOptimizer": "南光AIGC-Qwen-Image-2.1(提示词优化)",
}