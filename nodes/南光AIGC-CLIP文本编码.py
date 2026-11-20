# NK-AIGC-Comfyui/nodes/clip_text_encode_node.py
"""南光AIGC-CLIP文本编码
一次性输入正向 / 负向提示词，编码后同时输出两个 CONDITIONING。
兼容 ComfyUI 新旧版本（SD1.5 / SDXL / SD3 / Flux 等 CLIP 编码接口）。
"""

NODE_KEY = "NKCLIPTextEncode"
DISPLAY_NAME = "南光AIGC-CLIP文本编码"
CATEGORY = "南光AIGC/条件"


def _encode_text(clip, text: str):
    """将文本编码为 ComfyUI 的 CONDITIONING 结构。"""
    text = text or ""
    tokens = clip.tokenize(text)

    # 新版本接口：SDXL / SD3 / Flux 等会自动处理 pooled 输出
    if hasattr(clip, "encode_from_tokens_scheduled"):
        return clip.encode_from_tokens_scheduled(tokens)

    # 老版本接口：手动包装 pooled_output
    try:
        cond, pooled = clip.encode_from_tokens(tokens, return_pooled=True)
        return [[cond, {"pooled_output": pooled}]]
    except TypeError:
        cond = clip.encode_from_tokens(tokens)
        return [[cond, {}]]


class NKCLIPTextEncode:
    """同时编码正向与负向提示词，输出两个 CONDITIONING。"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "clip": ("CLIP",),
                "正向提示词": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "dynamicPrompts": True,
                    },
                ),
                "负向提示词": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "dynamicPrompts": True,
                    },
                ),
            }
        }

    RETURN_TYPES = ("CONDITIONING", "CONDITIONING")
    RETURN_NAMES = ("正面条件", "负面条件")
    FUNCTION = "encode"
    CATEGORY = CATEGORY

    def encode(self, clip, 正向提示词, 负向提示词):
        positive = _encode_text(clip, 正向提示词)
        negative = _encode_text(clip, 负向提示词)
        return (positive, negative)


# ── 节点注册映射（由根目录 __init__.py 自动合并） ──
NODE_CLASS_MAPPINGS = {NODE_KEY: NKCLIPTextEncode}
NODE_DISPLAY_NAME_MAPPINGS = {NODE_KEY: DISPLAY_NAME}