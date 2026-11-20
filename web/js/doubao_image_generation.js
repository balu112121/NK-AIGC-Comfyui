// web/js/doubao_image_generation.js
import { app } from "../../scripts/app.js";

const NODE_NAME = "NK_AIGC_DoubaoImageGeneration";
const MAX_IMAGES = 10;
const IMAGE_NAMES = ["image"];
for (let i = 1; i < MAX_IMAGES; i++) IMAGE_NAMES.push(`image${i}`);

app.registerExtension({
    name: "NK.AIGC.DoubaoImageGeneration",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== NODE_NAME) return;

        // ── 节点创建 ──
        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            onNodeCreated?.apply(this, arguments);

            // 刷新槽位：已连接 N 张 → 显示 N+1 个槽（上限 10）
            this._doubaoRefreshImageSlots = function () {
                const imgInputs = this.inputs.filter((i) => i.type === "IMAGE");
                const connected = imgInputs.filter((i) => i.link != null).length;
                const need = Math.min(Math.max(connected + 1, 1), MAX_IMAGES);

                // 补齐
                let guard = 0;
                while (
                    this.inputs.filter((i) => i.type === "IMAGE").length < need &&
                    guard++ < MAX_IMAGES
                ) {
                    const used = new Set(
                        this.inputs.filter((i) => i.type === "IMAGE").map((i) => i.name)
                    );
                    const nextName = IMAGE_NAMES.find((n) => !used.has(n));
                    if (!nextName) break;
                    this.addInput(nextName, "IMAGE");
                }

                // 收缩：移除末尾未连接的槽（保留 image 主槽）
                for (let i = this.inputs.length - 1; i >= 0; i--) {
                    const inp = this.inputs[i];
                    if (inp.type !== "IMAGE") continue;
                    const total = this.inputs.filter((x) => x.type === "IMAGE").length;
                    if (total <= need) break;
                    if (inp.link == null && inp.name !== "image") {
                        this.removeInput(i);
                    }
                }

                // 自适应高度
                const size = this.computeSize();
                this.setSize([Math.max(this.size[0], size[0]), size[1]]);
                this.setDirtyCanvas(true, true);
            };

            // 初始清理：只保留 image（如果有连线则保留）
            this._doubaoInitialHide = function () {
                for (let i = this.inputs.length - 1; i >= 0; i--) {
                    const inp = this.inputs[i];
                    if (
                        inp.type === "IMAGE" &&
                        inp.name !== "image" &&
                        inp.link == null
                    ) {
                        this.removeInput(i);
                    }
                }
                this._doubaoRefreshImageSlots();
            };

            // 延迟清理，等可能的连线恢复完成
            setTimeout(() => this._doubaoInitialHide?.(), 0);

            // 连接变化监听
            const origConn = this.onConnectionsChange;
            this.onConnectionsChange = function (type, index, connected, link_info, input_info) {
                origConn?.apply(this, arguments);
                this._doubaoRefreshImageSlots?.();
            };

            this.setSize([320, 380]);
        };

        // ── 加载工作流时，等连线恢复后再清理 ──
        const onConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function (info) {
            onConfigure?.apply(this, arguments);
            setTimeout(() => this._doubaoInitialHide?.(), 0);
        };
    },
});