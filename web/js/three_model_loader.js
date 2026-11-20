// NK-AIGC-Comfyui/web/js/three_model_loader.js
import { app } from "../../../scripts/app.js";

const NODE_NAME = "NKThreeModelLoader";

app.registerExtension({
    name: "NK.AIGC.ThreeModelLoader",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== NODE_NAME) return;

        const origOnNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            if (origOnNodeCreated) origOnNodeCreated.apply(this, arguments);

            const widgets = this.widgets || [];

            // 统一补充中文标签
            const labelMap = {
                unet_name: "UNET模型",
                weight_dtype: "权重类型",
                clip_name1: "CLIP 1",
                clip_name2: "CLIP 2",
                clip_type: "CLIP类型",
                device: "加载设备",
                vae_name: "VAE模型",
            };

            for (const w of widgets) {
                if (labelMap[w.name]) {
                    w.label = labelMap[w.name];
                }

                // ★ 核心修复：在前端彻底把 "None" 变成 "无" 显示，并去重
                if (w.name === "clip_name2" && w.options && Array.isArray(w.options.values)) {
                    // 替换底层列表中的 None 为 无
                    w.options.values = w.options.values.map(v => v === "None" ? "无" : v);
                    // 数组去重，防止出现多个 无
                    w.options.values = [...new Set(w.options.values)];
                    
                    // 如果当前选中的是 None，强制改成 "无"
                    if (w.value === "None" || w.value === undefined || w.value === null) {
                        w.value = "无";
                    }
                }
            }

            // 节点配色（保持你喜欢的深灰色）
            this.color = "#353535";
            this.bgcolor = "#2b2b2b";
        };
    },
});