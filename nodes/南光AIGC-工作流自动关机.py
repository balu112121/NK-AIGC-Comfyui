import platform
import subprocess
import time

CATEGORY = "南光AIGC/效率"


class NankangAutoShutdown:
    """
    南光AIGC - 工作流自动关机
    将本节点放在工作流末尾，把保存图像/视频节点的输出（或任意完成信号）
    连接到「触发」输入，工作流全部执行完毕后即按设定执行关机/重启/睡眠。
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "触发": ("*",),  # 通配符输入，接入保存节点的任意输出即可
            },
            "optional": {
                "启用自动关机": ("BOOLEAN", {"default": True}),
                "操作": (["关机", "重启", "睡眠"], {"default": "关机"}),
                "延迟秒数": (
                    "INT",
                    {"default": 30, "min": 0, "max": 600, "step": 5},
                ),
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "execute"
    OUTPUT_NODE = True
    CATEGORY = CATEGORY

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # 强制每次工作流运行都重新执行，避免缓存导致关机不触发
        return time.time()

    def execute(self, 触发, 启用自动关机=True, 操作="关机", 延迟秒数=30):
        if not 启用自动关机:
            print("[NK-AIGC] 自动关机已禁用，本次不执行任何操作。")
            return {"ui": {"text": ["自动关机已禁用"]}}

        system = platform.system()
        delay = max(0, int(延迟秒数))

        try:
            if 操作 == "关机":
                self._shutdown(system, delay)
            elif 操作 == "重启":
                self._reboot(system, delay)
            elif 操作 == "睡眠":
                self._sleep(system, delay)
            else:
                print(f"[NK-AIGC] 未知操作: {操作}")
                return {"ui": {"text": [f"未知操作: {操作}"]}}

            msg = f"已安排 {操作}，延迟 {delay} 秒。"
            print(f"[NK-AIGC] {msg}")
            return {"ui": {"text": [msg]}}

        except Exception as e:
            err = f"自动关机执行失败: {e}"
            print(f"[NK-AIGC] {err}")
            return {"ui": {"text": [err]}}

    # ---------- 跨平台实现 ----------
    def _shutdown(self, system, delay):
        if system == "Windows":
            # /s 关机，/t 延迟秒数，/f 强制关闭应用
            subprocess.Popen(
                ["shutdown", "/s", "/t", str(delay), "/f"],
                shell=False,
            )
        elif system in ("Linux", "Darwin"):
            # Linux/macOS 使用后台延时执行，避免阻塞 ComfyUI
            cmd = f"sleep {delay} && shutdown -h now"
            subprocess.Popen(cmd, shell=True)
        else:
            raise OSError(f"不支持的操作系统: {system}")

    def _reboot(self, system, delay):
        if system == "Windows":
            subprocess.Popen(
                ["shutdown", "/r", "/t", str(delay), "/f"],
                shell=False,
            )
        elif system in ("Linux", "Darwin"):
            cmd = f"sleep {delay} && shutdown -r now"
            subprocess.Popen(cmd, shell=True)
        else:
            raise OSError(f"不支持的操作系统: {system}")

    def _sleep(self, system, delay):
        if system == "Windows":
            # Windows 睡眠（部分机器可能因电源策略不可用）
            subprocess.Popen(
                ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
                shell=False,
            )
        elif system == "Darwin":
            cmd = f"sleep {delay} && pmset sleepnow"
            subprocess.Popen(cmd, shell=True)
        elif system == "Linux":
            cmd = f"sleep {delay} && systemctl suspend"
            subprocess.Popen(cmd, shell=True)
        else:
            raise OSError(f"不支持的操作系统: {system}")

from server import PromptServer
import platform
import subprocess

@PromptServer.instance.routes.post("/nk_aigc/cancel_shutdown")
async def cancel_shutdown(request):
    system = platform.system()
    try:
        if system == "Windows":
            subprocess.run(["shutdown", "/a"], check=True, capture_output=True)
            return web.json_response({"message": "Windows 自动关机已取消"})
        else:
            # Linux 上若使用了 shutdown -h +m，可执行 shutdown -c 取消
            subprocess.run(["shutdown", "-c"], check=False, capture_output=True)
            return web.json_response({"message": "已发送取消关机命令（Linux/macOS）"})
    except Exception as e:
        return web.json_response({"message": f"取消失败：{e}"})


NODE_CLASS_MAPPINGS = {
    "NankangAutoShutdown": NankangAutoShutdown,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "NankangAutoShutdown": "南光AIGC-工作流自动关机",
}