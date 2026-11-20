// NK-AIGC-Comfyui/web/js/memory_cleanup.js
import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

app.registerExtension({
    name: "NK.AIGC.MemoryCleanup",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "NK_AIGC_MemoryCleanup") {
            // 在节点创建时，可以在浏览器控制台看到提示
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;
                console.log("[南光AIGC] 清理占用内存节点已创建，运行工作流时将自动清理所选内存。");
                return r;
            };
        }
    },
});