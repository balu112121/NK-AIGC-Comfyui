# nodes/nk_load_batch_images.py
import os
import torch
import numpy as np
import random
from PIL import Image, ImageOps

class NKLoadBatchImages:
    """
    南光AIGC - 加载批次图像节点
    批量扫描指定目录下的图像文件，按索引顺序输出图像张量及配套文件元数据
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "图片目录": ("STRING", {"default": ""}),
                "开始索引": ("INT", {"default": 0, "min": 0, "max": 999999, "step": 1}),
                # 按照要求：新增单张模式，默认随机模式
                "加载模式": (["单张模式", "递增模式", "递减模式", "随机模式"], {"default": "随机模式"}),
                "RGBA模式": ("BOOLEAN", {"default": False}),
                "扫描子目录": ("BOOLEAN", {"default": True}),
                "文件名含后缀": ("BOOLEAN", {"default": False}),
                "强制扩展名": ("STRING", {"default": ""}),
                "重置递增序号": ("BOOLEAN", {"default": False}),
                "随机种子": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                "生成后控制": (["randomize", "fixed", "increment"], {"default": "randomize"}),
                "图像筛选": (["全部", "仅PNG", "仅JPG", "仅WEBP"], {"default": "全部"}),
            }
        }

    # 7个输出端，包含图像总数
    RETURN_TYPES = ("IMAGE", "STRING", "STRING", "STRING", "STRING", "INT", "INT")
    RETURN_NAMES = ("图像", "文件名", "图像路径", "扩展名", "路径+文件名", "序号", "图像总数")
    FUNCTION = "load_images"
    CATEGORY = "南光AIGC/图像"

    def load_images(self, 图片目录, 开始索引, 加载模式, RGBA模式, 
                    扫描子目录, 文件名含后缀, 强制扩展名, 
                    重置递增序号, 随机种子, 生成后控制, 图像筛选):
        
        image_directory = 图片目录.strip()
        if not image_directory or not os.path.isdir(image_directory):
            raise ValueError(f"[NK-AIGC] 图像目录无效或不存在: {image_directory}")

        SUPPORTED_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.webp', '.bmp')
        image_files = []
        
        # 扫描文件
        for root, dirs, files in os.walk(image_directory):
            if not 扫描子目录:
                dirs.clear()
            for f in files:
                if f.startswith('.'):
                    continue
                ext = os.path.splitext(f)[1].lower()
                if ext not in SUPPORTED_EXTENSIONS:
                    continue
                if 图像筛选 == "仅PNG" and ext != ".png": continue
                if 图像筛选 == "仅JPG" and ext not in (".jpg", ".jpeg"): continue
                if 图像筛选 == "仅WEBP" and ext != ".webp": continue
                image_files.append(os.path.join(root, f))
                
        # 排序
        image_files.sort()
        
        total_count = len(image_files)
        if total_count == 0:
            raise ValueError(f"[NK-AIGC] 目录下未找到匹配的图像: {image_directory}")

        # 加载模式逻辑处理
        if 加载模式 == "单张模式":
            current_index = 开始索引 if 开始索引 < total_count else 0
        else:
            if 加载模式 == "递减模式":
                image_files.reverse()
            elif 加载模式 == "随机模式":
                random.seed(随机种子)
                random.shuffle(image_files)
            
            # 索引越界防护
            current_index = max(0, min(开始索引, total_count - 1))

        target_path = image_files[current_index]
        try:
            img = Image.open(target_path)
            if not RGBA模式:
                if img.mode != "RGBA":
                    img = img.convert("RGBA")
            else:
                img = ImageOps.exif_transpose(img).convert("RGB")
                
            img_np = np.array(img).astype(np.float32) / 255.0
            image_tensor = torch.from_numpy(img_np)[None,] 
        except Exception as e:
            raise RuntimeError(f"[NK-AIGC] 读取图像失败 {target_path}: {e}")

        # 解析元数据
        path_no_ext, orig_ext = os.path.splitext(target_path)
        dir_path = os.path.dirname(target_path)
        base_name = os.path.basename(path_no_ext)
        
        final_ext = 强制扩展名.lstrip('.') if 强制扩展名 else orig_ext.lstrip('.')
        out_filename = os.path.basename(target_path) if 文件名含后缀 else base_name
        out_path = target_path
        out_path_plus_filename = os.path.join(os.path.basename(dir_path), os.path.basename(target_path))

        return (
            image_tensor,
            out_filename,
            out_path,
            final_ext,
            out_path_plus_filename,
            current_index,
            total_count
        )

NODE_CLASS_MAPPINGS = {
    "NKLoadBatchImages": NKLoadBatchImages
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "NKLoadBatchImages": "南光AIGC-加载批次图像"
}