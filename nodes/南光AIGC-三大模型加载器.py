# NK-AIGC-Comfyui/nodes/three_model_loader.py
import comfy.sd
import comfy.utils
import folder_paths
import torch


class NKThreeModelLoader:
    """
    南光AIGC-三大模型加载器
    集成：UNET 加载器 + 双 CLIP 加载器 + VAE 加载器
    """

    @classmethod
    def INPUT_TYPES(cls):
        # UNET 模型列表
        unet_list = folder_paths.get_filename_list("diffusion_models")
        if not unet_list:
            unet_list = folder_paths.get_filename_list("unet")

        # CLIP 模型列表
        clip_list = folder_paths.get_filename_list("clip")
        if not clip_list:
            clip_list = folder_paths.get_filename_list("text_encoders")
        
        # ★ 核心修复：同时加入 "无" 和 "None"，并去重。确保无论前端传什么，校验都能通过。
        clean_clip_list = [x for x in clip_list if x not in ("无", "None")]
        clip_list_with_none = ["无"] + clean_clip_list + ["None"]

        # VAE 模型列表
        vae_list = folder_paths.get_filename_list("vae")

        # 图1完整的 CLIP 类型列表
        clip_types = [
            "stable_diffusion", "stable_cascade", "sd3", "stable_audio", "mochi",
            "ltxv", "pixart", "cosmos", "lumina2", "wan", "hidream", "chroma",
            "ace", "omnigen2", "qwen_image", "hunyuan_image", "flux2", "ovis",
            "longcat_image", "cogvideox", "lens", "pixeldit", "ideogram4", "boogu",
            "krea2", "joyimage", "mage", "minimax", "yue2", "flux3", "moss_image", "fibo2"
        ]

        return {
            "required": {
                # ── UNET 部分 ──────────────────────────────
                "unet_name": (
                    unet_list,
                    {"tooltip": "选择 diffusion_models 文件夹中的 UNET 模型"},
                ),
                "weight_dtype": (
                    ["default", "fp8_e4m3fn", "fp8_e4m3fn_fast", "fp8_e5m2"],
                    {
                        "default": "default",
                        "tooltip": "UNET 权重数据类型，default 为自动选择"
                    },
                ),
                # ── 双 CLIP 部分 ───────────────────────────
                "clip_name1": (
                    clip_list,
                    {"tooltip": "第一个 CLIP / 文本编码器"},
                ),
                "clip_name2": (
                    clip_list_with_none,
                    {"tooltip": "第二个 CLIP / 文本编码器（单 CLIP 模型请选『无』）"},
                ),
                "clip_type": (
                    clip_types,
                    {
                        "default": "stable_diffusion",
                        "tooltip": "CLIP 类型，需与模型匹配（如 SD1.5用 stable_diffusion，Flux用 flux 等）"
                    },
                ),
                "device": (
                    ["默认", "CPU"],
                    {
                        "default": "默认",
                        "tooltip": "CLIP 加载设备，默认由系统自动分配"
                    },
                ),
                # ── VAE 部分 ──────────────────────────────
                "vae_name": (
                    vae_list,
                    {"tooltip": "选择 vae 文件夹中的 VAE 模型"},
                ),
            }
        }

    RETURN_TYPES = ("MODEL", "CLIP", "VAE")
    RETURN_NAMES = ("模型", "CLIP", "VAE")
    FUNCTION = "load_all"
    CATEGORY = "南光AIGC/加载器"

    def load_all(
        self,
        unet_name: str,
        weight_dtype: str,
        clip_name1: str,
        clip_name2: str,
        clip_type: str,
        device: str,
        vae_name: str,
    ):
        # ── 1. 加载 UNET / 扩散模型 ──────────────────────
        unet_path = folder_paths.get_full_path_or_raise("diffusion_models", unet_name)
        model = comfy.sd.load_diffusion_model(unet_path, model_options={"weight_dtype": weight_dtype})

        # ── 2. 加载双/单 CLIP ──────────────────────────────
        clip_path1 = folder_paths.get_full_path_or_raise("clip", clip_name1)
        
        # ★ 核心修复：只要选的是 "无" 或 "None" 或空，统统走单 CLIP 逻辑
        if clip_name2 in ("无", "None", "", None):
            ckpt_paths = [clip_path1]
        else:
            clip_path2 = folder_paths.get_full_path_or_raise("clip", clip_name2)
            ckpt_paths = [clip_path1, clip_path2]

        # 动态获取 CLIPType
        clip_type_enum = comfy.sd.CLIPType.STABLE_DIFFUSION
        if hasattr(comfy.sd, "CLIPType") and hasattr(comfy.sd.CLIPType, clip_type.upper()):
            clip_type_enum = getattr(comfy.sd.CLIPType, clip_type.upper())

        clip = comfy.sd.load_clip(
            ckpt_paths=ckpt_paths,
            embedding_directory=folder_paths.get_folder_paths("embeddings"),
            clip_type=clip_type_enum,
        )

        # 处理设备选择
        if device == "CPU":
            try:
                clip.cond_stage_model.to("cpu")
            except Exception:
                pass

        # ── 3. 加载 VAE ─────────────────────────────────
        vae_path = folder_paths.get_full_path_or_raise("vae", vae_name)
        vae = comfy.sd.VAE(sd=comfy.utils.load_torch_file(vae_path))

        return (model, clip, vae)


NODE_CLASS_MAPPINGS = {
    "NKThreeModelLoader": NKThreeModelLoader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "NKThreeModelLoader": "南光AIGC-三大模型加载器",
}