import { app } from "../../../scripts/app.js";

app.registerExtension({
    name: "nk.aigc.auto_shutdown",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "NankangAutoShutdown") return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            onNodeCreated?.apply(this, arguments);

            // 状态文字
            this.statusWidget = this.addWidget(
                "text",
                "状态",
                "等待工作流执行…",
                () => {}
            );
            this.statusWidget.disabled = true;

            // 取消关机按钮（Windows 上执行 shutdown /a，Linux 提示命令）
            this.addWidget("button", "取消自动关机", null, async () => {
                try {
                    const resp = await fetch("/nk_aigc/cancel_shutdown", {
                        method: "POST",
                    });
                    const data = await resp.json();
                    this.statusWidget.value = data.message || "取消请求已发送";
                } catch (e) {
                    this.statusWidget.value = "取消失败：" + e.message;
                }
                this.setDirtyCanvas(true);
            });

            // 显示后端执行结果
            const origOnExecuted = this.onExecuted;
            this.onExecuted = function (message) {
                origOnExecuted?.apply(this, arguments);
                if (message?.text?.[0]) {
                    this.statusWidget.value = message.text[0];
                    this.setDirtyCanvas(true);
                }
            };
        };
    },
});