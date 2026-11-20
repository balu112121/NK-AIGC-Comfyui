// NK-AIGC-Comfyui/web/js/qwen_image_prompt_optimizer.js

import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

app.registerExtension({
    name: "NK.AIGC.QwenImagePromptOptimizer",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== "NKQwenImagePromptOptimizer") return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = onNodeCreated?.apply(this, arguments);

            // ── 「自动反推」按钮：调用后端反推接口 ──
            this.addWidget("button", "自动反推提示词", null, async () => {
                const textWidget = this.widgets?.find(
                    (w) => w.name === "文本提示词"
                );
                const imageWidget = this.widgets?.find(
                    (w) => w.name === "图像"
                );
                // 如果图像端口已连接，优先提示使用图像反推；
                // 当前节点自身通过 IMAGE 输入，前端无法直接读取张量，
                // 因此这里仅调用纯文本反推接口作为辅助。
                const positive = textWidget?.value?.trim() || "";
                if (!positive) {
                    alert("请先在「文本提示词」中输入内容。");
                    return;
                }
                try {
                    const resp = await api.fetchApi("/nk_aigc/auto_negative", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ positive_prompt: positive }),
                    });
                    const data = await resp.json();
                    if (data.negative_prompt) {
                        // 如果节点上有「负向提示词」类控件可回填；此节点无，
                        // 仅复制到剪贴板，方便用户手动使用。
                        await navigator.clipboard.writeText(
                            data.negative_prompt
                        );
                        alert("反推的负向提示词已复制到剪贴板。");
                    } else if (data.error) {
                        alert("反推失败：" + data.error);
                    }
                } catch (e) {
                    console.warn("[NK-AIGC] 自动反推失败", e);
                }
            });

            // ── 依赖状态提示（非阻塞，仅在控制台输出） ──
            (async () => {
                try {
                    const resp = await api.fetchApi(
                        "/goohai/qwen_image_prompt_optimizer/llama_status"
                    );
                    const status = await resp.json();
                    if (status.needs_install) {
                        console.warn(
                            "[NK-AIGC] llama-cpp-python 依赖状态：",
                            status.reason
                        );
                    } else {
                        console.log(
                            "[NK-AIGC] llama-cpp-python 依赖可用，版本：",
                            status.installed_version
                        );
                    }
                } catch (e) {
                    // 忽略
                }
            })();

            return result;
        };
    },
});