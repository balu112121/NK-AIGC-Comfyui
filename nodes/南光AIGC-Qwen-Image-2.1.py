# NK-AIGC-Comfyui/nodes/qwen_image_21_pro.py

import base64
import io
import json
import os

import numpy as np
import requests
import torch
from PIL import Image

# 修正：使用官方原生同步多模态生成端点
DASHSCOPE_MULTIMODAL_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
MODEL_ID = "qwen-image-2.1-pro"

RATIO_TO_SIZE = {
    "1:1": "1024*1024",
    "16:9": "1280*720",
    "9:16": "720*1280",
    "4:3": "1024*768",
    "3:4": "768*1024",
    "3:2": "1152*768",
    "2:3": "768*1152",
    "自动": None,  # 自动让模型根据提示词决定分辨率
}


def _tensor_to_base64(tensor: torch.Tensor) -> str:
    """将 ComfyUI 的 IMAGE 张量转为 Base64 Data URL"""
    if tensor is None:
        return ""
    if tensor.dim() == 4:
        img_np = tensor[0].cpu().numpy()
    else:
        img_np = tensor.cpu().numpy()
    img_np = (img_np * 255.0).clip(0, 255).astype(np.uint8)
    if img_np.shape[-1] == 1:
        img_np = img_np.squeeze(-1)
        pil_img = Image.fromarray(img_np, mode="L")
    else:
        pil_img = Image.fromarray(img_np, mode="RGB")
    buffer = io.BytesIO()
    pil_img.save(buffer, format="PNG")
    b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"


def _download_image(url: str) -> torch.Tensor:
    """下载网络图片转为 IMAGE 张量"""
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    pil_img = Image.open(io.BytesIO(resp.content)).convert("RGB")
    arr = np.array(pil_img).astype(np.float32) / 255.0
    return torch.from_numpy(arr).unsqueeze(0)


class QwenImage21ProNode:
    @classmethod
    def INPUT_TYPES(cls):
        optional_images = {}
        for i in range(1, 10):
            optional_images[f"图像{i}"] = ("IMAGE",)

        return {
            "required": {
                "提示词": ("STRING", {
                    "multiline": True,
                    "default": "南光AIGC丨AI绘画提示词、模型、图像、音频、视频、工作流定制，节点软件开发服务。",
                }),
                "API密钥": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "tooltip": "阿里云百炼 API Key，留空则尝试读取环境变量 DASHSCOPE_API_KEY",
                }),
                "比例": (list(RATIO_TO_SIZE.keys()), {
                    "default": "自动",
                }),
                "张数": ("INT", {
                    "default": 1,
                    "min": 1,
                    "max": 6,
                    "step": 1,
                }),
            },
            "optional": {
                "图像": ("IMAGE",),
                **optional_images,
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("图像",)
    FUNCTION = "generate"
    CATEGORY = "南光AIGC/千问"

    def generate(self, 提示词, API密钥, 比例, 张数,
                 图像=None, 图像1=None, 图像2=None, 图像3=None,
                 图像4=None, 图像5=None, 图像6=None, 图像7=None,
                 图像8=None, 图像9=None):

        api_key = (API密钥 or "").strip() or os.environ.get("DASHSCOPE_API_KEY", "")
        if not api_key:
            raise ValueError("未提供 API 密钥。请在节点中填写或在环境变量中配置 DASHSCOPE_API_KEY。")

        # 构建用户消息内容
        content_list = [{"text": 提示词}]

        # 收集输入的图像
        image_tensors = [
            图像, 图像1, 图像2, 图像3, 图像4,
            图像5, 图像6, 图像7, 图像8, 图像9,
        ]
        for t in image_tensors:
            if t is not None:
                b64 = _tensor_to_base64(t)
                if b64:
                    content_list.append({"image": b64})

        # 官方原生多模态请求体参数
        parameters = {"n": int(张数)}
        size_str = RATIO_TO_SIZE.get(比例)
        if size_str:
            parameters["size"] = size_str

        payload = {
            "model": MODEL_ID,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": content_list
                    }
                ]
            },
            "parameters": parameters
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            resp = requests.post(DASHSCOPE_MULTIMODAL_URL, headers=headers, json=payload, timeout=300)
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"请求阿里云百炼失败：{e}") from e

        if resp.status_code != 200:
            raise RuntimeError(f"API 返回错误（HTTP {resp.status_code}）：{resp.text[:800]}")

        data = resp.json()
        
        # 解析多模态生成结果
        output = data.get("output", {})
        choices = output.get("choices", [])
        if not choices:
            raise RuntimeError(f"API 未返回有效数据。完整响应：{json.dumps(data, ensure_ascii=False)[:800]}")

        content_items = choices[0].get("message", {}).get("content", [])
        
        tensors = []
        for item in content_items:
            url = item.get("image")
            if url:
                tensors.append(_download_image(url))

        if not tensors:
            raise RuntimeError("未能从 API 响应中获取任何有效图像。")

        result = torch.cat(tensors, dim=0) if len(tensors) > 1 else tensors[0]
        return (result,)


NODE_CLASS_MAPPINGS = {
    "NK_AIGC_QwenImage21Pro": QwenImage21ProNode,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "NK_AIGC_QwenImage21Pro": "南光AIGC-Qwen-Image-2.1",
}