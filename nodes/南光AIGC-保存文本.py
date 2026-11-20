import os
import folder_paths


class NKSaveText:
    CATEGORY = "南光AIGC/文本"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "文本": ("STRING", {
                    "forceInput": True,
                    "multiline": True,
                }),
            },
            "optional": {
                "文件名": ("STRING", {
                    "default": "南光AIGC.txt",
                    "multiline": False,
                }),
                "追加写入": ("BOOLEAN", {
                    "default": False,
                }),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("字符串",)
    FUNCTION = "save_text"
    OUTPUT_NODE = True

    def save_text(self, 文本, 文件名="南光AIGC.txt", 追加写入=False):
        input_dir = folder_paths.get_input_directory()
        os.makedirs(input_dir, exist_ok=True)

        safe_name = os.path.basename(文件名.strip() or "南光AIGC.txt")
        if not safe_name.lower().endswith(".txt"):
            safe_name += ".txt"

        file_path = os.path.join(input_dir, safe_name)
        mode = "a" if 追加写入 else "w"

        try:
            with open(file_path, mode, encoding="utf-8") as f:
                f.write(str(文本))
            print(f"[南光AIGC-保存文本] 已保存: {file_path}")
        except Exception as e:
            print(f"[南光AIGC-保存文本] 写入失败: {e}")

        return (文本,)


# ============ 节点注册映射 ============
NODE_CLASS_MAPPINGS = {
    "NKSaveText": NKSaveText,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "NKSaveText": "南光AIGC-保存文本",
}

# ============ 对外导出 ============
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]