# nodes/aliyun_bailian_config_node.py
import folder_paths  # 可选，如需保存配置可参考

class NK_AliyunBailianConfig:
    """
    南光AIGC-阿里云百炼配置
    输出阿里云百炼 OpenAI 兼容接口的 地址 (base_url) 和 密钥 (api_key)。
    """
    CATEGORY = "南光AIGC/API"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "API密钥": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "password": True,          # 隐藏输入内容
                    "tooltip": "阿里云百炼 API Key，以 sk- 开头。可在百炼控制台创建。"
                }),
            },
            "optional": {
                "地址": ("STRING", {
                    "default": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                    "multiline": False,
                    "tooltip": "阿里云百炼 OpenAI 兼容接口的 base_url。一般保持默认即可。"
                }),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("地址", "密钥")
    FUNCTION = "get_config"

    def get_config(self, API密钥, 地址="https://dashscope.aliyuncs.com/compatible-mode/v1"):
        # 去除首尾空白，避免下游因空格报错
        api_key = (API密钥 or "").strip()
        base_url = (地址 or "").strip() or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        return (base_url, api_key)


# ── 节点注册 ──────────────────────────────────────────────
NODE_CLASS_MAPPINGS = {
    "NK_AliyunBailianConfig": NK_AliyunBailianConfig
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "NK_AliyunBailianConfig": "南光AIGC-阿里云百炼配置"
}