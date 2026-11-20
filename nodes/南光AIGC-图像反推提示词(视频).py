import base64
import io

import numpy as np
import torch
from PIL import Image
from openai import OpenAI

DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

DEFAULT_INSTRUCTION = (
    "请详细描述这段视频或图像的内容，包括场景、人物、动作、物体、风格、光线、色彩、镜头运动等，"
    "生成一段适合用于 AI 图像或视频生成的提示词。请直接输出提示词，不要额外解释。"
)

MIN_VIDEO_FRAMES = 4


class NKImageToPromptVideo:
    """
    南光AIGC-图像反推提示词(视频)
    自动判断模式：
      - 有 VIDEO 输入 → 视频模式（补足至少 4 帧）
      - 只有 IMAGE 且批次 ≥ 4 → 视频模式
      - 只有单张 IMAGE → 图像模式（彻底避开视频帧数限制）
    """

    CATEGORY = "南光AIGC/千问"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "api_key": ("STRING", {
                    "multiline": False,
                    "default": "",
                    "tooltip": "阿里云百炼 API Key（sk-...）",
                }),
                "model": (["Qwen3-VL-Plus", "Qwen3-VL-Embedding"], {
                    "default": "Qwen3-VL-Plus",
                }),
            },
            "optional": {
                "image": ("IMAGE",),
                "video": ("VIDEO",),
                "custom_instruction": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "tooltip": "自定义反推指令，留空则使用默认指令",
                }),
                "max_frames": ("INT", {
                    "default": 8,
                    "min": 1,
                    "max": 32,
                    "step": 1,
                    "tooltip": "从视频中均匀采样的最大帧数（仅视频模式生效）",
                }),
                "base_url": ("STRING", {
                    "multiline": False,
                    "default": DEFAULT_BASE_URL,
                    "tooltip": "百炼 OpenAI 兼容端点",
                }),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("文本",)
    FUNCTION = "generate_prompt"
    OUTPUT_NODE = False

    def generate_prompt(
        self,
        api_key: str,
        model: str,
        image=None,
        video=None,
        custom_instruction: str = "",
        max_frames: int = 8,
        base_url: str = DEFAULT_BASE_URL,
    ):
        # 强制转为纯字符串并去除空格
        api_key = str(api_key).strip() if api_key else ""
        if not api_key:
            raise ValueError("请填写或连接阿里云百炼 API Key。")

        if "embedding" in model.lower():
            raise ValueError("Qwen3-VL-Embedding 是向量化模型，不支持文本生成。请切换为 Qwen3-VL-Plus。")

        model_name = "qwen3-vl-plus"

        # 1. 收集帧
        frames = []
        if video is not None:
            frames.extend(self._frames_from_video(video, max_frames))
        if image is not None:
            frames.extend(self._frames_from_tensor(image, max_frames))

        if not frames:
            raise ValueError("请至少连接图像或视频输入。")

        instruction = (custom_instruction or "").strip() or DEFAULT_INSTRUCTION
        client = OpenAI(api_key=api_key, base_url=base_url)

        # 2. 决定模式
        if video is not None or len(frames) >= MIN_VIDEO_FRAMES:
            # 视频模式
            mode_tag = "视频"
            frames = self._subsample(frames, max_frames)
            frames = self._ensure_min_frames(frames, MIN_VIDEO_FRAMES)
            content = [
                {"type": "video", "video": [self._pil_to_data_url(f) for f in frames]},
                {"type": "text", "text": instruction},
            ]
        else:
            # 图像模式（单张或不足4张）
            mode_tag = "图像"
            content = [
                {"type": "image_url", "image_url": {"url": self._pil_to_data_url(frames[0])}},
                {"type": "text", "text": instruction},
            ]

        # 3. 调用 API
        try:
            print(f"[NK-AIGC] 图像反推(视频) 启动 | 模式={mode_tag} | 帧数={len(frames)}")
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": content}],
                max_tokens=1024,
                temperature=0.7,
            )
        except Exception as e:
            raise RuntimeError(f"调用百炼 API 失败（模式：{mode_tag}，帧数：{len(frames)}）：{e}") from e

        text = (response.choices[0].message.content or "").strip()
        if not text:
            text = "（模型未返回文本内容，请重试。）"

        print(f"[NK-AIGC] 图像反推(视频) 完成 | 输出长度: {len(text)}")
        return (text,)

    # ── 工具方法 ────────────────────────────────────────────
    @staticmethod
    def _frames_from_video(video, max_frames: int):
        try:
            components = video.get_components()
            images = components.images
            frames = []
            total = images.shape[0]
            step = max(1, total // max_frames) if total > max_frames else 1
            for i in range(0, total, step):
                if len(frames) >= max_frames:
                    break
                arr = (images[i].cpu().numpy() * 255).clip(0, 255).astype(np.uint8)
                frames.append(Image.fromarray(arr))
            return frames
        except Exception as e:
            raise RuntimeError(f"无法从视频提取帧: {e}") from e

    @staticmethod
    def _frames_from_tensor(tensor, max_frames: int):
        frames = []
        total = tensor.shape[0]
        step = max(1, total // max_frames) if total > max_frames else 1
        for i in range(0, total, step):
            if len(frames) >= max_frames:
                break
            arr = (tensor[i].cpu().numpy() * 255).clip(0, 255).astype(np.uint8)
            frames.append(Image.fromarray(arr))
        return frames

    @staticmethod
    def _subsample(frames, max_frames: int):
        if len(frames) <= max_frames:
            return frames
        indices = np.linspace(0, len(frames) - 1, max_frames, dtype=int)
        return [frames[i] for i in indices]

    @staticmethod
    def _ensure_min_frames(frames, min_count: int):
        if len(frames) >= min_count:
            return frames
        result = list(frames)
        idx = 0
        while len(result) < min_count:
            result.append(frames[idx % len(frames)])
            idx += 1
        return result

    @staticmethod
    def _pil_to_data_url(img: Image.Image) -> str:
        # 【新增】自动限制图片最大边长为 1024，防止 base64 体积过大导致 API 超限
        max_size = 1024
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/jpeg;base64,{b64}"


NODE_CLASS_MAPPINGS = {"NK_ImageToPromptVideo": NKImageToPromptVideo}
NODE_DISPLAY_NAME_MAPPINGS = {"NK_ImageToPromptVideo": "南光AIGC-图像反推提示词(视频)"}