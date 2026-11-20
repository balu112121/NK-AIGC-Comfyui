import os
import io
import base64

import numpy as np
from PIL import Image
from openai import OpenAI

SYSTEM_PROMPT = """你是资深小红书爆款文案操盘手，擅长根据一张图片或一段文字素材，写出高点击、高互动的种草笔记。
请严格按以下要求输出：
1. 标题：15字以内，带1-2个emoji；使用数字、痛点、对比、悬念或好奇钩子，让人忍不住点开
2. 正文：第一人称口语化，短句分段，每段不超过2行，用emoji分隔；开头3秒抓住注意力，中间讲场景痛点+真实体验+解决方案，结尾一句强互动引导（提问/求同款/收藏）
3. 标签：3-5个相关话题，用#开头，兼顾大流量词和精准长尾词
4. 禁止书面语、禁止“首先其次最后”、禁止AI腔、禁止空泛形容词
输出格式：
标题
（空行）
正文
（空行）
标签"""


def _image_to_data_url(image) -> str:
    if image is None:
        return ""
    if image.dim() == 4:
        image = image[0]
    arr = (image.detach().cpu().numpy() * 255.0).clip(0, 255).astype(np.uint8)
    if arr.ndim == 3 and arr.shape[-1] == 1:
        arr = np.repeat(arr, 3, axis=-1)
    pil = Image.fromarray(arr)
    buf = io.BytesIO()
    pil.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"


class NKXHSWriter:
    CATEGORY = "南光AIGC/文案"
    FUNCTION = "generate"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("文案",)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "api_key": ("STRING", {"default": "", "multiline": False}),
            },
            "optional": {
                "image": ("IMAGE",),
                "text": ("STRING", {"forceInput": True}),
                "topic": ("STRING", {"multiline": True, "default": ""}),
                "audience": ("STRING", {"default": "", "multiline": False}),
                "temperature": ("FLOAT", {"default": 1.1, "min": 0.1, "max": 1.5, "step": 0.1}),
                # 下拉框核心，列表格式
                "model": (["qwen3-vl-plus", "qwen3.8-flash"],),
                "base_url": ("STRING", {"default": "https://dashscope.aliyuncs.com/compatible-mode/v1"}),
            },
        }

    def generate(self, api_key, image=None, text=None, topic="", audience="",
                 temperature=1.1, model="qwen3-vl-plus",
                 base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"):
        key = (api_key or "").strip() \
            or os.environ.get("DASHSCOPE_API_KEY", "") \
            or os.environ.get("OPENAI_API_KEY", "")

        text = (text or "").strip()
        topic = (topic or "").strip()
        audience = (audience or "").strip()
        has_image = image is not None

        if not key:
            msg = "⚠️ 未配置API密钥：请在节点“API密钥”中填入，或设置环境变量 DASHSCOPE_API_KEY。"
            return {"ui": {"text": [msg]}, "result": (msg,)}

        if not has_image and not text and not topic:
            msg = "⚠️ 请至少提供一项输入：连接“图像”、连接“文本”，或填写“主题”。"
            return {"ui": {"text": [msg]}, "result": (msg,)}

        try:
            data_url = _image_to_data_url(image) if has_image else ""
            parts = ["请根据以下素材生成一篇爆款小红书文案。"]
            if topic: parts.append(f"主题：{topic}")
            if audience: parts.append(f"目标人群：{audience}")
            if text: parts.append(f"文本素材：{text}")
            if has_image: parts.append("已附上图片素材，请结合图片内容创作。")
            parts.append("要求：标题抓眼、正文口语化有情绪、结尾引导互动、标签精准。")
            user_text = "\n".join(parts)

            content = [{"type": "text", "text": user_text}]
            if data_url:
                content.append({"type": "image_url", "image_url": {"url": data_url}})

            client = OpenAI(
                api_key=key,
                base_url=base_url.strip() or "https://dashscope.aliyuncs.com/compatible-mode/v1",
            )
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": content},
                ],
                temperature=float(temperature),
            )
            result = (resp.choices[0].message.content or "").strip()
            if not result:
                result = "⚠️ 模型返回为空，请稍后重试。"
        except Exception as e:
            result = f"⚠️ 生成失败：{e}"

        return {"ui": {"text": [result]}, "result": (result,)}

NODE_CLASS_MAPPINGS = {"NKXHSWriter": NKXHSWriter}
NODE_DISPLAY_NAME_MAPPINGS = {"NKXHSWriter": "南光AIGC-小红书文案"}