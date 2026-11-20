# NK-AIGC-Comfyui/nodes/doubao_video_node.py

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from typing import Any

import aiohttp
import numpy as np
import torch

try:
    from comfy_api.input_impl import VideoFromFile
    _VIDEO_AVAILABLE = True
except ImportError:
    VideoFromFile = None
    _VIDEO_AVAILABLE = False

CATEGORY = "南光AIGC/豆包"

ARK_BASE = "https://ark.cn-beijing.volces.com/api/v3"
ARK_CREATE_URL = f"{ARK_BASE}/contents/generations/tasks"
ARK_QUERY_URL = f"{ARK_BASE}/contents/generations/tasks/{{task_id}}"

# ⚠️ 关键修正：使用火山方舟真实 Model ID，而非界面简称
MODEL_MAP = {
    "Seedance 2.5": "doubao-seedance-2-5-260628",
    "Seedance 2.5 Flash": "doubao-seedance-2-5-flash-261115",
    "Seedance 2.0": "doubao-seedance-2-0-260128",
    "Seedance 2.0 Fast": "doubao-seedance-2-0-fast-260128",
    "Seedance 2.0 Mini": "doubao-seedance-2-0-mini-260615",
}

RATIO_OPTIONS = [
    "16:9", "9:16", "4:3", "3:4", "1:1", "21:9", "9:21", "adaptive",
]


def _tensor_to_temp_png(image: torch.Tensor) -> str:
    if image is None:
        return ""
    if image.dim() == 4:
        image = image[0]
    arr = (image.cpu().numpy() * 255.0).clip(0, 255).astype(np.uint8)
    from PIL import Image as PILImage
    pil = PILImage.fromarray(arr)
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False, dir=tempfile.gettempdir())
    pil.save(tmp.name, format="PNG")
    tmp.close()
    return tmp.name


def _file_to_data_url(path: str) -> str:
    if not path or not os.path.isfile(path):
        return ""
    import base64
    import mimetypes
    mime, _ = mimetypes.guess_type(path)
    mime = mime or "application/octet-stream"
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{data}"


def _build_content(
    prompt: str,
    first_frame: torch.Tensor | None,
    last_frame: torch.Tensor | None,
    audio: Any,
    ref_images: list[torch.Tensor],
    generate_audio: bool,
) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = []

    # 首帧 / 尾帧
    if first_frame is not None:
        path = _tensor_to_temp_png(first_frame)
        url = _file_to_data_url(path)
        if url:
            content.append({"type": "image_url", "image_url": {"url": url}, "role": "first_frame"})

    if last_frame is not None and first_frame is not None:
        path = _tensor_to_temp_png(last_frame)
        url = _file_to_data_url(path)
        if url:
            content.append({"type": "image_url", "image_url": {"url": url}, "role": "last_frame"})

    # 参考图：仅在没有首帧时传入，避免与首尾帧互斥
    if first_frame is None:
        for idx, img in enumerate(ref_images, start=1):
            if img is None:
                continue
            path = _tensor_to_temp_png(img)
            url = _file_to_data_url(path)
            if url:
                content.append({"type": "image_url", "image_url": {"url": url}, "role": "reference_image"})
                if idx >= 9:
                    break

    # 音频参考
    if audio is not None and generate_audio:
        audio_url = ""
        if isinstance(audio, dict) and "waveform" in audio:
            import soundfile as sf
            waveform = audio["waveform"]
            if torch.is_tensor(waveform):
                waveform = waveform.cpu().numpy()
            if waveform.ndim == 3:
                waveform = waveform[0]
            if waveform.ndim == 2 and waveform.shape[0] < waveform.shape[1]:
                waveform = waveform.T
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            sf.write(tmp.name, waveform, int(audio.get("sample_rate", 44100)))
            tmp.close()
            audio_url = _file_to_data_url(tmp.name)
        elif isinstance(audio, str):
            audio_url = audio
        if audio_url:
            content.append({"type": "audio_url", "audio_url": {"url": audio_url}, "role": "reference_audio"})

    if prompt.strip():
        content.insert(0, {"type": "text", "text": prompt.strip()})

    return content


async def _poll_task(session: aiohttp.ClientSession, api_key: str, task_id: str, timeout: int = 900, interval: float = 5.0) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {api_key}"}
    url = ARK_QUERY_URL.format(task_id=task_id)
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout

    while loop.time() < deadline:
        async with session.get(url, headers=headers) as resp:
            data = await resp.json()
        status = str(data.get("status", "")).lower()
        if status in {"succeeded", "success"}:
            return data
        if status in {"failed", "expired", "cancelled"}:
            raise RuntimeError(f"视频任务失败：{json.dumps(data, ensure_ascii=False)[:2000]}")
        await asyncio.sleep(interval)
    raise TimeoutError(f"视频任务超时（{timeout} 秒），task_id={task_id}")


