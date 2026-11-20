// NK-AIGC-Comfyui/web/js/doubao_video.js
import { app } from "../../scripts/app.js";

const NODE_NAME = "NK_DoubaoVideo";
const API_KEY_WIDGET = "API密钥";
const STORAGE_KEY = "nk_aigc_doubao_api_key";

app.registerExtension({
    name: "NK.AIGC.DoubaoVideo",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== NODE_NAME) return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;

            // 1) API Key 本地存储
            const apiWidget = this.widgets?.find((w) => w.name === API_KEY_WIDGET);
            if (apiWidget) {
                const saved = localStorage.getItem(STORAGE_KEY);
                if (saved && !apiWidget.value) apiWidget.value = saved;

                this.addWidget("button", "设置密钥(保存到浏览器)", null, () => {
                    const key = prompt("请输入火山方舟 API Key（将保存到当前浏览器本地）：", apiWidget.value || "");
                    if (key !== null) {
                        apiWidget.value = key.trim();
                        localStorage.setItem(STORAGE_KEY, apiWidget.value);
                    }
                });
            }

            // 2) 动态端口：连接图像N → 自动出现图像N+1
            this.onConnectionsChange = function (type, index, connected, link_info) {
                if (type !== 1) return;
                const slot = this.inputs?.[index];
                if (!slot) return;

                const match = slot.name.match(/^图像(\d+)$/);
                if (match) {
                    const n = parseInt(match[1], 10);
                    if (connected && n >= 1 && n < 10) {
                        const nextName = `图像${n + 1}`;
                        if (!this.inputs.some(x => x.name === nextName)) {
                            this.addInput(nextName, "IMAGE");
                        }
                    } else if (!connected) {
                        for (let i = 10; i > 1; i--) {
                            const idx = this.inputs.findIndex(x => x.name === `图像${i}`);
                            if (idx !== -1) {
                                if (!this.inputs[idx].link) {
                                    this.removeInput(idx);
                                } else {
                                    break;
                                }
                            }
                        }
                    }
                }
                this.setSize([this.size[0], this.computeSize()[1]]);
                if (this.graph) this.graph.setDirtyCanvas(true, true);
            };

            // 3) 工作流加载时恢复动态端口
            const onConfigure = this.onConfigure;
            this.onConfigure = function (info) {
                const r2 = onConfigure ? onConfigure.apply(this, arguments) : undefined;
                setTimeout(() => {
                    if (!this.inputs) return;
                    let maxConnected = 1;
                    for (let i = 1; i <= 10; i++) {
                        const s = this.inputs.find(x => x.name === `图像${i}`);
                        if (s && s.link) maxConnected = Math.max(maxConnected, i);
                    }
                    for (let i = 2; i <= Math.min(10, maxConnected + 1); i++) {
                        if (!this.inputs.some(x => x.name === `图像${i}`)) {
                            this.addInput(`图像${i}`, "IMAGE");
                        }
                    }
                    this.setSize([this.size[0], this.computeSize()[1]]);
                }, 50);
                return r2;
            };

            return r;
        };
    },
});