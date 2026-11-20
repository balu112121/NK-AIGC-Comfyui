# nodes/南光AIGC-豆包图像生成.py
import base64
import io
import json
import urllib.error
import urllib.request

import numpy as np
import torch
from PIL import Image

ARK_API_URL = "https://ark.cn-beijing.volces.com/api/v3/images/generations"

DOUBAO_MODEL_IDS = {
    "Seedream 5.5":       "doubao-seedream-5-5-261028",
    "Seedream 5.0 Pro":   "doubao-seedream-5-0-pro-260628",
    "Seedream 5.0 Flash": "doubao-seedream-5-0-flash-260915",
    "Seedream 4.5":       "doubao-seedream-4-5-251128",
    "Seedream 4.0":       "doubao-seedream-4-0-250828",
}

MAX_REF_IMAGES = 10

# 比例 → "WxH" 字符串（API 只接受字符串形式的尺寸）
ASPECT_RATIOS = {
    "1:1":  "2048x2048",
    "4:3":  "2304x1728",
    "3:4":  "1728x2304",
    "16:9": "2560x1440",
    "9:16": "1440x2560",
    "3:2":  "2496x1664",
    "2:3":  "1664x2496",
    "21:9": "3024x1296",
}

BACKGROUND_OPTIONS = ["保留背景", "透明背景"]

# 支持组图（sequential_image_generation）的模型[reference:1][reference:2]
MODELS_WITH_GROUP_GENERATION = {"Seedream 4.5", "Seedream 4.0"}

# 需要 output_format=png 才能保留透明背景的模型（5.0 系列）[reference:3]
MODELS_NEED_PNG_FOR_TRANSPARENT = {"Seedream 5.0 Pro", "Seedream 5.0 Flash"}


def _tensor_to_pil(tensor: torch.Tensor) -> Image.Image:
    arr = (tensor.cpu().numpy() * 255.0).clip(0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def _pil_to_base64(img: Image.Image, fmt: str = "PNG") -> str:
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _b64_to_tensor(b64_str: str) -> torch.Tensor:
    raw = base64.b64decode(b64_str)
    pil = Image.open(io.BytesIO(raw))
    if pil.mode in ("RGBA", "LA", "P"):
        pil = pil.convert("RGBA")
        bg = Image.new("RGB", pil.size, (255, 255, 255))
        bg.paste(pil, mask=pil.split()[-1])
        pil = bg
    else:
        pil = pil.convert("RGB")
    arr = np.array(pil).astype(np.float32) / 255.0
    return torch.from_numpy(arr).unsqueeze(0)


class NK_AIGC_DoubaoImageGeneration:
    """南光AIGC-豆包图像生成（子节点）"""

    @classmethod
    def INPUT_TYPES(cls):
        optional = {"image": ("IMAGE", {"tooltip": "参考图 1"})}
        for i in range(1, MAX_REF_IMAGES):
            optional[f"image{i}"] = ("IMAGE", {"tooltip": f"参考图 {i + 1}"})

        return {
            "required": {
                "prompt": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "tooltip": "提示词，描述你想要生成的图像内容",
                }),
                "api_key": ("STRING", {
                    "default": "",
                    "tooltip": "火山方舟 API Key",
                }),
                "model": (list(DOUBAO_MODEL_IDS.keys()), {
                    "default": "Seedream 5.5",
                    "tooltip": "选择豆包 Seedream 模型",
                }),
                "aspect_ratio": (list(ASPECT_RATIOS.keys()), {
                    "default": "1:1",
                    "tooltip": "输出图像比例",
                }),
                "background": (BACKGROUND_OPTIONS, {
                    "default": "保留背景",
                    "tooltip": "透明背景需模型支持，输出会合成到白底",
                }),
                "num_images": ("INT", {
                    "default": 1,
                    "min": 1,
                    "max": 10,
                    "step": 1,
                    "tooltip": "生成张数（仅 Seedream 4.5 / 4.0 支持组图）",
                }),
            },
            "optional": optional,
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("图像",)
    FUNCTION = "generate"
    CATEGORY = "南光AIGC/豆包"

    def generate(self, prompt, api_key, model, aspect_ratio, background,
                 num_images, **kwargs):
        # ── 1. 收集 IMAGE 输入（最多 10 张）──
        ref_tensors = []
        for name in ["image"] + [f"image{i}" for i in range(1, MAX_REF_IMAGES)]:
            t = kwargs.get(name)
            if t is None:
                continue
            batch = t if t.dim() == 4 else t.unsqueeze(0)
            for i in range(batch.shape[0]):
                if len(ref_tensors) >= MAX_REF_IMAGES:
                    break
                ref_tensors.append(batch[i])
            if len(ref_tensors) >= MAX_REF_IMAGES:
                break

        ref_b64 = [_pil_to_base64(_tensor_to_pil(t)) for t in ref_tensors]

        # ── 2. 构造 payload ──
        model_id = DOUBAO_MODEL_IDS.get(model, DOUBAO_MODEL_IDS["Seedream 5.5"])
        size_str = ASPECT_RATIOS.get(aspect_ratio, "2048x2048")

        payload = {
            "model": model_id,
            "prompt": (prompt or "").strip(),
            "response_format": "b64_json",
            "size": size_str,  # 关键修正：字符串格式
        }
        if ref_b64:
            payload["image"] = [f"data:image/png;base64,{b}" for b in ref_b64]

        # 背景
        if background == "透明背景":
            payload["background"] = "transparent"
            # 5.0 系列透明背景需要 output_format=png[reference:5]
            if model in MODELS_NEED_PNG_FOR_TRANSPARENT:
                payload["output_format"] = "png"

        # 张数：仅对支持组图的模型启用[reference:6]
        n = max(1, min(int(num_images), 10))
        if n > 1 and model in MODELS_WITH_GROUP_GENERATION:
            payload["sequential_image_generation"] = "auto"
            payload["sequential_image_generation_options"] = {"max_images": n}
        # 不支持组图的模型，即使 num_images > 1 也静默生成 1 张，不传非法参数

        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            ARK_API_URL,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {(api_key or '').strip()}",
            },
            method="POST",
        )

        # ── 3. 调用 API ──
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                result = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            err_code = ""
            try:
                err_code = json.loads(err_body).get("error", {}).get("code", "")
            except json.JSONDecodeError:
                pass
            if err_code == "ModelNotOpen":
                raise RuntimeError(
                    f"模型 {model_id} 未开通。请前往火山方舟控制台 → 开通管理，"
                    f"开通该模型服务后重试。原始返回：{err_body[:800]}"
                ) from e
            raise RuntimeError(
                f"豆包 API 请求失败（HTTP {e.code}）：{err_body[:2000]}"
            ) from e
        except Exception as e:
            raise RuntimeError(f"豆包 API 请求异常：{e}") from e

        # ── 4. 解析输出 ──
        data_list = result.get("data") or []
        if not data_list:
            raise RuntimeError(
                f"豆包 API 未返回图像数据："
                f"{json.dumps(result, ensure_ascii=False)[:2000]}"
            )

        tensors = []
        for item in data_list:
            b64 = item.get("b64_json")
            if b64:
                tensors.append(_b64_to_tensor(b64))
        if not tensors:
            raise RuntimeError("豆包 API 返回了数据，但没有 b64_json 图像字段。")

        return (torch.cat(tensors, dim=0),)


NODE_CLASS_MAPPINGS = {
    "NK_AIGC_DoubaoImageGeneration": NK_AIGC_DoubaoImageGeneration,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "NK_AIGC_DoubaoImageGeneration": "南光AIGC-豆包图像生成",
}