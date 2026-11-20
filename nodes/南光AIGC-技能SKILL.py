# NK-AIGC-Comfyui/nodes/skill_node.py
import json
import importlib.util
import traceback
import zipfile
import shutil
from pathlib import Path
import folder_paths

PLUGIN_SKILL_DIR = Path(__file__).parent.parent / "skills"
PLUGIN_SKILL_DIR.mkdir(exist_ok=True)

INPUT_DIR = Path(folder_paths.get_input_directory())
UPLOAD_SKILL_DIR = INPUT_DIR / "nk_skills"
UPLOAD_SKILL_DIR.mkdir(exist_ok=True)

class NKSkillNode:
    CATEGORY = "南光AIGC/提示词"

    @classmethod
    def INPUT_TYPES(cls):
        zip_files = []
        for d in [PLUGIN_SKILL_DIR, UPLOAD_SKILL_DIR]:
            if d.exists():
                zip_files.extend([p.name for p in d.glob("*.zip")])
        
        zip_files = sorted(list(set(zip_files)))
        if not zip_files:
            zip_files = ["__无技能包，请先上传__"]

        return {
            "required": {},
            "optional": {
                "文本": ("STRING", {"forceInput": True}),
                "图像": ("IMAGE", {"forceInput": True}),
                "音频": ("AUDIO", {"forceInput": True}),
                "视频": ("VIDEO", {"forceInput": True}),
                "SKILL加载": (zip_files, {"default": zip_files[0]}),
                "API_KEY": ("STRING", {"default": "", "multiline": False}),
            },
        }

    RETURN_TYPES = ("STRING", "IMAGE", "AUDIO", "VIDEO")
    RETURN_NAMES = ("文本", "图像", "音频", "视频")
    FUNCTION = "execute"

    def execute(self, 文本=None, 图像=None, 音频=None, 视频=None, SKILL加载=None, API_KEY="", **kwargs):
        context = {
            "text": 文本, "image": 图像, "audio": 音频, "video": 视频, "api_key": API_KEY,
        }

        if not SKILL加载 or SKILL加载.startswith("__"):
            return (context["text"], context["image"], context["audio"], context["video"])

        zip_path = None
        if (PLUGIN_SKILL_DIR / SKILL加载).exists():
            zip_path = PLUGIN_SKILL_DIR / SKILL加载
        elif (UPLOAD_SKILL_DIR / SKILL加载).exists():
            zip_path = UPLOAD_SKILL_DIR / SKILL加载

        if not zip_path:
            raise FileNotFoundError(f"找不到技能包: {SKILL加载}")

        try:
            result = self._run_skill(zip_path, context)
        except Exception as e:
            traceback.print_exc()
            raise RuntimeError(f"技能执行失败，请查看后台控制台。报错: {e}") from e

        return (
            result.get("text", context["text"]),
            result.get("image", context["image"]),
            result.get("audio", context["audio"]),
            result.get("video", context["video"])
        )

    def _run_skill(self, zip_path: Path, context: dict) -> dict:
        extract_root = zip_path.parent / f"_extracted_{zip_path.stem}"
        if extract_root.exists():
            shutil.rmtree(extract_root)
        extract_root.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_root)

        # 智能定位 manifest 和 main.py
        manifest_path = extract_root / "manifest.json"
        manifest = {}
        if manifest_path.exists():
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        else:
            manifest_files = list(extract_root.rglob("manifest.json"))
            if manifest_files:
                manifest_path = manifest_files[0]
                extract_root = manifest_path.parent
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)

        entry = manifest.get("entry", "main.py")
        entry_path = extract_root / entry

        if not entry_path.exists():
            found_entries = list(extract_root.rglob(entry))
            if found_entries:
                entry_path = found_entries[0]
                extract_root = entry_path.parent
                print(f"[NK-SKILL] 检测到ZIP目录嵌套，已自动修正路径至: {extract_root}")
            else:
                raise FileNotFoundError(f"ZIP包中找不到入口文件 '{entry}'！请确认文件中包含该代码。")

        module_name = f"nk_skill_{zip_path.stem}_{id(entry_path)}"
        spec = importlib.util.spec_from_file_location(module_name, entry_path)
        module = importlib.util.module_from_spec(spec)
        
        import sys
        sys.path.insert(0, str(extract_root))
        try:
            spec.loader.exec_module(module)
            if not hasattr(module, "run"):
                raise AttributeError(f"入口文件 {entry} 中缺少 run(context) 函数！")
            result = module.run(context)
        finally:
            sys.path.pop(0)

        if not isinstance(result, dict):
            raise TypeError("技能包的 run(context) 必须返回 dict！")

        return result

NODE_CLASS_MAPPINGS = {"NKSkillNode": NKSkillNode}
NODE_DISPLAY_NAME_MAPPINGS = {"NKSkillNode": "南光AIGC-技能SKILL"}