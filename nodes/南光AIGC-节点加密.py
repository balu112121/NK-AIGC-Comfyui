# NK-AIGC-Comfyui/nodes/node_encrypt_node.py

class NKNodeEncryptNode:
    """
    南光AIGC-节点加密
    - 类别：南光AIGC/加密
    - 输出：文本（STRING）
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "placeholder": "在此输入提示词文本 ..."
                }),
                "password_setting": ("STRING", {
                    "default": ""
                }),
                "password_switch": ("BOOLEAN", {
                    "default": False,
                    "label_on": "open",
                    "label_off": "close"
                }),
                "encrypted_text": ("STRING", {
                    "multiline": False,
                    "default": ""
                }),
                "is_encrypted": ("BOOLEAN", {
                    "default": False
                }),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("文本",)
    FUNCTION = "process"
    CATEGORY = "南光AIGC/加密"

    def process(self, text, password_setting, password_switch, encrypted_text, is_encrypted):
        # 如果处于加密状态，输出备份的 encrypted_text，保证工作流正常运行
        if is_encrypted:
            return (encrypted_text,)
        return (text,)


NODE_CLASS_MAPPINGS = {
    "NKNodeEncryptNode": NKNodeEncryptNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "NKNodeEncryptNode": "南光AIGC-节点加密",
}