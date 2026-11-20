// NK-AIGC-Comfyui/web/js/image_to_prompt.js
import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "NK.AIGC.ImageToPrompt",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "NKImageToPrompt") return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            if (onNodeCreated) onNodeCreated.apply(this, arguments);

            const node = this;

            // 节点上添加“🔄 反推提示词”按钮
            node.addWidget("button", "🔄 反推提示词", null, async () => {
                if (app.ui?.dialog?.show) {
                    app.ui.dialog.show(
                        "请点击队列执行工作流，节点会自动完成图像反推。\n反推结果会输出到「提示词」端口。"
                    );
                }
            });

            if (node.widgets) {
                const modelWidget = node.widgets.find((w) => w.name === "模型");
                if (modelWidget) {
                    modelWidget.tooltip =
                        "3B 适合 12GB 显存；7B 精度更高但需更多显存，首次运行从 hf-mirror.com 下载";
                }
            }
        };
    },
});