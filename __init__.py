# NK-AIGC-Comfyui/__init__.py

import os
import sys
import json
import asyncio
import importlib.util
import importlib.metadata
import platform
import re
import subprocess
import urllib.request
from pathlib import Path

from aiohttp import web
from server import PromptServer

current_dir = Path(__file__).parent
nodes_dir = current_dir / "nodes"

# 前端 JS 扩展目录：指向 web/js，ComfyUI 只扫描该目录下一层的 .js 文件
WEB_DIRECTORY = "./web/js"

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

# 保存已加载的模块对象，便于后续复用其内部函数
_loaded_modules = {}

# ── 动态加载 nodes 目录下的所有 Python 节点文件 ─────────────
for file_path in sorted(nodes_dir.glob("*.py")):
    if file_path.name == "__init__.py":
        continue

    module_name = file_path.stem
    spec = importlib.util.spec_from_file_location(
        f"nk_aigc.nodes.{module_name}", file_path
    )
    module = importlib.util.module_from_spec(spec)

    try:
        spec.loader.exec_module(module)
        _loaded_modules[module_name] = module

        if hasattr(module, "NODE_CLASS_MAPPINGS"):
            NODE_CLASS_MAPPINGS.update(module.NODE_CLASS_MAPPINGS)

        if hasattr(module, "NODE_DISPLAY_NAME_MAPPINGS"):
            NODE_DISPLAY_NAME_MAPPINGS.update(module.NODE_DISPLAY_NAME_MAPPINGS)

    except Exception as e:
        print(f"[NK-AIGC] 加载节点模块 {module_name} 失败: {e}")
        continue


# ── 从前端路由复用 text_prompt_node 的反推函数 ───────────────
_text_prompt_module = _loaded_modules.get("text_prompt_node")
_auto_negative_from_positive = getattr(
    _text_prompt_module, "_auto_negative_from_positive", None
)


# ── HTTP 路由：前端「自动反推负面提示词」按钮调用 ────────────
@PromptServer.instance.routes.post("/nk_aigc/auto_negative")
async def nk_aigc_auto_negative(request):
    """接收 JSON: { "positive_prompt": "..." } 返回反推的负向提示词。"""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "无效的 JSON"}, status=400)

    positive = (data.get("positive_prompt") or "").strip()
    if not positive:
        return web.json_response({"negative_prompt": ""})

    if _auto_negative_from_positive is None:
        return web.json_response({"error": "反推函数未加载"}, status=500)

    negative = _auto_negative_from_positive(positive)
    return web.json_response({"negative_prompt": negative})


# ══════════════════════════════════════════════════════════════
# ── 自动安装 llama-cpp-python 相关路由与逻辑 ──────────────────
# ══════════════════════════════════════════════════════════════

_LLAMA_CPP_MIN_VERSION = (0, 3, 48)
_LLAMA_CPP_RELEASES_URL = "https://github.com/JamePeng/llama-cpp-python/releases"
_LLAMA_CPP_API_URL = "https://api.github.com/repos/JamePeng/llama-cpp-python/releases?per_page=100"
_LLAMA_CPP_INSTALL_LOCK = asyncio.Lock()


def _version_tuple(value: str) -> tuple[int, int, int]:
    match = re.match(r"\s*(\d+)\.(\d+)\.(\d+)", str(value or ""))
    return tuple(map(int, match.groups())) if match else (0, 0, 0)


def _llama_install_target() -> dict[str, str | bool]:
    system = platform.system()
    machine = platform.machine().casefold()
    python_tag = f"cp{sys.version_info.major}{sys.version_info.minor}"
    result: dict[str, str | bool] = {
        "supported": False,
        "system": system,
        "machine": platform.machine(),
        "python_tag": python_tag,
        "release_url": _LLAMA_CPP_RELEASES_URL,
    }
    if system == "Darwin" and machine in {"arm64", "aarch64"}:
        result.update({
            "supported": True,
            "backend": "metal",
            "tag_marker": "-metal-macos-",
            "wheel_suffix": f"-{python_tag}-{python_tag}-macosx_11_0_arm64.whl",
        })
        return result
    if system == "Windows" and machine in {"amd64", "x86_64"}:
        os_marker, wheel_platform = "-win-", "win_amd64"
    elif system == "Linux" and machine in {"amd64", "x86_64"}:
        os_marker, wheel_platform = "-linux-", "linux_x86_64"
    else:
        result["reason"] = "当前系统或 CPU 架构没有可自动选择的官方 wheel。"
        return result
    try:
        import torch
        cuda_version = str(torch.version.cuda or "")
    except Exception:
        cuda_version = ""
    cuda_match = re.match(r"(\d+)\.(\d+)", cuda_version)
    if not cuda_match:
        result["reason"] = "未检测到 PyTorch CUDA 环境，无法安全选择 GPU wheel。"
        return result
    backend = f"cu{cuda_match.group(1)}{cuda_match.group(2)}"
    result.update({
        "supported": True,
        "backend": backend,
        "cuda": cuda_version,
        "tag_marker": f"-{backend}{os_marker}",
        "wheel_suffix": f"-{python_tag}-{python_tag}-{wheel_platform}.whl",
    })
    return result


