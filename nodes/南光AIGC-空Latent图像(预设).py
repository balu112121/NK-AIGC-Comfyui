import torch

ASPECT_RATIO_PRESETS = {
    "1:1(Square)": (512, 512),
    "2:3 (Portrait Photo)": (512, 768),
    "3:2 (Photo)": (768, 512),
    "3:4 (Portrait Standard)": (576, 768),
    "4:3 (Standard)": (768, 576),
    "9:16 (Portrait Widescreen)": (432, 768),
    "16:9 (Widescreen)": (768, 432),
    "21:9 (Ultrawide)": (1008, 432),
    "自定义": None,
}

class NK_AIGC_EmptyLatentPreset:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "宽高比": (
                    list(ASPECT_RATIO_PRESETS.keys()),
                    {
                        "default": "2:3 (Portrait Photo)",
                        "tooltip": "选择预设后，宽度与高度会锁定为对应分辨率；选择「自定义」后可手动设置。",
                    },
                ),
                "宽度": (
                    "INT",
                    {
                        "default": 512,
                        "min": 64,
                        "max": 8192,
                        "step": 8,
                        "display": "number",
                    },
                ),
                "高度": (
                    "INT",
                    {
                        "default": 768,
                        "min": 64,
                        "max": 8192,
                        "step": 8,
                        "display": "number",
                    },
                ),
                "批次大小": (
                    "INT",
                    {
                        "default": 1,
                        "min": 1,
                        "max": 4096,
                        "display": "number",
                    },
                ),
            }
        }

    RETURN_TYPES = ("LATENT",)
    RETURN_NAMES = ("Latent",)
    FUNCTION = "generate"
    CATEGORY = "南光AIGC/Latent"
    DESCRIPTION = "根据宽高比预设或自定义尺寸生成空Latent，可直接连接 K采样器的 Latent 输入端。"

    def generate(self, 宽高比, 宽度, 高度, 批次大小):
        preset = ASPECT_RATIO_PRESETS.get(宽高比)
        if preset is not None:
            宽度, 高度 = preset
        else:
            # 安全兜底：防止前端传入 NaN 导致后端崩溃
            try:
                宽度 = int(宽度)
            except (ValueError, TypeError):
                宽度 = 512
            try:
                高度 = int(高度)
            except (ValueError, TypeError):
                高度 = 768

        # 确保尺寸为 8 的倍数
        宽度 = max(8, (宽度 // 8) * 8)
        高度 = max(8, (高度 // 8) * 8)
        
        try:
            批次大小 = max(1, int(批次大小))
        except (ValueError, TypeError):
            批次大小 = 1

        latent = torch.zeros([批次大小, 4, 高度 // 8, 宽度 // 8])
        return ({"samples": latent},)

NODE_CLASS_MAPPINGS = {
    "NK_AIGC_EmptyLatentPreset": NK_AIGC_EmptyLatentPreset,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "NK_AIGC_EmptyLatentPreset": "南光AIGC-空Latent图像(预设)",
}