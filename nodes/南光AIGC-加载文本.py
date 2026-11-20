class NanGuangLoadText:
    """
    南光AIGC-加载文本
    """
    # 严格设定分类路径
    CATEGORY = "南光AIGC/文本"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("文本",)
    FUNCTION = "load_text"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "display": "text",
                        "tooltip": "在此编辑文本，或点击“加载文本文件”按钮从本地文件导入",
                    },
                ),
            },
        }

    def load_text(self, text):
        return (text,)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

# ==== 注册节点映射 ====
NODE_CLASS_MAPPINGS = {
    "NanGuangLoadText": NanGuangLoadText
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "NanGuangLoadText": "南光AIGC-加载文本"
}