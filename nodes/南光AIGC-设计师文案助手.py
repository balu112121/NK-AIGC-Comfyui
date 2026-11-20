# NK-AIGC-Comfyui/nodes/designer_copywriter_node.py

from typing import Any

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# ── 模型配置：统一指向火山方舟平台 ───────────────
MODEL_CONFIG = {
    "Kimi-K3.1-Pro": {
        "model_id": "kimi-k3-1-pro-261024",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
    },
    "DeepSeek-V4.1-Flash": {
        "model_id": "deepseek-v4-1-flash-261017",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
    },
    "GLM-5.2": {
        "model_id": "glm-5-2-260617",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
    },
    "Doubao-Seed-2.1-turbo": {
        "model_id": "doubao-seed-2-1-turbo-260628",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
    },
}

MODEL_NAMES = list(MODEL_CONFIG.keys())

SYSTEM_PROMPT = (
    "你是一位资深平面设计师与品牌文案专家。"
    "用户会给你一段设计需求或对话，请直接输出一段高质量的中文设计文案，"
    "风格专业、简洁、有传播力。不要解释，只输出文案本身。"
)


def _get_client(model_display: str, api_key: str, api_base_override: str = "") -> tuple[Any, str]:
    if OpenAI is None:
        raise RuntimeError("缺少 openai 库，请先在终端执行 pip install openai>=1.0")
    cfg = MODEL_CONFIG.get(model_display)
    if cfg is None:
        raise ValueError(f"未知模型：{model_display}")
    
    base_url = api_base_override.strip() or cfg["base_url"]
    client = OpenAI(api_key=api_key.strip(), base_url=base_url)
    return client, cfg["model_id"]


def test_api_connection(model_display: str, api_key: str) -> tuple[bool, str]:
    """供 __init__.py 的 HTTP 路由调用，测试 Key 是否可用。"""
    try:
        client, model_id = _get_client(model_display, api_key)
        
        create_kwargs = {
            "model": model_id,
            "messages": [{"role": "user", "content": "只回复 OK"}],
            "max_tokens": 8,
        }
        # 测试连通性时也要遵循 Kimi 的 temperature 规则
        if model_display != "Kimi-K3.1-Pro":
            create_kwargs["temperature"] = 0
            
        resp = client.chat.completions.create(**create_kwargs)
        text = (resp.choices[0].message.content or "").strip()
        return True, f"连接成功，模型回复：{text}"
    except Exception as e:
        return False, f"连接失败：{e}"


class NKDesignerCopywriter:
    """南光AIGC-设计师文案助手"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "conversation": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "placeholder": "在这里输入设计需求或对话内容，例如：\n"
                                       "为一家新中式茶饮品牌写一段小红书种草文案，突出「低卡」「手作」「东方美学」。",
                    },
                ),
                "api_key": (
                    "STRING",
                    {
                        "multiline": False,
                        "default": "",
                        "placeholder": "填写火山方舟 (ark-开头) 的 API Key",
                    },
                ),
                "model": (MODEL_NAMES,),
                "temperature": (
                    "FLOAT",
                    {"default": 0.7, "min": 0.0, "max": 2.0, "step": 0.05},
                ),
            },
            "optional": {
                "api_base_override": (
                    "STRING",
                    {
                        "multiline": False,
                        "default": "",
                        "placeholder": "（进阶）覆写 Base URL，留空使用默认方舟接口",
                    },
                ),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("文本",)
    FUNCTION = "generate"
    CATEGORY = "南光AIGC/文案"

    def generate(
        self,
        conversation: str,
        api_key: str,
        model: str,
        temperature: float,
        api_base_override: str = "",
        unique_id: str = "",
    ):
        conversation = (conversation or "").strip()
        api_key = (api_key or "").strip()

        if not conversation:
            return ("",)
        if not api_key:
            raise RuntimeError("设计师文案助手：API Key 不能为空。")

        try:
            client, model_id = _get_client(model, api_key, api_base_override)
            
            # ── 核心修复：Kimi 系列模型锁定 temperature，需动态剥离 ──
            create_kwargs = {
                "model": model_id,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": conversation},
                ],
                "max_tokens": 2048,
            }
            
            # 仅当不是 Kimi 模型时，才传入 temperature
            if model != "Kimi-K3.1-Pro":
                create_kwargs["temperature"] = float(temperature)
            
            resp = client.chat.completions.create(**create_kwargs)
            
            text = (resp.choices[0].message.content or "").strip()
            return (text,)
        except Exception as e:
            raise RuntimeError(f"设计师文案助手调用失败：{e}") from e


NODE_CLASS_MAPPINGS = {"NKDesignerCopywriter": NKDesignerCopywriter}
NODE_DISPLAY_NAME_MAPPINGS = {"NKDesignerCopywriter": "南光AIGC-设计师文案助手"}