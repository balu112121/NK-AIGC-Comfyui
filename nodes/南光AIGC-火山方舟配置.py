# NK-AIGC-Comfyui/nodes/volcengine_ark_config.py
import os

class VolcengineArkConfigNode:
    """
    南光AIGC-火山方舟配置
    输出火山方舟数据面 Base URL 与 API Key，供下游节点连接使用。
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                # 这里的名字为了配合前端 JS 的识别，使用 api_key 和 base_url
                "api_key": ("STRING", {"default": "", "multiline": False}),
                "base_url": (
                    "STRING",
                    {
                        "default": "https://ark.cn-beijing.volces.com/api/v3",
                        "multiline": False,
                    },
                ),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("地址", "密钥")
    FUNCTION = "get_config"
    CATEGORY = "南光AIGC/API"

    def get_config(self, api_key, base_url):
        # 安全策略：环境变量优先
        resolved_key = os.environ.get("ARK_API_KEY", "").strip() or (api_key or "").strip()
        resolved_url = (base_url or "").strip() or "https://ark.cn-beijing.volces.com/api/v3"

        if not resolved_key:
            print(
                "[NK-AIGC] ⚠️ 未检测到火山方舟 API Key。"
                "请在节点中填写，或设置环境变量 ARK_API_KEY。"
            )
        else:
            print("[NK-AIGC] ✅ 火山方舟配置已就绪（地址：%s）" % resolved_url)

        # 注意：输出端顺序必须是 地址、密钥，对应 RETURN_NAMES
        return (resolved_url, resolved_key)


NODE_CLASS_MAPPINGS = {
    "NK_AIGC_VolcengineArkConfig": VolcengineArkConfigNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "NK_AIGC_VolcengineArkConfig": "南光AIGC-火山方舟配置",
}