# NK-AIGC-Comfyui/nodes/南光AIGC-图像缩放(NK).py
import torch
import torch.nn.functional as F
import comfy.utils

class NKImageResize:
    """
    南光AIGC-图像缩放(NK)
    支持按长边/短边等比例缩放、裁剪/填充模式、Lanczos 插值、填充颜色与整除对齐。
    遮罩为可选输入，不连接时会自动输出全黑遮罩。
    """
    CATEGORY = "南光AIGC/图像"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "图像": ("IMAGE",),
                "宽度": ("INT", {"default": 512, "min": 1, "max": 16384, "step": 1}),
                "高度": ("INT", {"default": 512, "min": 1, "max": 16384, "step": 1}),
                "缩放方法": ([
                    "按长边等比例",
                    "按短边等比例",
                    "拉伸填满",
                    "指定宽高" # <--- 修改点 1
                ], {"default": "按长边等比例"}),
                "将边缩放到": ("INT", {"default": 1024, "min": 1, "max": 16384, "step": 1}),
                "缩放插值": ([
                    "Lanczos",
                    "Bicubic",
                    "Bilinear",
                    "Area",
                    "Nearest-Exact"
                ], {"default": "Lanczos"}),
                "缩放模式": (["裁剪", "填充", "拉伸"], {"default": "裁剪"}),
                "固定方向": (["居中", "顶部", "底部", "左侧", "右侧"], {"default": "居中"}),
                "执行条件": (["总是", "仅放大", "仅缩小"], {"default": "总是"}),
                "填充颜色": ("STRING", {"default": "#7d7d7d"}),
                "整除整数": ("INT", {"default": 0, "min": 0, "max": 1024, "step": 1}),
            },
            "optional": {
                "遮罩": ("MASK",),
            }
        }

    RETURN_TYPES = ("IMAGE", "INT", "INT", "MASK")
    RETURN_NAMES = ("图像", "宽度", "高度", "遮罩")
    FUNCTION = "resize"

    _INTERP_MAP = {
        "Lanczos": "lanczos",
        "Bicubic": "bicubic",
        "Bilinear": "bilinear",
        "Area": "area",
        "Nearest-Exact": "nearest-exact",
    }

    def _parse_hex_color(self, hex_str):
        hex_str = hex_str.strip().lstrip("#")
        if len(hex_str) == 3:
            hex_str = "".join([c * 2 for c in hex_str])
        if len(hex_str) != 6:
            return (125/255.0, 125/255.0, 125/255.0)
        r = int(hex_str[0:2], 16) / 255.0
        g = int(hex_str[2:4], 16) / 255.0
        b = int(hex_str[4:6], 16) / 255.0
        return (r, g, b)

    def _resize_mask(self, mask, width, height, upscale_method):
        if mask is None:
            return None
            
        if mask.dim() == 2:
            mask = mask.unsqueeze(0).unsqueeze(0)
        elif mask.dim() == 3:
            mask = mask.unsqueeze(1)
            
        if upscale_method in ("lanczos", "bicubic"):
            mode = "bicubic"
        elif upscale_method == "nearest-exact":
            mode = "nearest"
        else:
            mode = upscale_method
            
        align_corners = False if mode in ("bicubic", "bilinear") else None
        
        return F.interpolate(mask, size=(height, width), mode=mode, align_corners=align_corners)

    def resize(self, 图像, 宽度, 高度, 缩放方法, 将边缩放到, 缩放插值, 缩放模式, 固定方向, 执行条件, 填充颜色, 整除整数, 遮罩=None):
        img_tensor = 图像
        if img_tensor.dim() == 3: 
            img_tensor = img_tensor.unsqueeze(0)
        img_tensor = img_tensor.movedim(-1, 1)
        
        mask_tensor = 遮罩
        if mask_tensor is not None:
            if mask_tensor.dim() == 2: 
                mask_tensor = mask_tensor.unsqueeze(0).unsqueeze(0)
            elif mask_tensor.dim() == 3: 
                mask_tensor = mask_tensor.unsqueeze(1)

        B, C, H_orig, W_orig = img_tensor.shape
        upscale_method = self._INTERP_MAP.get(缩放插值, "lanczos")

        if 缩放方法 == "指定宽高": # <--- 修改点 2
            target_w, target_h = 宽度, 高度
        elif 缩放方法 in ("按长边等比例", "按短边等比例"):
            if 缩放方法 == "按长边等比例":
                scale = 将边缩放到 / max(W_orig, H_orig)
            else:
                scale = 将边缩放到 / min(W_orig, H_orig)
            target_w = max(1, round(W_orig * scale))
            target_h = max(1, round(H_orig * scale))
        else:
            target_w, target_h = 宽度, 高度

        if 执行条件 == "仅放大" and (W_orig >= target_w and H_orig >= target_h):
            if mask_tensor is not None:
                mask_tensor = mask_tensor[:, 0, :, :]
            else:
                mask_tensor = torch.zeros((B, H_orig, W_orig), dtype=img_tensor.dtype, device=img_tensor.device)
            return (图像, W_orig, H_orig, mask_tensor)
            
        if 执行条件 == "仅缩小" and (W_orig <= target_w and H_orig <= target_h):
            if mask_tensor is not None:
                mask_tensor = mask_tensor[:, 0, :, :]
            else:
                mask_tensor = torch.zeros((B, H_orig, W_orig), dtype=img_tensor.dtype, device=img_tensor.device)
            return (图像, W_orig, H_orig, mask_tensor)

        if 缩放模式 == "拉伸":
            img_tensor = comfy.utils.common_upscale(img_tensor, target_w, target_h, upscale_method, "disabled")
            if mask_tensor is not None:
                mask_tensor = self._resize_mask(mask_tensor, target_w, target_h, upscale_method)

        elif 缩放模式 == "裁剪":
            scale_cover = max(target_w / W_orig, target_h / H_orig)
            new_w = max(target_w, round(W_orig * scale_cover))
            new_h = max(target_h, round(H_orig * scale_cover))

            img_tensor = comfy.utils.common_upscale(img_tensor, new_w, new_h, upscale_method, "disabled")
            if mask_tensor is not None:
                mask_tensor = self._resize_mask(mask_tensor, new_w, new_h, upscale_method)

            if 固定方向 == "居中":
                x = (new_w - target_w) // 2
                y = (new_h - target_h) // 2
            elif 固定方向 == "顶部":
                x = (new_w - target_w) // 2
                y = 0
            elif 固定方向 == "底部":
                x = (new_w - target_w) // 2
                y = new_h - target_h
            elif 固定方向 == "左侧":
                x = 0
                y = (new_h - target_h) // 2
            else:
                x = new_w - target_w
                y = (new_h - target_h) // 2

            img_tensor = img_tensor[:, :, y:y + target_h, x:x + target_w]
            if mask_tensor is not None:
                mask_tensor = mask_tensor[:, :, y:y + target_h, x:x + target_w]

        elif 缩放模式 == "填充":
            scale_fit = min(target_w / W_orig, target_h / H_orig)
            new_w = max(1, round(W_orig * scale_fit))
            new_h = max(1, round(H_orig * scale_fit))

            img_tensor = comfy.utils.common_upscale(img_tensor, new_w, new_h, upscale_method, "disabled")
            if mask_tensor is not None:
                mask_tensor = self._resize_mask(mask_tensor, new_w, new_h, upscale_method)

            pad_left = (target_w - new_w) // 2
            pad_right = target_w - new_w - pad_left
            pad_top = (target_h - new_h) // 2
            pad_bottom = target_h - new_h - pad_top

            r, g, b = self._parse_hex_color(填充颜色)
            canvas = torch.zeros((B, 3, target_h, target_w), dtype=img_tensor.dtype, device=img_tensor.device)
            canvas[:, 0, :, :] = r
            canvas[:, 1, :, :] = g
            canvas[:, 2, :, :] = b

            canvas[:, :, pad_top:pad_top + new_h, pad_left:pad_left + new_w] = img_tensor
            img_tensor = canvas

            if mask_tensor is not None:
                mask_canvas = torch.zeros((B, 1, target_h, target_w), dtype=mask_tensor.dtype, device=mask_tensor.device)
                mask_canvas[:, :, pad_top:pad_top + new_h, pad_left:pad_left + new_w] = mask_tensor
                mask_tensor = mask_canvas

        if 整除整数 > 0:
            _, _, H_out, W_out = img_tensor.shape
            new_H = max(整除整数, (H_out // 整除整数) * 整除整数)
            new_W = max(整除整数, (W_out // 整除整数) * 整除整数)
            if new_H != H_out or new_W != W_out:
                img_tensor = comfy.utils.common_upscale(img_tensor, new_W, new_H, "bilinear", "disabled")
                if mask_tensor is not None:
                    mask_tensor = self._resize_mask(mask_tensor, new_W, new_H, "bilinear")

        img_out = img_tensor.movedim(1, -1)
        final_h = img_out.shape[1]
        final_w = img_out.shape[2]

        if mask_tensor is not None:
            mask_out = mask_tensor.squeeze(1)
        else:
            mask_out = torch.zeros((B, final_h, final_w), dtype=img_out.dtype, device=img_out.device)

        return (img_out, final_w, final_h, mask_out)

NODE_CLASS_MAPPINGS = {
    "NKImageResize": NKImageResize
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "NKImageResize": "南光AIGC-图像缩放(NK)"
}