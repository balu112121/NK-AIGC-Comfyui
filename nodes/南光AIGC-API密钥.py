# NK-AIGC-Comfyui/nodes/api_key_node.py
import json
import os
from pathlib import Path

from aiohttp import web
from server import PromptServer

# ── 密钥备份文件路径（ComfyUI/user/nk_aigc_api_keys.json）────────
try:
    import folder_paths
    _USER_DIR = folder_paths.get_user_directory()
except Exception:
    # 兼容没有 folder_paths 的环境
    _USER_DIR = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "user")
    )

_KEY_FILE = Path(_USER_DIR) / "nk_aigc_api_keys.json"


def _load_keys() -> dict:
    if not _KEY_FILE.exists():
        return {}
    try:
        with open(_KEY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_keys(data: dict) -> None:
    _KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(_KEY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── 前端路由：保存 / 读取密钥 ──────────────────────────────────
@PromptServer.instance.routes.post("/nk_aigc/api_key/save")
async def nk_aigc_api_key_save(request):
    """请求体：{ "name": "密钥名称", "value": "sk-..." }"""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "无效的 JSON"}, status=400)

    name = (data.get("name") or "").strip()
    value = data.get("value", "")

    if not name:
        return web.json_response({"error": "密钥名称不能为空"}, status=400)

    keys = _load_keys()
    keys[name] = value
    _save_keys(keys)

    return web.json_response({"ok": True, "name": name})


@PromptServer.instance.routes.get("/nk_aigc/api_key/list")
async def nk_aigc_api_key_list(request):
    """返回已保存的密钥名称列表（不返回具体密钥值，避免泄露）。"""
    keys = _load_keys()
    return web.json_response({"names": list(keys.keys())})


@PromptServer.instance.routes.get("/nk_aigc/api_key/get/{name}")
async def nk_aigc_api_key_get(request):
    """按名称读取密钥值。"""
    name = request.match_info.get("name", "")
    keys = _load_keys()
    if name not in keys:
        return web.json_response({"error": "密钥不存在"}, status=404)
    return web.json_response({"name": name, "value": keys[name]})


# ── 节点类定义 ────────────────────────────────────────────────
class NK_AIGC_APIKey:
    """
    南光AIGC-API密钥（子节点 / 前端虚拟节点）。

    该节点不参与后端 prompt 执行，仅在前端维护一个字符串值，
    并通过 DOM Widget 持久化到工作流中。
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "api_key": ("STRING", {
                    "default": "",
                    "multiline": False,
                    # 前端 JS 会把这个 widget 替换为密码输入框
                }),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("密钥",)
    FUNCTION = "output_key"
    CATEGORY = "南光AIGC/API"

    # 标记为虚拟节点：ComfyUI 不会把它发送到后端执行
    isVirtualNode = True

    def output_key(self, api_key):
        return (api_key,)


# ── 注册映射 ──────────────────────────────────────────────────
NODE_CLASS_MAPPINGS = {
    "NK_AIGC_APIKey": NK_AIGC_APIKey,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "NK_AIGC_APIKey": "南光AIGC-API密钥",
}