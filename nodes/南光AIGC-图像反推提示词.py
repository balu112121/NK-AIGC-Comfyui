# NK-AIGC-Comfyui/nodes/image_to_prompt_node.py

import os

# 强制镜像站，必须在导入 transformers 之前设置
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

import torch
import numpy as np
from PIL import Image
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor

# 模型缓存，避免重复加载
_QWEN_CACHE = {
    "model": None,
    "processor": None,
    "model_id": None,
    "device": None,
}


def _tensor_to_pil(image_tensor: torch.Tensor) -> Image.Image:
    """ComfyUI IMAGE 张量 (B, H, W, C) -> PIL Image"""
    if image_tensor.dim() == 4:
        image_tensor = image_tensor[0]
    np_image = (image_tensor.cpu().numpy() * 255.0).clip(0, 255).astype(np.uint8)
    return Image.fromarray(np_image)


def _get_qwen(model_id: str):
    """延迟加载 Qwen2.5-VL，首次运行从 hf-mirror.com 自动下载。"""
    device = "cuda" if torch.cuda.is_available() else "cpu"

    if (
        _QWEN_CACHE["model"] is not None
        and _QWEN_CACHE["model_id"] == model_id
        and _QWEN_CACHE["device"] == device
    ):
        return _QWEN_CACHE["processor"], _QWEN_CACHE["model"]

    try:
        processor = AutoProcessor.from_pretrained(model_id)
        model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            model_id,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        )
        model.to(device)
        model.eval()
    except Exception as e:
        raise RuntimeError(
            f"加载模型 {model_id} 失败：{e}\n"
            "【排查建议】\n"
            "1. 确认网络可正常访问 https://hf-mirror.com\n"
            "2. 确认已安装 transformers>=4.49.0：\n"
            "   pip install \"transformers>=4.49.0\" --upgrade\n"
            "3. 如需手动预下载，在终端执行：\n"
            f'   set HF_ENDPOINT=https://hf-mirror.com && python -c "from transformers import AutoProcessor; AutoProcessor.from_pretrained(\'{model_id}\')"'
        ) from e

    _QWEN_CACHE.update(
        model=model,
        processor=processor,
        model_id=model_id,
        device=device,
    )
    return processor, model


class NKImageToPrompt:
    """
    南光AIGC-图像反推提示词
    输入：参考图（IMAGE）
    输出：提示词（STRING）
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "参考图": ("IMAGE",),
                "模型": (
                    [
                        "Qwen/Qwen2.5-VL-3B-Instruct",
                        "Qwen/Qwen2.5-VL-7B-Instruct",
                    ],
                    {
                        "default": "Qwen/Qwen2.5-VL-3B-Instruct",
                        "tooltip": "3B 适合 12GB 显存；7B 精度更高但需更多显存（首次运行从 hf-mirror.com 下载）",
                    },
                ),
                "最大长度": (
                    "INT",
                    {"default": 512, "min": 32, "max": 1024, "step": 32},
                ),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("提示词",)
    FUNCTION = "generate_prompt"
    CATEGORY = "南光AIGC/提示词"

    def generate_prompt(self, 参考图, 模型, 最大长度):
        # 1. 加载模型（首次运行自动镜像下载）
        processor, model = _get_qwen(模型)
        device = next(model.parameters()).device

        # 2. 张量转 PIL
        pil_image = _tensor_to_pil(参考图)

        # 3. 构建“反向提示词工程”指令，引导输出长而结构化的描述
        instruction = (
            "You are an expert AI art prompt engineer. "
            "Analyze the provided image and write a VERY DETAILED, comma-separated prompt "
            "that could be used to reproduce this exact image in Stable Diffusion or a similar model. "
            "Include: subject, character details (if any), clothing, pose, composition, background, environment, "
            "lighting, color palette, art style, camera angle, lens, depth of field, rendering quality, and any other visual details. "
            "Aim for a long and comprehensive prompt (up to 500 words). "
            "Return ONLY the prompt text, no explanations, no markdown, no quotes."
        )

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": pil_image},
                    {"type": "text", "text": instruction},
                ],
            }
        ]

        # 4. 多模态推理
        text = processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = processor(
            text=[text],
            images=[pil_image],
            padding=True,
            return_tensors="pt",
        ).to(device)

        with torch.no_grad():
            output_ids = model.generate(
                **inputs,
                max_new_tokens=最大长度,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
            )

        # 5. 解码，只取新生成的 token
        generated_ids = output_ids[:, inputs["input_ids"].shape[1]:]
        prompt = processor.batch_decode(
            generated_ids, skip_special_tokens=True
        )[0].strip()

        # 6. 清洗
        prompt = prompt.strip().strip('"').strip("'")
        if prompt.lower().startswith("prompt:"):
            prompt = prompt[7:].strip()

        if not prompt:
            prompt = "a detailed high quality image"

        return (prompt,)


NODE_CLASS_MAPPINGS = {
    "NKImageToPrompt": NKImageToPrompt,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "NKImageToPrompt": "南光AIGC-图像反推提示词",
}