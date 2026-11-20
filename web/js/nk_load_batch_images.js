import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "NK.AIGC.LoadBatchImages",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "NKLoadBatchImages") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            
            nodeType.prototype.onNodeCreated = function () {
                const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;

                // 仅做基础宽度适配，不注入任何多余控件，保持原图纯净界面
                if (this.size[0] < 320) this.size[0] = 320;

                return r;
            };
        }
    }
});