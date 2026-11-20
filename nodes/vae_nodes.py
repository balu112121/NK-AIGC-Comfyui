import torch

class NKVAEDecode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "Latent": ("LATENT",),
                "VAE": ("VAE",)
            }
        }
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("图像",)
    FUNCTION = "decode"
    CATEGORY = "南光AIGC/VAE"

    def decode(self, Latent, VAE):
        image = VAE.decode(Latent["samples"])
        return (image,)

class NKVAEEncode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "图像": ("IMAGE",),
                "VAE": ("VAE",)
            }
        }
    RETURN_TYPES = ("LATENT",)
    RETURN_NAMES = ("Latent",)
    FUNCTION = "encode"
    CATEGORY = "南光AIGC/VAE"

    def encode(self, 图像, VAE):
        t = []
        for batch_num in range(图像.shape[0]):
            t.append(VAE.encode(图像[batch_num,:,:,:3]))
        return ({"samples": torch.cat(t, dim=0)},)

NODE_CLASS_MAPPINGS = {
    "NKVAEDecode": NKVAEDecode,
    "NKVAEEncode": NKVAEEncode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "NKVAEDecode": "南光AIGC-VAE解码(NK)",
    "NKVAEEncode": "南光AIGC-VAE编码(NK)",
}