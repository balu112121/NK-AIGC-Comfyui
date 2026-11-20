import torch
import comfy.sd
import comfy.sample
import comfy.utils
import latent_preview

class NK_AIGC_KSampler:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "模型": ("MODEL",),
                "正面条件": ("CONDITIONING",),
                "负面条件": ("CONDITIONING",),
                "Latent": ("LATENT",),
                "种子": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                "生成后控制": (["fixed", "increment", "decrement", "randomize"], {"default": "randomize"}),
                "步数": ("INT", {"default": 20, "min": 1, "max": 10000}),
                "CFG": ("FLOAT", {"default": 8.0, "min": 0.0, "max": 100.0, "step": 0.1, "round": 0.01}),
                "采样器名称": (comfy.samplers.KSampler.SAMPLERS, {"default": "euler"}),
                "调度器": (comfy.samplers.KSampler.SCHEDULERS, {"default": "simple"}),
                "降噪": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
            }
        }

    RETURN_TYPES = ("LATENT",)
    RETURN_NAMES = ("Latent",)
    FUNCTION = "sample"
    CATEGORY = "南光AIGC/模型"

    def sample(self, 模型, 正面条件, 负面条件, Latent, 种子, 生成后控制, 步数, CFG, 采样器名称, 调度器, 降噪):
        # 提取 Latent 图
        latent_image = Latent["samples"]
        
        # 根据种子和批次准备噪声张量（修复了原代码将 int 传给 noise 的错误）
        batch_inds = Latent["batch_index"] if "batch_index" in Latent else None
        noise = comfy.sample.prepare_noise(latent_image, 种子, batch_inds)
        
        # 提取遮罩（如果有）
        noise_mask = None
        if "noise_mask" in Latent:
            noise_mask = Latent["noise_mask"]
            
        # 准备进度条回调
        callback = latent_preview.prepare_callback(模型, 步数)
        disable_pbar = not comfy.utils.PROGRESS_BAR_ENABLED
        
        # 严格按照 ComfyUI 官方的参数顺序调用核心采样器
        samples = comfy.sample.sample(
            模型,         # model
            noise,       # noise (张量)
            步数,         # steps
            CFG,         # cfg
            采样器名称,    # sampler_name
            调度器,       # scheduler
            正面条件,      # positive
            负面条件,      # negative
            latent_image,# latent_image
            denoise=降噪,
            noise_mask=noise_mask,
            callback=callback,
            disable_pbar=disable_pbar,
            seed=种子
        )
        
        # 将采样结果重新打包为 LATENT 格式返回
        out = Latent.copy()
        out["samples"] = samples
        return (out,)

NODE_CLASS_MAPPINGS = {
    "NK_AIGC_KSampler": NK_AIGC_KSampler
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "NK_AIGC_KSampler": "南光AIGC-K采样器(NK)"
}