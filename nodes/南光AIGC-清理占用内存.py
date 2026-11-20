# NK-AIGC-Comfyui/nodes/memory_cleanup.py
import gc
import time
import platform
import ctypes
from ctypes import wintypes
import psutil
import torch

import comfy.model_management
import folder_paths


# ── 通配符类型：允许任何输入连接 ──────────────────────────────
class AnyType(str):
    def __ne__(self, __value: object) -> bool:
        return False

any_type = AnyType("*")


class NK_AIGC_MemoryCleanup:
    """
    南光AIGC-清理占用内存
    在节点处手动或自动清理 CPU / RAM / GPU / VRAM / 临时缓存。
    """

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                # 5 个开关，全部默认开启
                "清理CPU": ("BOOLEAN", {"default": True, "label_on": "开启", "label_off": "关闭"}),
                "清理RAM": ("BOOLEAN", {"default": True, "label_on": "开启", "label_off": "关闭"}),
                "清理GPU": ("BOOLEAN", {"default": True, "label_on": "开启", "label_off": "关闭"}),
                "清理VRAM": ("BOOLEAN", {"default": True, "label_on": "开启", "label_off": "关闭"}),
                "清理临时缓存": ("BOOLEAN", {"default": True, "label_on": "开启", "label_off": "关闭"}),
            },
            "optional": {
                # 通配符输入，可以连接任何节点的输出端
                "任意内容": (any_type, {}),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ("输出",)
    OUTPUT_NODE = True
    FUNCTION = "cleanup_memory"
    CATEGORY = "南光AIGC/清理"

    @classmethod
    def IS_CHANGED(s, **kwargs):
        # 每次都执行，确保点击“运行”时必定清理
        return float(time.time())

    def cleanup_memory(
        self,
        清理CPU,
        清理RAM,
        清理GPU,
        清理VRAM,
        清理临时缓存,
        任意内容=None,
        unique_id=None,
        extra_pnginfo=None,
    ):
        result_log = []

        # ── 1. 清理 CPU（主要是 Python 垃圾回收 + 系统工作集修剪） ──
        if 清理CPU:
            try:
                gc.collect()
                if platform.system() == "Windows":
                    # 修剪当前进程工作集，促使系统回收部分内存
                    ctypes.windll.kernel32.SetProcessWorkingSetSize(-1, -1, -1)
                elif platform.system() == "Linux":
                    libc = ctypes.CDLL("libc.so.6")
                    libc.malloc_trim(0)
                result_log.append("CPU缓存已清理")
            except Exception as e:
                result_log.append(f"CPU清理跳过({e})")

        # ── 2. 清理 RAM（系统内存，通过 psutil 强制回收文件缓存） ──
        if 清理RAM:
            try:
                # 尝试清理系统文件缓存（仅部分系统生效）
                system = platform.system()
                if system == "Windows":
                    ctypes.windll.kernel32.SetSystemFileCacheSize(-1, -1, 0)
                elif system == "Linux":
                    libc = ctypes.CDLL("libc.so.6")
                    libc.malloc_trim(0)

                # 读取清理后的 RAM 状态用于日志
                mem = psutil.virtual_memory()
                result_log.append(f"RAM已清理(可用 {mem.available // (1024**2)} MB)")
            except Exception as e:
                result_log.append(f"RAM清理跳过({e})")

        # ── 3. 清理 GPU（卸载已加载的模型） ──────────────────────
        if 清理GPU:
            try:
                comfy.model_management.unload_all_models()
                result_log.append("GPU模型已卸载")
            except Exception as e:
                result_log.append(f"GPU卸载跳过({e})")

        # ── 4. 清理 VRAM（CUDA 显存缓存） ────────────────────────
        if 清理VRAM:
            try:
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.ipc_collect()
                    result_log.append("VRAM显存已清理")
                else:
                    result_log.append("VRAM清理跳过(无CUDA)")
            except Exception as e:
                result_log.append(f"VRAM清理跳过({e})")

        # ── 5. 清理临时缓存（ComfyUI 执行缓存 + Python GC） ──────
        if 清理临时缓存:
            try:
                # 通知 ComfyUI 的 prompt 队列释放执行缓存
                from server import PromptServer
                PromptServer.instance.prompt_queue.set_flag("free_memory", True)

                # 再次执行 Python 垃圾回收，清理临时张量等
                gc.collect()
                result_log.append("临时缓存已清理")
            except Exception as e:
                result_log.append(f"临时缓存清理跳过({e})")

        # ── 输出日志到控制台 ──────────────────────────────────────
        print(f"[南光AIGC-清理] {' | '.join(result_log)}")

        # 将输入原样返回，保证工作流数据流不中断
        return (任意内容,)


# ── 节点注册 ──────────────────────────────────────────────────
NODE_CLASS_MAPPINGS = {
    "NK_AIGC_MemoryCleanup": NK_AIGC_MemoryCleanup,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "NK_AIGC_MemoryCleanup": "南光AIGC-清理占用内存",
}