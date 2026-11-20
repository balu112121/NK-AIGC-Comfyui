// NK-AIGC-Comfyui/web/js/nk_image_resize.js
import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "NK.AIGC.ImageResize",

    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "NKImageResize") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;

            nodeType.prototype.onNodeCreated = function () {
                const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;

                const methodWidget = this.widgets?.find(w => w.name === "缩放方法");
                const widthWidget = this.widgets?.find(w => w.name === "宽度");
                const heightWidget = this.widgets?.find(w => w.name === "高度");
                const scaleToEdgeWidget = this.widgets?.find(w => w.name === "将边缩放到");

                if (methodWidget && widthWidget && heightWidget && scaleToEdgeWidget) {
                    const updateWidgets = () => {
                        const method = methodWidget.value;
                        const isDirect = method === "指定宽高"; // <--- 修改点 3
                        const isScaleEdge = method === "按长边等比例" || method === "按短边等比例";

                        // 如果是指定宽高，启用宽高，禁用等比例边
                        widthWidget.disabled = !isDirect;
                        heightWidget.disabled = !isDirect;
                        
                        // 如果是等比例缩放，禁用宽高，启用等比例边
                        scaleToEdgeWidget.disabled = !isScaleEdge;
                    };
                    
                    methodWidget.callback = updateWidgets;
                    updateWidgets();
                }

                return r;
            };
        }
    },
});