def _llama_dependency_status() -> dict[str, object]:
    target = _llama_install_target()
    try:
        installed_version = importlib.metadata.version("llama-cpp-python")
    except importlib.metadata.PackageNotFoundError:
        installed_version = ""
    reasons: list[str] = []
    if not installed_version:
        reasons.append("当前未安装 llama-cpp-python")
    elif _version_tuple(installed_version) < _LLAMA_CPP_MIN_VERSION:
        reasons.append(f"当前 llama-cpp-python 版本：{installed_version}")
    if importlib.util.find_spec("diskcache") is None:
        reasons.append("缺少运行依赖：diskcache")
    return {
        **target,
        "installed_version": installed_version or None,
        "needs_install": bool(reasons),
        "reason": "；".join(reasons) or "依赖可用",
        "minimum_version": "0.3.48",
    }


def _find_llama_wheel(target: dict[str, object]) -> tuple[str, str]:
    request = urllib.request.Request(
        _LLAMA_CPP_API_URL,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "NK-AIGC-Comfyui"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        releases = json.load(response)
    marker = str(target["tag_marker"]).casefold()
    suffix = str(target["wheel_suffix"]).casefold()
    for release in releases:
        if release.get("draft") or release.get("prerelease"):
            continue
        tag = str(release.get("tag_name", ""))
        if marker not in tag.casefold():
            continue
        for asset in release.get("assets", []):
            name = str(asset.get("name", ""))
            url = str(asset.get("browser_download_url", ""))
            if name.casefold().endswith(suffix) and url.startswith(
                "https://github.com/JamePeng/llama-cpp-python/releases/download/"
            ):
                return url, name
    raise RuntimeError("官方发布页没有找到与当前系统、Python 和 CUDA 完全匹配的 wheel。")


def _install_llama_cpp() -> dict[str, object]:
    target = _llama_install_target()
    if not target.get("supported"):
        raise RuntimeError(str(target.get("reason") or "当前环境不支持自动安装。"))
    wheel_url, wheel_name = _find_llama_wheel(target)
    command = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--upgrade",
        "--force-reinstall",
        "--no-deps",
        "--disable-pip-version-check",
        "--no-input",
        "diskcache",
        wheel_url,
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=900,
        check=False,
    )
    output = "\n".join(part.strip() for part in (completed.stdout, completed.stderr) if part.strip())
    if completed.returncode != 0:
        raise RuntimeError(f"pip 安装失败（退出码 {completed.returncode}）：\n{output[-4000:]}")
    return {
        "success": True,
        "wheel": wheel_name,
        "message": "llama-cpp-python 安装完成。请完全重启 ComfyUI 后再使用该节点。",
    }


@PromptServer.instance.routes.get("/goohai/qwen_image_prompt_optimizer/llama_status")
async def qwen_image_llama_status(_request):
    return web.json_response(_llama_dependency_status())


@PromptServer.instance.routes.post("/goohai/qwen_image_prompt_optimizer/install_llama")
async def qwen_image_install_llama(request):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    if payload.get("confirm") is not True:
        return web.json_response({"success": False, "message": "安装请求缺少用户确认。"}, status=400)
    if _LLAMA_CPP_INSTALL_LOCK.locked():
        return web.json_response({"success": False, "message": "安装任务正在运行。"}, status=409)
    async with _LLAMA_CPP_INSTALL_LOCK:
        try:
            result = await asyncio.to_thread(_install_llama_cpp)
            return web.json_response(result)
        except Exception as error:
            return web.json_response({
                "success": False,
                "message": str(error),
                "release_url": _LLAMA_CPP_RELEASES_URL,
            }, status=500)


# ── 导出与启动日志 ─────────────
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]

print(
    f"\033[92m[NK-AIGC]\033[0m "
    f"\033[93m{len(NODE_CLASS_MAPPINGS)} 个节点\033[0m 已加载 | "
    f"\033[94m前端扩展已启用\033[0m"
)