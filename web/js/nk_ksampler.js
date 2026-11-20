import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "NK.AIGC.KSampler",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "NK_AIGC_KSampler") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;
                
                // 设置节点默认颜色
                this.color = "#2a2a2a";
                this.bgcolor = "#3a3a3a";
                
                console.log("南光AIGC-K采样器(NK) 已成功加载！");
                return r;
            };
        }
    }
});