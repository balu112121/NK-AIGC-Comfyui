import torch
import numpy as np
from PIL import Image, ImageOps
import os
import folder_paths

class NKLoadImageMask:
    @classmethod
    def INPUT_TYPES(cls):
        input_dir = folder_paths.get_input_directory()
        files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
        if not files:
            files = ["None"]
            
        aspect_ratios = [
            "原始比例", 
            "1:1 (Square)", 
            "2:3 (Portrait Photo)", 
            "3:2 (Photo)", 
            "3:4 (Portrait Standard)", 
            "4:3 (Standard)", 
            "9:16 (Portrait Widescreen)", 
            "16:9 (Widescreen)", 
            "21:9 (Ultrawide)"
        ]

        return {
            "required": {
                "image": (sorted(files), {"image_upload": True}),
                "宽高比": (aspect_ratios, {"default": "原始比例"}),
                "裁剪宽度": ("INT", {"default": 0, "min": 0, "max": 16384, "step": 1}),
                "裁剪高度": ("INT", {"default": 0, "min": 0, "max": 16384, "step": 1}),
                "处理模式": (["自动", "Alpha", "RGB"], {"default": "自动"}),
                "遮罩阈值": ("FLOAT", {"default": 1.00, "min": 0.0, "max": 1.0, "step": 0.01}),
                "反转遮罩": ("BOOLEAN", {"default": True, "label_on": "开启", "label_off": "关闭"}),
            }
        }

    RETURN_TYPES = ("IMAGE", "MASK", "STRING")
    RETURN_NAMES = ("图像", "遮罩", "文件名")
    FUNCTION = "load_and_process"
    CATEGORY = "南光AIGC/图像"

    @classmethod
    def VALIDATE_INPUTS(cls, image):
        if not folder_paths.exists_annotated_filepath(image):
            return "无效图像文件: {}".format(image)
        return True

    def load_and_process(self, image, 宽高比, 裁剪宽度, 裁剪高度, 处理模式, 遮罩阈值, 反转遮罩):
        image_path = folder_paths.get_annotated_filepath(image)
        i = Image.open(image_path)
        i = ImageOps.exif_transpose(i)
        
        orig_w, orig_h = i.size

        # ================= 核心：完全显示图像裁剪 (等比缩放 + 透明补边) =================
        if 宽高比 != "原始比例":
            ratio_str = 宽高比.split(" ")[0]
            try:
                w_r, h_r = map(float, ratio_str.split(":"))
                target_ratio = w_r / h_r
            except:
                target_ratio = orig_w / orig_h

            # 计算目标画布的尺寸（尽量保持原有的高度或宽度作为极限）
            if (orig_w / orig_h) > target_ratio:
                new_w = orig_w
                new_h = int(new_w / target_ratio)
                if new_h > orig_h:
                    new_h = orig_h
                    new_w = int(new_h * target_ratio)
            else:
                new_h = orig_h
                new_w = int(new_h * target_ratio)
                if new_w > orig_w:
                    new_w = orig_w
                    new_h = int(new_w / target_ratio)

            # 保证背景透明，不影响遮罩
            if i.mode != 'RGBA':
                i = i.convert('RGBA')
                
            # 使用 ImageOps.pad 进行等比缩放并居中填充，完全保留原图所有像素
            i = ImageOps.pad(i, (new_w, new_h), color=(0, 0, 0, 0), centering=(0.5, 0.5))
        else:
            # 原始比例：不缩放不补边，直接输出原图
            if 裁剪宽度 > 0 and 裁剪高度 > 0:
                i = i.crop((0, 0, min(裁剪宽度, orig_w), min(裁剪高度, orig_h)))

        # 图像输出
        img_rgb = i.convert("RGB")
        image_np = np.array(img_rgb).astype(np.float32) / 255.0
        image_tensor = torch.from_numpy(image_np)[None,]

        # 遮罩输出
        if 处理模式 == "RGB":
            gray = np.array(i.convert('L')).astype(np.float32) / 255.0
            mask_np = (gray > 遮罩阈值).astype(np.float32)
            mask_tensor = torch.from_numpy(mask_np)[None,]
        else:
            if 'A' in i.getbands():
                mask = i.getchannel('A')
            elif 'transparency' in i.info:
                mask = i.convert('RGBA').getchannel('A')
            else:
                mask = Image.new('L', i.size, 255)
                
            mask_np = np.array(mask).astype(np.float32) / 255.0
            mask_tensor = torch.from_numpy(mask_np)[None,]

        if 反转遮罩:
            mask_tensor = 1.0 - mask_tensor

        clean_name = os.path.basename(image_path).split(" [")[0]
        return (image_tensor, mask_tensor, clean_name)

NODE_CLASS_MAPPINGS = {"NK_LoadImageMask": NKLoadImageMask}
NODE_DISPLAY_NAME_MAPPINGS = {"NK_LoadImageMask": "南光AIGC-加载图像(遮罩)"}