async def _download_video(url: str, timeout: int = 300) -> str:
    tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
            resp.raise_for_status()
            with open(tmp.name, "wb") as f:
                while True:
                    chunk = await resp.content.read(1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
    tmp.close()
    return tmp.name


class NK豆包视频生成:
    @classmethod
    def INPUT_TYPES(cls):
        optional = {
            "首帧图": ("IMAGE", {"tooltip": "作为 first_frame 传入"}),
            "尾帧图": ("IMAGE", {"tooltip": "作为 last_frame 传入"}),
            "音频": ("AUDIO", {"tooltip": "参考音频（Seedance 2.5 支持单独音频）"}),
            "图像1": ("IMAGE", {"tooltip": "参考图 1，连接后自动出现图像2"}),
        }
        return {
            "required": {
                "API密钥": ("STRING", {"default": "", "multiline": False}),
                "模型": (list(MODEL_MAP.keys()), {"default": "Seedance 2.5"}),
                "比例": (RATIO_OPTIONS, {"default": "16:9"}),
                "时长": ("INT", {"default": 5, "min": 4, "max": 15, "step": 1}),
                "提示词": ("STRING", {"default": "", "multiline": True, "placeholder": "描述你想要的视频内容..."}),
                "生成音频": ("BOOLEAN", {"default": True}),
                "分辨率": (["720p", "1080p"], {"default": "720p"}),
            },
            "optional": optional,
        }

    RETURN_TYPES = ("VIDEO",)
    RETURN_NAMES = ("视频",)
    FUNCTION = "generate"
    CATEGORY = CATEGORY
    OUTPUT_NODE = True

    async def generate(self, **kwargs):
        if not _VIDEO_AVAILABLE:
            raise RuntimeError("当前 ComfyUI 版本不支持 VIDEO 输出类型，请升级 ComfyUI。")

        api_key = str(kwargs.get("API密钥", "")).strip()
        if not api_key:
            raise ValueError("API密钥 不能为空。请填写火山方舟 API Key。")

        model_display = kwargs.get("模型", "Seedance 2.5")
        model_id = MODEL_MAP.get(model_display, model_display)
        ratio = kwargs.get("比例", "16:9")
        duration = int(kwargs.get("时长", 5))
        prompt = str(kwargs.get("提示词", ""))
        generate_audio = bool(kwargs.get("生成音频", True))
        resolution = kwargs.get("分辨率", "720p")

        first_frame = kwargs.get("首帧图")
        last_frame = kwargs.get("尾帧图")
        audio = kwargs.get("音频")

        ref_images: list[torch.Tensor] = []
        for i in range(1, 11):
            img = kwargs.get(f"图像{i}")
            if img is not None:
                ref_images.append(img)

        content = _build_content(prompt, first_frame, last_frame, audio, ref_images, generate_audio)
        if not content:
            raise ValueError("至少需要提供提示词、首帧图、尾帧图或任意图像之一。")

        payload: dict[str, Any] = {
            "model": model_id,
            "content": content,
            "duration": duration,
            "resolution": resolution,
            "ratio": ratio,
            "generate_audio": generate_audio,
            "watermark": False,
        }
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        async with aiohttp.ClientSession() as session:
            async with session.post(ARK_CREATE_URL, headers=headers, json=payload) as resp:
                resp_text = await resp.text()
                if resp.status not in (200, 201):
                    raise RuntimeError(f"创建视频任务失败 HTTP {resp.status}：{resp_text[:2000]}")
                created = json.loads(resp_text)

            task_id = created.get("id") or created.get("task_id")
            result = await _poll_task(session, api_key, task_id)

        content_list = result.get("content") or []
        video_url = ""
        if isinstance(content_list, list):
            for item in content_list:
                if isinstance(item, dict) and item.get("video_url"):
                    video_url = item["video_url"]
                    break
        if not video_url:
            video_url = result.get("video_url", "") or result.get("output", {}).get("video_url", "")
        if not video_url:
            raise RuntimeError("任务成功但未找到 video_url")

        local_path = await _download_video(video_url)
        return (VideoFromFile(local_path),)


NODE_CLASS_MAPPINGS = {"NK_DoubaoVideo": NK豆包视频生成}
NODE_DISPLAY_NAME_MAPPINGS = {"NK_DoubaoVideo": "南光AIGC-豆包视频生成"}